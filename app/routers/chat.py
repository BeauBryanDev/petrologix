
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.chats import ChatRequest, ChatResponse, SessionInfo
from app.services import chat_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])
"""Chat endpoints for the geologist assistant."""

# The chat endpoint is the main entry point for the geologist assistant.
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Ask the geologist assistant a question.

    Pass the `session_id` returned by `POST /predict?session_id=...` to ask about
    a well log analysed earlier; without it the assistant has no well context and
    answers from the fine-tuned model's geology knowledge alone.

    Always returns 200 when the request is well-formed. If the LLM Space is
    asleep, `llm_used` is false and `answer` carries the raw model summary rather
    than failing the request.
    """
    try:
        return await chat_service.chat(request)
    # The LLM is unavailable, so the request is a no-op. The frontend can retry
    # later, but the backend does not need to retry the request itself.
    except Exception:
        
        logger.exception("chat failed")
        raise HTTPException(500, "chat failed")

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """The same turn as POST /chat, streamed as server-sent events.

    Events: `delta` (text chunk), `tool` (a tool is running; discard text so
    far), `done` (the full ChatResponse, corrections included), `error`.
    """
    return StreamingResponse(
        chat_service.chat_stream(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# The session info endpoint is not documented because it is not used by the
# demo frontend. It is used by the agent to remember the well context.
@router.get("/chat/session/{session_id}", response_model=SessionInfo)
def session_info(session_id: str) -> SessionInfo:
    """What the assistant currently remembers about a session."""
    info = chat_service.store.info(session_id)
    
    if info is None:
        
        raise HTTPException(404, f"unknown or expired session: {session_id}")
    
    return info
