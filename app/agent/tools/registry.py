
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from app.agent.tools import ( market_tools,
                             ooip_tool,
                             porosity_tool,
                             rag_tools,
                             rock_properties_tool )

logger = logging.getLogger(__name__)

# Adapters take the request state and the model's input, and return the text the
# model sees. Async because the corpus search is an HTTP call.
ToolRunner = Callable[[object, dict], Awaitable[str]]

# The model decides which of these runs, not the backend. Lithology is the
# deliberate exception: it stays on lithology_node because its output also fills
# state.prediction.

@dataclass(frozen=True)
class Tool:
    schema: dict
    run: ToolRunner
    # Quantities this tool measures. Dropped from the fabrication guard for the
    # turn, or the guard calls the tool's own output invented.
    measures: set[str] = field(default_factory=set)

    @property
    def name(self) -> str:
        return self.schema["name"]


async def _run_porosity(state, tool_input: dict) -> str:
    return porosity_tool.run(state, tool_input)


async def _run_ooip(state, tool_input: dict) -> str:
    return ooip_tool.run(tool_input)


async def _run_market(state, tool_input: dict) -> str:
    return market_tools.run(tool_input)


async def _run_rock_properties(state, tool_input: dict) -> str:
    return rock_properties_tool.run(tool_input)

# this is the Geogloy corpus -> context adapter
async def _run_geology_search(state, tool_input: dict) -> str:
    """
    Search the corpus and record the hit on the state.

    Sets rag_context because the fabrication guard uses it to decide whether a
    [n]-cited number can be legitimately sourced. 
    """
    # Hard stop behind MATH_RULES: the corpus maths is unreadable OCR.
    if not state.corpus_available:
        return (
            "The corpus cannot serve this question. Answer from your own "
            "knowledge and cite nothing."
        )

    query = (tool_input.get("query") or "").strip()

    if len(query) < 8:
        # Too short to embed usefully; a vague vector retrieves vague passages.
        return "That query is too short to search with. Use a fuller question."

    context, hits = await rag_tools.run_geology_search(query)

    if context is None:
        return (
            "The geology corpus is unavailable right now. Answer from your own "
            "knowledge and say the reference corpus was not consulted."
        )

    if not context:
        return (
            "The corpus returned no relevant passages. Answer from your own "
            "knowledge, marked as such, and cite nothing."
        )

    # Accumulate: a second search adds to the first rather than replacing it.
    state.rag_context = f"{state.rag_context}\n\n{context}" if state.rag_context else context
    state.rag_hits += hits

    return context


# The model decides which of these runs, not the backend.
TOOLS: tuple[Tool, ...] = ( # the tools Agent[Claude] decides to run
    Tool(porosity_tool.TOOL_SCHEMA, _run_porosity, porosity_tool.MEASURES),
    Tool(ooip_tool.TOOL_SCHEMA, _run_ooip, ooip_tool.MEASURES),
    Tool(market_tools.TOOL_SCHEMA, _run_market, market_tools.MEASURES),
    Tool(rock_properties_tool.TOOL_SCHEMA, _run_rock_properties, rock_properties_tool.MEASURES),
    Tool(rag_tools.GEOLOGY_SEARCH_TOOL_SPEC, _run_geology_search),
)

BY_NAME: dict[str, Tool] = {t.name: t for t in TOOLS}

SCHEMAS: list[dict] = [t.schema for t in TOOLS]
