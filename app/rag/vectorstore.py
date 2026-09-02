"""Qdrant Cloud connection for the geology corpus.

One async client for the process. The collection is read-only from the backend's
point of view -- ingestion happens offline, so nothing here creates or writes to
a collection.
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorStoreUnavailableError(RuntimeError):
    """Qdrant is unconfigured, unreachable, or missing the collection."""


_client = None


def get_client():
    """Process-wide AsyncQdrantClient.

    qdrant-client is imported lazily so a deployment without RAG configured does
    not need the dependency installed at all.
    """
    global _client

    if _client is not None:
        return _client

    if not settings.qdrant_url:
        raise VectorStoreUnavailableError(
            "no Qdrant URL configured -- set QDRANT_URL in .env"
        )

    try:
        from qdrant_client import AsyncQdrantClient

    except ImportError as e:
        raise VectorStoreUnavailableError(
            "qdrant-client is not installed -- pip install -r requirements.txt"
        ) from e

    _client = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=settings.qdrant_timeout_s,
    )
    logger.info("qdrant client created for %s", settings.qdrant_url)

    return _client


async def check_collection() -> dict:
    """Verify the collection exists and its vector size matches the embedder.

    Called at startup. A dimension mismatch means the collection was built with a
    different encoder, which retrieves plausible-looking nonsense rather than
    failing -- so it is worth one round trip to catch it.
    """
    from app.rag.embeddings import EMBED_DIM

    client = get_client()
    name = settings.qdrant_collection

    try:
        info = await client.get_collection(name)

    except Exception as e:
        raise VectorStoreUnavailableError(
            f"collection '{name}' is not readable: {e}"
        ) from e

    vectors = info.config.params.vectors
    # Named-vector collections expose a dict; unnamed ones a single config.
    size = (
        vectors.size
        if hasattr(vectors, "size")
        else next(iter(vectors.values())).size
    )

    if size != EMBED_DIM:
        raise VectorStoreUnavailableError(
            f"collection '{name}' has {size}-dim vectors but the embedder "
            f"produces {EMBED_DIM} -- they were built with different models"
        )

    return {"collection": name, "vector_size": size, "points": info.points_count}


async def aclose() -> None:
    global _client

    if _client is not None:
        await _client.close()
        _client = None
