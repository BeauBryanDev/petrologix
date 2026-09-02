
from fastapi import APIRouter

from app.core.config import settings
from app.petrologix.loader import get_model
from app.rag import vectorstore

router = APIRouter(tags=["health"])
"""Liveness and readiness."""

@router.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


@router.get("/ready")
async def ready() -> dict:
    """Ready means the lithology model is loaded and usable.

    RAG state is reported but never gates readiness -- the agent degrades to
    answering without retrieval rather than going down.
    """
    bundle = get_model()

    rag: dict = {"enabled": settings.rag_enabled and bool(settings.qdrant_url)}

    if rag["enabled"]:
        try:
            rag |= await vectorstore.check_collection()
            rag["status"] = "ok"

        except Exception as e:  # noqa: BLE001
            rag["status"] = "unavailable"
            rag["message"] = str(e)
    else:
        rag["status"] = "disabled"

    return {
        "status": "ready",
        "model_version": bundle["version"],
        "model_classes": len(bundle["classes_name"]),
        "rag": rag,
    }
