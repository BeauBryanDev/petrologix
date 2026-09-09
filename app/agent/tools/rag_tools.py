
import logging

from app.rag.embeddings import EmbeddingUnavailableError
from app.rag.retriever import format_context, retrieve
from app.rag.vectorstore import VectorStoreUnavailableError

# Geology RAG as an agent tool.
# Wrap app.rag.retriever.retrieve for the agent to call.
logger = logging.getLogger(__name__)

# Ready for when the model chooses its own tools; the graph calls retrieve
# deterministically for now, as it does with lithology.
GEOLOGY_SEARCH_TOOL_SPEC = {
    "name": "search_geology_corpus",
    "description": (
        "Search a curated petroleum-geology reference corpus for passages "
        "relevant to a question. Use it for definitions, equations, typical "
        "property ranges and depositional-environment facts, rather than "
        "answering from memory."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The geological question or topic to look up.",
            }
        },
        "required": ["query"],
    },
}

# This is what the LLM sees
async def run_geology_search(question: str, top_k: int | None = None) -> tuple[str | None, int]:
    """Return (formatted context, passage count). ("", 0) means no usable hits.

    Returns None for context when RAG is unconfigured or failed, so the caller
    can distinguish "the corpus had nothing" from "the corpus was not consulted".
    """
    try:
        passages = await retrieve(question, top_k=top_k)

    except (EmbeddingUnavailableError, VectorStoreUnavailableError) as e:
        logger.warning("rag unavailable: %s", e)
        return None, 0

    except Exception:
        logger.exception("rag search failed")
        return None, 0

    if not passages:
        return "", 0

    return format_context(passages), len(passages)
