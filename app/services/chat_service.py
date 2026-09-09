
import asyncio
import json
import logging
import pickle
import tempfile
import time
import uuid

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

from app.agent import graph
from app.petrologix import compute_porosity
from app.petrologix.compute_porosity import WellCurves
from app.schemas.chats import ChatRequest, ChatResponse, SessionInfo
from app.schemas.predictions import LithologyInterval, PredictionResponse

logger = logging.getLogger(__name__)
"""Chat orchestration and per-session well context.
"""
SESSION_TTL_SECONDS = 60 * 60 * 4      # 4 hours
MAX_SESSIONS = 500
# Sessions are mirrored here so they survive a worker restart. Under
# `uvicorn --reload` every file save restarts the process and an in-memory
# store loses the well the user just uploaded -- the next chat turn then has no
# intervals, the porosity tool is never offered, and the model rightly says it
# has no curves.
SESSION_DIR = Path(tempfile.gettempdir()) / "aegis-geo-mind-sessions"


@dataclass
class SessionState:
    session_id: str
    created_at: float = field(default_factory=time.time)
    lithology_summary: str | None = None
    well_name: str | None = None
    n_intervals: int | None = None
    dominant_lithology: str | None = None
    mean_confidence: float | None = None
    # What the porosity tool needs on a follow-up turn. The upload is a temp
    # file the router deletes when the request ends, so the zones and the two
    # curves are kept here instead -- roughly 170 KB per well.
    intervals: list[LithologyInterval] = field(default_factory=list)
    curves: WellCurves | None = None


class SessionStore:
    """In-memory session cache with TTL and a hard size cap."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {} # session_id -> state

    @staticmethod
    def _path(session_id: str) -> Path:
        return SESSION_DIR / f"{session_id}.pkl"

    def _persist(self, state: SessionState) -> None:
        try:
            SESSION_DIR.mkdir(parents=True, exist_ok=True)
            self._path(state.session_id).write_bytes(pickle.dumps(state))

        except Exception:
            logger.exception("could not persist session %s", state.session_id)

    def _load(self, session_id: str) -> SessionState | None:
        path = self._path(session_id)

        if not path.is_file():
            return None

        try:
            state = pickle.loads(path.read_bytes())

        except Exception:
            logger.warning("discarding unreadable session file %s", path)
            path.unlink(missing_ok=True)
            return None

        if time.time() - state.created_at > SESSION_TTL_SECONDS:
            path.unlink(missing_ok=True)
            return None

        return state

    def _drop(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._path(session_id).unlink(missing_ok=True)

    def _evict(self) -> None:
        now = time.time()
        expired = [k for k, v in self._sessions.items()
                   if now - v.created_at > SESSION_TTL_SECONDS]
        
        for k in expired:
            
            self._drop(k)
        # Hard cap as a backstop against a burst of sessions inside the TTL.
        while len(self._sessions) > MAX_SESSIONS:
            
            oldest = min(self._sessions, key=lambda k: self._sessions[k].created_at)
            
            self._drop(oldest)

    def get(self, session_id: str | None) -> SessionState | None:
        
        if not session_id:
            
            return None
        
        self._evict()

        state = self._sessions.get(session_id)

        if state is None:
            # A fresh process after a reload: the well may still be on disk.
            state = self._load(session_id)

            if state is not None:
                self._sessions[session_id] = state
                logger.info("session %s restored from disk", session_id)
        
        return state

    def create(self, session_id: str | None = None) -> SessionState:
        
        self._evict()
        
        sid = session_id or uuid.uuid4().hex[:16]
        state = self._sessions.get(sid) or SessionState(session_id=sid)
        self._sessions[sid] = state
        
        return state

    def attach_prediction(
        self,
        session_id: str,
        prediction: PredictionResponse,
        summary: str,
        well_log_path: str | None = None,
        well_log_filename: str | None = None,
    ) -> SessionState:
        """Record a prediction so later chat turns can refer to it.

        Pass the upload's path to keep porosity available on later turns: the
        curves are read here, while the file still exists, because the caller
        deletes it as soon as the request finishes.
        """
        state = self.get(session_id) or self.create(session_id)
        state.lithology_summary = summary
        state.well_name = prediction.well_name
        state.n_intervals = len(prediction.intervals)
        state.intervals = list(prediction.intervals)

        if well_log_path:

            try:
                state.curves = compute_porosity.extract_curves(
                    well_log_path, well_log_filename or prediction.well_name
                )

            except Exception:
                # Losing the curves costs the porosity tool on later turns; it
                # must not cost the prediction the user just paid for.
                logger.exception("could not cache curves for session %s", session_id)
                state.curves = None
        
        if prediction.intervals:
            
            total = sum(i.thickness for i in prediction.intervals) or 1.0
            by_lith: dict[str, float] = {}
            
            for iv in prediction.intervals:
                
                by_lith[iv.lithology] = by_lith.get(iv.lithology, 0.0) + iv.thickness
                
            state.dominant_lithology = max(by_lith, key=by_lith.get)
            state.mean_confidence = round(
                sum(i.confidence * i.thickness for i in prediction.intervals) / total, 3
            )
        logger.info("session %s: attached %s (%d zones)",
                    session_id, state.well_name, state.n_intervals or 0)
        self._persist(state)
        
        return state


    def info(self, session_id: str) -> SessionInfo | None:
        state = self.get(session_id)
        
        if not state:
            
            return None
        
        return SessionInfo(
            session_id=state.session_id,
            has_well_context=state.lithology_summary is not None,
            well_name=state.well_name,
            n_intervals=state.n_intervals,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(state.created_at)),
        )


store = SessionStore()


async def chat(request: ChatRequest, on_event=None) -> ChatResponse:
    """Answer one chat turn, using the session's well context when present.

    on_event, when given, receives the model's text as it streams; the
    returned answer is still the complete, guard-corrected text.
    """
    state = store.get(request.session_id) or store.create(request.session_id)

    result = await graph.run(
        question=request.message,
        history=[t.model_dump() for t in request.history],
        prior_lithology_summary=state.lithology_summary,
        # Carried so the porosity tool can run on this turn without the upload.
        prior_intervals=state.intervals or None,
        prior_curves=state.curves,
        on_event=on_event,
    )

    return ChatResponse(
        answer=result.answer,
        session_id=state.session_id,
        llm_used=result.llm_used,
        rag_hits=result.rag_hits,
        has_well_context=state.lithology_summary is not None,
        warnings=result.warnings,
        dominant_lithology=state.dominant_lithology,
        mean_confidence=state.mean_confidence,
        trace=result.trace,
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def chat_stream(request: ChatRequest) -> AsyncIterator[str]:
    """The same turn as chat(), as server-sent events.

    delta  {"text"}   a chunk of the model's answer, in order
    tool   {"name"}   a tool is running; text streamed so far was preamble
    done   ChatResponse, with the guard corrections appended -- the client
                      replaces what it has assembled with this answer
    error  {"detail"}

    The graph runs in a task and events pass through a queue, so the model's
    text reaches the client while the turn is still in progress.
    """
    queue: asyncio.Queue = asyncio.Queue()

    async def on_event(event: dict) -> None:
        await queue.put(event)

    async def run() -> None:
        try:
            response = await chat(request, on_event=on_event)
            await queue.put({"type": "done", "response": response.model_dump()})

        except Exception:
            logger.exception("chat stream failed")
            await queue.put({"type": "error", "detail": "chat failed"})

    task = asyncio.create_task(run())

    try:
        while True:
            event = await queue.get()
            kind = event.pop("type")
            payload = event["response"] if kind == "done" else event
            yield _sse(kind, payload)

            if kind in ("done", "error"):
                return

    finally:
        # A client that disconnects mid-answer should not leave the turn running.
        if not task.done():
            task.cancel()
