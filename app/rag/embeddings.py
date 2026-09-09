
import asyncio
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBED_DIM = 1024

# Query embeddings for the geology RAG.

# BAAI/bge-large-en-v1.5, 1024 dimensions -- the same model the Qdrant collection
# was built with. Swapping it silently would make every retrieval garbage, so the
# dimension is asserted on the first call rather than trusted.
class EmbeddingUnavailableError(RuntimeError):
    """The embedding endpoint is unreachable or returned an error."""


class BGEEmbedder:
    """Async client for a hosted feature-extraction endpoint."""

    def __init__(
        self,
        endpoint: str | None = None,
        token: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.endpoint = (endpoint or settings.embedding_endpoint or "").rstrip("/")

        if not self.endpoint:
            raise EmbeddingUnavailableError(
                "no embedding endpoint configured -- set EMBEDDING_ENDPOINT in .env"
            )

        self.token = token or settings.embedding_token or settings.hf_token
        self._timeout = timeout or settings.embedding_timeout_s
        self._client = httpx.AsyncClient(timeout=self._timeout)

    async def embed(self, text: str, retries: int = 2) -> list[float]:
        """Embed one query string.

        bge asks for a retrieval instruction on the QUERY side only; passages are
        embedded bare. The collection holds passages, so the prefix goes here.
        """
        payload = {
            "inputs": settings.embedding_query_prefix + text,
            "options": {"wait_for_model": True},
        }
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

        last: Exception | None = None

        for attempt in range(retries + 1):
            try:
                r = await self._client.post(self.endpoint, 
                                            json=payload, 
                                            headers=headers)
                r.raise_for_status()
                return _as_vector(r.json())

            except (httpx.HTTPError, ValueError) as e:
                last = e
                logger.warning("embedding attempt %d failed: %s", attempt + 1, e)

                if attempt < retries:
                    # A cold serverless endpoint 503s while it loads.
                    await asyncio.sleep(2 * (attempt + 1))

        raise EmbeddingUnavailableError(f"embedding endpoint failed: {last}") from last

    async def aclose(self) -> None:
        await self._client.aclose()


def _as_vector(data) -> list[float]:
    """Normalise the response shape to one flat 1024-float vector.

    Feature-extraction endpoints return either [dim] for a single input, [1][dim]
    when the input was batched, or [1][tokens][dim] when the model has no pooling
    layer configured. Only the first two are usable -- token-level output means
    the endpoint is misconfigured and mean-pooling it here would produce vectors
    that do not match how the collection was embedded.
    """
    vec = data

    if isinstance(vec, list) and vec and isinstance(vec[0], list):
        if vec[0] and isinstance(vec[0][0], list):
            raise ValueError(
                "endpoint returned token-level embeddings; it must apply sentence "
                "pooling to match the collection"
            )
        vec = vec[0]

    if not isinstance(vec, list) or len(vec) != EMBED_DIM:
        raise ValueError(
            f"expected a {EMBED_DIM}-dim vector, got {type(vec).__name__} "
            f"of length {len(vec) if isinstance(vec, list) else 'n/a'}"
        )

    return [float(x) for x in vec]


_embedder: BGEEmbedder | None = None


def get_embedder() -> BGEEmbedder:
    """Process-wide embedder. Raises EmbeddingUnavailableError if unconfigured."""
    global _embedder

    if _embedder is None:
        _embedder = BGEEmbedder()

    return _embedder
