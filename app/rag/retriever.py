"""Retrieval over the geology corpus.

RAG is here for one measured reason: the fine-tune reproduces expert register
reliably but states specific numeric facts wrong with high confidence. Retrieved
passages give the model a source for those facts instead of its own weights.
"""

import logging
from dataclasses import dataclass

from app.core.config import settings
from app.rag.embeddings import EmbeddingUnavailableError, get_embedder
from app.rag.vectorstore import VectorStoreUnavailableError, get_client

logger = logging.getLogger(__name__)

# Payload keys vary by how the corpus was ingested; the first one present wins.
_TEXT_KEYS = ("text", "page_content", "content", "chunk", "body")
_SOURCE_KEYS = ("source_doc", "source", "document", "file_name", "url")
# Appended to the source when present, so a citation names the section and not
# just a 600-page handbook.
_SECTION_KEYS = ("section_title", "title", "heading")


@dataclass
class Passage:
    text: str
    source: str | None
    score: float


def _payload_field(payload: dict, keys: tuple[str, ...]) -> str | None:
    for k in keys:
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


async def retrieve(question: str, top_k: int | None = None) -> list[Passage]:
    """Embed the question and return the closest passages above the threshold.

    Raises EmbeddingUnavailableError / VectorStoreUnavailableError so the caller
    can decide whether a retrieval failure is fatal. In the graph it is not.
    """
    k = top_k or settings.rag_top_k
    vector = await get_embedder().embed(question)

    # ~14% of the corpus is near-duplicate chunks (the same passage ingested from
    # two OCR passes), so ask for more than k and drop the repeats below --
    # otherwise a query spends most of its slots on one document.
    hits = await get_client().query_points(
        collection_name=settings.qdrant_collection,
        query=vector,
        limit=k * settings.rag_overfetch,
        score_threshold=settings.rag_score_threshold,
        with_payload=True,
    )

    passages: list[Passage] = []
    seen: set[str] = set()

    for point in hits.points:
        payload = point.payload or {}
        text = _payload_field(payload, _TEXT_KEYS)

        if not text:
            # A point with no readable text is an ingestion bug, not a miss.
            logger.warning(
                "qdrant point %s has no text field (keys: %s)",
                point.id,
                sorted(payload),
            )
            continue

        # Dedup on a normalised text prefix rather than parent_id: the duplicate
        # pairs are separate parents, and identical text is the actual problem.
        fingerprint = "".join(text.split())[:200].lower()

        if fingerprint in seen:
            continue

        seen.add(fingerprint)

        source = _payload_field(payload, _SOURCE_KEYS)
        section = _payload_field(payload, _SECTION_KEYS)

        if section and len(section) > settings.rag_max_section_chars:
            # Ingestion concatenated every heading on the page into section_title,
            # so some run to hundreds of characters. Keep the first heading.
            section = section.split(" / ")[0][: settings.rag_max_section_chars]

        if source and section:
            source = f"{source} — {section}"
        else:
            source = source or section

        if len(passages) >= k:
            break

        passages.append(
            Passage(
                text=text[: settings.rag_max_chars_per_passage],
                source=source,
                score=point.score,
            )
        )

    logger.info(
        "rag: %d passages (k=%d, %d hits, threshold %.2f)",
        len(passages), k, len(hits.points), settings.rag_score_threshold,
    )

    return passages


def format_context(passages: list[Passage]) -> str:
    """Render passages as numbered, attributed blocks.

    Numbered so the system prompt can tell the model to cite [1], [2] -- an
    unattributed blob is indistinguishable from the model's own recall, which is
    exactly the confusion RAG is supposed to remove here.
    """
    blocks = []

    for i, p in enumerate(passages, 1):
        header = f"[{i}] {p.source}" if p.source else f"[{i}]"
        blocks.append(f"{header}\n{p.text}")

    return "\n\n".join(blocks)
