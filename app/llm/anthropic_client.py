import logging
from collections.abc import Awaitable, Callable

from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncAnthropic,
)

from app.core.config import settings


logger = logging.getLogger(__name__)

# Called with {"type": "delta", "text": ...} for each chunk of answer text and
# {"type": "tool", "name": ...} when a call ends in a tool request -- the text
# streamed before it was preamble, and the receiver should start over.
StreamEvent = Callable[[dict], Awaitable[None]]


class LLMUnavailableError(RuntimeError):
    """Claude API is unreachable, rate-limited, or returned an error."""


class ClaudeLLMClient:
    """Async client for Claude (Anthropic API)."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        timeout: float = 60.0,
    ) -> None:

        key = api_key or settings.anthropic_api_key

        if not key:
            raise LLMUnavailableError(
                "no Anthropic API key configured :: set ANTHROPIC_API_KEY in .env"
            )

        self.model = model or settings.anthropic_model or "claude-sonnet-5"
        self.max_tokens = max_tokens or settings.anthropic_max_tokens
        # Omitting on max_tokens and adds seconds per call; send it explicitly on every
        # request so the setting decides.
        self.thinking = (
            {"type": "adaptive"} if settings.anthropic_thinking else {"type": "disabled"}
        )
        self.output_config = (
            {"effort": settings.anthropic_effort} if settings.anthropic_effort else None
        )
        self._client = AsyncAnthropic(api_key=key, timeout=timeout)

    async def _stream_once(self, request: dict, 
                           on_event: StreamEvent | None
                           ):
        """One streamed request. Text deltas go to on_event as they arrive;
        the complete message comes back for the tool loop to inspect."""
        async with self._client.messages.stream(**request) as stream:

            async for text in stream.text_stream:

                if on_event and text:
                    await on_event({"type": "delta", "text": text})

            return await stream.get_final_message()

    def _request(self, system, 
                 messages: list[dict],
                 tools: list[dict] | None
                 ) -> dict:
        request = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "thinking": self.thinking,
            "system": system or "",
            "messages": messages,
            # Automatic breakpoint on the last block, so the second call of a
            # tool turn reads the first call's prefix from cache instead of
            # paying for it again. The explicit marker on the stable system
            # block (set by the caller) covers the part every turn shares.
            "cache_control": {"type": "ephemeral"},
        }
        if tools:
            request["tools"] = tools

        if self.output_config:
            request["output_config"] = self.output_config

        return request

    @staticmethod
    def _text(response) -> str:
        return "".join(block.text for block in response.content if block.type == "text")

    def _log(self, response, reply: str) -> None:
        usage = response.usage
        logger.info(
            "Claude replied (%d chars, stop=%s, in=%d cached=%d out=%d tokens)",
            len(reply),
            response.stop_reason,
            usage.input_tokens,
            usage.cache_read_input_tokens or 0,
            usage.output_tokens,
        )

    async def generate(
        self,
        message: str,
        system: str | list[dict] | None = None,
        history: list[dict] | None = None,
        retries: int = 1,
        on_event: StreamEvent | None = None,
    ) -> str:
        """
        Send one turn and return Claude's reply.

        message : the current user turn.
        system : system prompt, a string or a list of text blocks (the latter
            lets the caller put a cache_control marker on the stable part).
        history : prior turns as [{"role": "user"|"assistant", "content": str}].
        on_event : receives text deltas as they stream.
        """
        messages = [*(history or []), {"role": "user", "content": message}]
        request = self._request(system, messages, None)

        last: Exception | None = None

        for attempt in range(retries + 1):
            try:
                response = await self._stream_once(request, on_event)
                reply = self._text(response)

                if response.stop_reason == "max_tokens":
                    # The answer is cut mid-sentence. Say so rather than letting
                    # a truncated geology assessment read as a complete one.
                    logger.warning(
                        "Claude hit max_tokens=%d; answer truncated", self.max_tokens
                    )
                    reply = reply.rstrip() + "\n\n[Answer truncated at the length limit.]"

                self._log(response, reply)
                return reply

            except (APIConnectionError, APITimeoutError) as e:
                last = e
                logger.warning(
                    "Claude call failed (attempt %d/%d): %s", attempt + 1, retries + 1, e
                )
            except APIStatusError as e:
                # 4xx/5xx from the API -- retrying blindly on a 4xx would just
                # fail again, so surface this immediately.
                raise LLMUnavailableError(
                    f"Claude API returned HTTP {e.status_code}: {e.message}"
                ) from e

        raise LLMUnavailableError(
            f"Claude API unreachable after {retries + 1} attempts. ({last})"
        ) from last


    async def generate_with_tools(
        self,
        message: str,
        system: str | list[dict],
        tools: list[dict],
        tool_executor,
        history: list[dict] | None = None,
        max_iterations: int = 5,
        on_event: StreamEvent | None = None,
    ) -> str:
        """
        Agentic loop: call Claude with tools, execute any tool_use blocks via
        tool_executor(name, input) -> str, feed results back, repeat until Claude
        stops requesting tools or max_iterations is hit.

        Every call streams. Text that precedes a tool request is preamble
        ("let me compute that"); the receiver gets a "tool" event and drops it.
        """
        messages = [*(history or []), {"role": "user", "content": message}]

        try:
            for _ in range(max_iterations):

                response = await self._stream_once(
                    self._request(system, messages, tools), 
                    on_event
                )
                messages.append({"role": "assistant", "content": response.content})

                if response.stop_reason != "tool_use":
                    reply = self._text(response)
                    self._log(response, reply)
                    return reply

                tool_results = []

                for block in response.content:

                    if block.type != "tool_use":
                        continue

                    if on_event:
                        await on_event({"type": "tool", "name": block.name})

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": tool_executor(block.name, block.input),
                    })

                messages.append({"role": "user", "content": tool_results})

        except (APIConnectionError, APITimeoutError) as e:
            raise LLMUnavailableError(f"Claude API unreachable. ({e})") from e

        except APIStatusError as e:
            raise LLMUnavailableError(
                f"Claude API returned HTTP {e.status_code}: {e.message}"
            ) from e

        logger.warning("hit max_iterations (%d) still requesting tools", max_iterations)
        return "I wasn't able to finish that calculation. Please try again."

    async def is_awake(self) -> bool:
        """No cold starts with the API -- always True if a key is configured."""
        return True


_client: ClaudeLLMClient | None = None

# Create a singleton client instance for the life of the process.
def get_llm_client() -> ClaudeLLMClient:
    """Process-wide client (construction is cheap; keeps config in one place)."""
    global _client

    if _client is None:

        _client = ClaudeLLMClient()

    return _client
