
import logging
import re
from collections.abc import Collection
from dataclasses import dataclass, field
from typing import Literal

from app.agent.prompts import (
    GENERAL_SYSTEM_PROMPT,
    LITHOLOGY_RULES,
    POROSITY_TOOL_RULE,
    RETRIEVAL_RULES,
    build_retrieval_context,
)
from app.agent.tools.rag_tools import run_geology_search
from app.core.config import settings
from app.agent.tools.xgboost_tool import (
    UNRELIABLE_CLASSES,
    run_lithology_tool,
    summarize_prediction,
)
from app.llm.anthropic_client import LLMUnavailableError, get_llm_client
from app.schemas.predictions import PredictionResponse
from app.services import prediction_service
from app.services.prediction_service import InvalidWellLogError
from app.utils.las2csv_parser import UnsupportedFormatError
from app.agent.tools import porosity_tool, rag_tools
from app.schemas.predictions import LithologyInterval
from app.petrologix.compute_porosity import WellCurves

logger = logging.getLogger(__name__)

Route = Literal["lithology", "chat"]


@dataclass
class GeoMindState:
    """State passed between nodes. One instance per request."""

    # inputs
    question: str
    well_log_path: str | None = None
    well_log_filename: str | None = None
    history: list[dict] = field(default_factory=list)
    min_thickness_m: float | None = None
    # A summary carried over from an earlier turn. Lets follow-up questions reuse
    # a prediction instead of re-running it
    prior_lithology_summary: str | None = None
    # Same idea for the intervals the porosity tool needs: a follow-up turn can
    # compute porosity without re-running the lithology model.
    prior_intervals: list[LithologyInterval] | None = None
    # Depth + RHOB cached by the session, so porosity works on a chat turn where
    # the uploaded file is long gone.
    prior_curves: WellCurves | None = None

    # populated by nodes
    route: Route | None = None
    prediction: PredictionResponse | None = None
    lithology_summary: str | None = None
    rag_context: str | None = None
    rag_hits: int = 0
    answer: str | None = None

    # observability
    llm_used: bool = False
    warnings: list[str] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)
    # for the porosity tool
    intervals: list[LithologyInterval] | None = None
    curves: WellCurves | None = None
    # Quantities a tool measured this turn, so the fabrication guard stops
    # treating them as unsourceable. A tool that returns real numbers must add
    # its own name here -- compute_porosity adds "porosity".
    computed_quantities: set[str] = field(default_factory=set)
    # Raw text of every tool result handed to the model this turn. The guards
    # check the answer against what the model was actually shown, so anything
    # missing from here gets reported as invented -- the porosity tool quoting
    # its own 0.7 confidence threshold was flagged that way.
    tool_outputs: list[str] = field(default_factory=list)

    def note(self, step: str) -> None:
        self.trace.append(step)



# nodes
def route_node(state: GeoMindState) -> GeoMindState:
    """Decide which path the request takes.

    Deterministic on purpose: presence of an uploaded file is a fact the backend
    already has, not something to ask a 7B model to infer.
    """
    if state.well_log_path:
        state.route = "lithology"
    else:
        # No new file: reuse a summary from earlier in the session if there is one.
        state.lithology_summary = state.prior_lithology_summary
        state.intervals = state.prior_intervals
        state.curves = state.prior_curves
        state.route = "chat"
    state.note(f"route={state.route}")
    
    return state


def lithology_node(state: GeoMindState) -> GeoMindState:
    """Run the well-log model and produce both structured and text output.

    Structured (`prediction`) goes to the UI for the log track; the text summary
    (~250 tokens) is what the LLM sees.
    """
    try:
        state.prediction = prediction_service.predict_from_upload(
            state.well_log_path,
            state.well_log_filename or "upload",
            include_samples=True,        # the UI plots these; the LLM never sees them
            min_thickness=state.min_thickness_m,
        )
        state.lithology_summary = summarize_prediction(state.prediction)
        status = state.prediction.distribution.status
        state.intervals = state.prediction.intervals
        state.note(f"lithology ok ({len(state.prediction.intervals)} zones, {status})")
        
        if status != "ok":
            state.warnings.append(state.prediction.distribution.message)
            
    except (InvalidWellLogError, UnsupportedFormatError) as e:
        # A rejected upload is a normal outcome, not a crash: tell the user what
        # is wrong with their file rather than failing the request.
        state.lithology_summary = f"Cannot predict: {e}"
        state.warnings.append(str(e))
        state.note("lithology rejected")
        
    except Exception:
        logger.exception("lithology node failed")
        state.lithology_summary = run_lithology_tool(state.well_log_path or "")
        state.note("lithology fallback")
        
    return state


async def retrieve_node(state: GeoMindState) -> GeoMindState:
    """Geology RAG: fetch reference passages for the question.

    Runs on every turn, not only chat turns. A lithology upload is usually
    followed by an interpretation question ("is this a reservoir?"), and that is
    exactly where the model's recall of numeric facts is weakest.

    Never raises: run_geology_search swallows its own failures, and a turn with
    no context is still a usable answer.
    """
    if not settings.rag_enabled:
        state.note("retrieve=disabled")
        return state

    question = state.question.strip()

    if len(question) < 8:
        # Too short to embed usefully ("ok", "and?"); the history has the topic
        # but the query does not, and a vague vector retrieves vague passages.
        state.note("retrieve=skipped (query too short)")
        return state

    context, hits = await run_geology_search(question)

    if context is None:
        state.note("retrieve=unavailable")
        return state

    state.rag_context = context or None
    state.rag_hits = hits
    state.note(f"retrieve={hits} passages")

    return state


async def generate_node(state: GeoMindState) -> GeoMindState:
    """Build system + user turns and call Claude.

    On LLM failure the tool summary is returned directly. The prediction is the
    expensive, trustworthy part of the answer; losing it because the API is down
    would be the wrong trade.
    """
    rules = [GENERAL_SYSTEM_PROMPT]
    blocks: list[str] = []
    question = state.question.strip()

    if state.lithology_summary:
        
        rules.append(LITHOLOGY_RULES)
        
        blocks.append(
            "Lithology prediction for the uploaded well log:\n\n"
            f"{state.lithology_summary}\n\n"
            "This table has already been shown to the user, so do not repeat it."
        )

    if state.rag_context:
        
        rules.append(RETRIEVAL_RULES)
        blocks.append(build_retrieval_context(state.rag_context))

    # The one place the model, not the backend, decides whether a tool runs:
    # "compute porosity" and "explain porosity" are the same words apart, and
    # only the model can tell them apart. Offered only when there is a log on
    # disk and zones to compute over -- otherwise the tool has nothing to read.
    tools: list[dict] = []

    if state.intervals and (state.well_log_path or state.curves):
        tools.append(porosity_tool.TOOL_SCHEMA)
        rules.append(POROSITY_TOOL_RULE)
        state.note("tool offered: compute_porosity")

    system = "\n\n".join(rules)
    user_message = "\n\n".join([*blocks, f"Question: {question}"]) if blocks else question

    state.note(f"prompt~{len(user_message) // 4}tok")

    def execute_tool(name: str, tool_input: dict) -> str:
        """Run a tool for the model. Claude never sees the LAS -- the tool reads
        it here and returns only its text summary, as the lithology tool does.
        """
        if name != porosity_tool.TOOL_SCHEMA["name"]:
            logger.warning("model requested unknown tool %r", name)
            return f"No such tool: {name}"

        try:
            summary = porosity_tool.run(state, tool_input)

        except Exception:
            # A failed tool must not lose the turn: hand the model the failure so
            # it can say so, rather than raising and dropping the whole answer.
            logger.exception("porosity tool failed")
            return (
                "The porosity calculation failed. Tell the user it could not be "
                "computed; do not estimate a value."
            )

        # Without these the guards flag the tool's own numbers as invented.
        state.computed_quantities |= porosity_tool.MEASURES
        state.tool_outputs.append(summary)
        state.note("tool: compute_porosity")

        return summary

    try:
        if tools:
            state.answer = await get_llm_client().generate_with_tools(
                user_message,
                system=system,
                tools=tools,
                tool_executor=execute_tool,
                history=state.history,
            )
        else:
            state.answer = await get_llm_client().generate(
                user_message, system=system, history=state.history
            )

        state.llm_used = True
        state.note("llm ok")
        
    except LLMUnavailableError as e:
        
        logger.warning("LLM unavailable, falling back to the tool summary: %s", e)
        state.warnings.append(
            "The geologist assistant is unavailable, so the raw model output is "
            "shown below."
        )
        state.answer = state.lithology_summary or (
            "The geologist assistant is currently not available. Please try again."
        )
        state.note("llm unavailable -> fallback")

    return state


# output guard

_NEGATION = r"(?:no|not|none|without|absent|absence of|lacks?|free of|didn't|did not|isn't|is not|wasn't|was not)"
_ABSENCE_RE = [
    re.compile(rf"\b{_NEGATION}\b[^.]{{0,60}}\b{cls}\b", re.I) for cls in UNRELIABLE_CLASSES
] + [
    re.compile(rf"\b{cls}\b[^.]{{0,40}}\b(?:{_NEGATION}|absent)\b", re.I)
    for cls in UNRELIABLE_CLASSES
]

_BLIND_SPOT_NOTE_ONE = (
    "Correction: this model cannot detect {classes}. Its absence from the result "
    "is a limitation of the model, not evidence that it is absent from the well."
)


# Language that describes the MODEL's limits rather than the WELL's contents.
# "The model cannot detect Chalk" is the correct thing to say -- appending a
# correction that says the same thing back is noise, and reads as the assistant
# arguing with itself.
_LIMITATION_RE = re.compile(
    r"\b(?:model|classifier|xgboost|it)\b[^.]{0,40}\b(?:cannot|can't|unable|"
    r"does not reliably|doesn't reliably|not reliably|fails? to)\b"
    r"|\b(?:cannot|can't|unable to|not able to)\s+(?:reliably\s+)?"
    r"(?:detect|determine|distinguish|identify|resolve|predict)\b"
    r"|\b(?:blind spot|limitation of the model|model limitation|low recall|"
    r"not reliably detected|below detection)\b",
    re.I,
)


def find_blind_spot_claims(answer: str) -> list[str]:
    """Return blind-spot lithologies the answer wrongly claims are absent.

    Sentences that frame the class as undetectable are left alone: those state
    the model's limitation, which is what the system prompt asks for. Only a
    claim about the well itself ("no dolomite is present") is corrected.
    """
    sentences = [
        s for s in re.split(r"(?<=[.!?\n])\s+", answer) if not _LIMITATION_RE.search(s)
    ]
    text = " ".join(sentences)

    return [cls for cls in UNRELIABLE_CLASSES
            if any(rx.search(text) for rx in _ABSENCE_RE if cls.lower() in rx.pattern.lower())]


# The model is given lithology, depth, thickness and confidence -- nothing else.
# It has no saturation, porosity, permeability, API gravity or net-pay data, so a
# NUMERIC claim about any of them is fabricated by construction.
_UNSUPPORTED_QUANTITIES = [
    "porosity", "permeability", "saturation", "api gravity", "net pay",
    "net-to-gross", "net to gross", "toc", "water cut", "pore pressure",
    "reserves", "flow rate", "viscosity",
]
# Require a digit within ~40 characters, so "the model does not report porosity"
# is not flagged while "17.0 porosity" is.
_QUANTITY_RE = [
    (q, re.compile(rf"(?:\d[\d.,]*\s*%?[^.]{{0,40}}\b{re.escape(q)}\b"
                   rf"|\b{re.escape(q)}\b[^.]{{0,40}}\d[\d.,]*)", re.I))
    for q in _UNSUPPORTED_QUANTITIES
]

_FABRICATION_NOTE = (
    "Correction: the lithology model provides only rock type, depth and "
    "confidence. It has no {quantities} data."
)

_FABRICATION_NOTE_WITH_RAG = (
    "Correction: the figures above for {quantities} are uncited. The lithology "
    "model provides only rock type, depth and confidence, and no reference "
    "passage was credited for them."
)

_FORMULA_REQUEST_RE = re.compile(
    r"\b(equation|formula|how (?:do you|is it) calculat(?:e|ing|ion)?|how to calculate|"
    r"derive|what is the (?:equation|formula)|worked example)\b",
    re.I,
)


def is_formula_request(question: str) -> bool:
    """True when the user asks for a general equation or derivation rather than
    an interpretation of this well's specific measured properties. Worked
    examples in a formula answer use illustrative numbers, not claims about
    the well, so the unsupported-quantity guard should not fire on them.
    """
    return bool(_FORMULA_REQUEST_RE.search(question))


# A bracketed passage number, e.g. "[2]". RETRIEVAL_RULES require one next to any
# fact taken from the corpus.
_CITATION_RE = re.compile(r"\[\d{1,2}\]")


def _uncited_text(answer: str) -> str:
    """The answer minus every sentence that cites a retrieved passage.

    With RAG on, a number can legitimately come from the corpus -- a typical
    porosity range for a formation, say. The fabrication guard is about numbers
    the model cannot source, so cited sentences are out of its scope; uncited
    ones are still fabricated by construction.
    """
    kept = [s for s in re.split(r"(?<=[.!?\n])\s+", answer) if not _CITATION_RE.search(s)]

    return " ".join(kept)


def find_unsupported_quantities(
    answer: str,
    has_context: bool = False,
    computed: Collection[str] | None = None,
) -> list[str]:
    """Return petrophysical quantities the answer quotes numbers for but cannot know.

    has_context : retrieved passages were in the prompt, so cited sentences are
        exempt. Without them every such number is unsourced.
    computed : quantities a tool actually measured this turn (e.g. "porosity"
        once compute_porosity has run). The premise of this guard is that the
        model was handed nothing but lithology, depth and confidence -- once a
        tool supplies a real figure that premise no longer holds, and flagging
        it would have the agent call its own measurement fabricated.
    """
    text = _uncited_text(answer) if has_context else answer
    exempt = {q.lower() for q in (computed or ())}

    return sorted(
        {q for q, rx in _QUANTITY_RE if q not in exempt and rx.search(text)}
    )


_CONFIDENCE_RE = re.compile(
    r"\b(?:confidence|probability|certainty)\b[^.\n]{0,30}?(\d\d?\d?(?:\.\d+)?)\s*(%?)"
    r"|(\d\d?\d?(?:\.\d+)?)\s*(%?)[^.\n]{0,20}?\b(?:confidence|probability|certainty)\b",
    re.I,
)
_SUMMARY_NUMBER_RE = re.compile(r"\b(0\.\d+|1\.0+)\b")

_NO_PREDICTION_NOTE = (
    "Correction: no well log has been analysed in this session, so the "
    "confidence figures above were not produced by the lithology model. "
    "Disregard them and upload a log to get a real prediction."
)
_MISMATCHED_CONFIDENCE_NOTE = (
    "Correction: the confidence values {values} do not appear in this well's "
    "prediction. Trust the measured result above, not these figures. "
)
_THRESHOLD_RE = re.compile(
    r"\b(?:below|above|under|over|less than|greater than|at least|at most|"
    r"exceeds?|threshold|beneath)\b",
    re.I,
)


def _confidence_values(answer: str) -> list[float]:
    """Every confidence-like figure in the answer, normalised to 0-1."""
    found: list[float] = []
    
    for m in _CONFIDENCE_RE.finditer(answer):
        
        if _THRESHOLD_RE.search(m.group(0)):
            continue
        
        raw, pct = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        try:
            value = float(raw)
            
        except (TypeError, ValueError):
            continue
        
        if pct == "%" or value > 1:
            value /= 100.0
            
        found.append(value)
        
    return found


def find_unsupported_confidence(
    answer: str,
    lithology_summary: str | None,
    tool_outputs: Collection[str] = (),
) -> tuple[bool, list[str]]:
    """Check confidence claims against the figures the model was actually given.

    Returns (no_prediction_at_all, mismatched_values). Matching is exact to two
    decimals -- the precision the summary prints.

    tool_outputs : every other tool result shown to the model this turn. Without
        them the guard only knows the lithology summary and reports any other
        real figure as invented -- the porosity tool quoting its own 0.7
        confidence threshold was flagged exactly that way.
    """
    claimed = _confidence_values(answer)

    if not claimed:
        return False, []

    if not lithology_summary:
        return True, []

    sources = [lithology_summary, *tool_outputs]
    shown = {
        round(float(m), 2)
        for text in sources
        for m in _SUMMARY_NUMBER_RE.findall(text)
    }
    mismatched = [f"{c:.2f}" for c in claimed if round(c, 2) not in shown]
    
    return False, sorted(set(mismatched))


def guard_node(state: GeoMindState) -> GeoMindState:
    """Append corrections for claims the answer cannot support."""
    if not state.answer or not state.llm_used:
        return state

    notes: list[str] = []

    no_prediction, mismatched = find_unsupported_confidence(
        state.answer, state.lithology_summary, state.tool_outputs
    )
    if no_prediction:
        notes.append(_NO_PREDICTION_NOTE)
        state.note("guard: confidence claimed with no prediction")
        logger.error("model quoted confidence with no prediction in session")
        
    elif mismatched:
        notes.append(_MISMATCHED_CONFIDENCE_NOTE.format(values=", ".join(mismatched)))
        state.note(f"guard: mismatched confidence ({', '.join(mismatched)})")
        logger.error("model quoted confidence %s absent from prediction", mismatched)

    if not state.lithology_summary:
        
        if notes:
            state.answer = "\n\n".join([state.answer.rstrip(), *notes])
            state.warnings.extend(notes)
            
        return state

    claimed = find_blind_spot_claims(state.answer)
    
    _BLIND_SPOT_NOTE_ONE = (
        "Correction: this model cannot detect {classes}. Its absence from the result "
        "is a limitation of the model, not evidence that it is absent from the well."
    )
    _BLIND_SPOT_NOTE_MANY = (
        "Correction: this model cannot detect {classes}. Their absence from the "
        "result is a limitation of the model, not evidence that they are absent "
        "from the well."
    )
    if claimed:
        
        template = _BLIND_SPOT_NOTE_ONE if len(claimed) == 1 else _BLIND_SPOT_NOTE_MANY
        notes.append(template.format(classes=", ".join(claimed)))
        state.note(f"guard: corrected absence claim ({', '.join(claimed)})")
        logger.warning("model claimed %s absent; correction appended", claimed)

    if not is_formula_request(state.question):
        
        invented = find_unsupported_quantities(
            state.answer,
            has_context=bool(state.rag_context),
            computed=state.computed_quantities,
        )
        
        if invented:
            note = (
                _FABRICATION_NOTE_WITH_RAG if state.rag_context else _FABRICATION_NOTE
            )
            notes.append(note.format(quantities=", ".join(invented)))
            state.note(f"guard: flagged fabricated quantities ({', '.join(invented)})")
            logger.error("model quoted unsupported quantities %s -- fabricated", invented)
    else:
        state.note("guard: skipped quantity check (formula request)")

    if notes:
        state.answer = "\n\n".join([state.answer.rstrip(), *notes])
        state.warnings.extend(notes)

    return state


# graph
@dataclass
class GeoMindResult:
    """What a caller (router/service) gets back."""

    answer: str
    prediction: PredictionResponse | None
    llm_used: bool
    warnings: list[str]
    trace: list[str]
    rag_hits: int = 0
    # Carried out so the caller can cache it and reuse it on follow-up turns
    # without re-running the model or asking the user to re-upload.
    lithology_summary: str | None = None


async def run(
    question: str,
    well_log_path: str | None = None,
    well_log_filename: str | None = None,
    history: list[dict] | None = None,
    min_thickness_m: float | None = None,
    prior_lithology_summary: str | None = None,
    prior_intervals: list[LithologyInterval] | None = None,
    prior_curves: WellCurves | None = None,
) -> GeoMindResult:
    """Execute the flow.

        route -> [lithology] -> generate -> guard

    (retrieve is disconnected -- see the commented call below.)

    Both structured prediction and prose answer come back, so the caller can
    render the log track and the chat bubble from one request.
    """
    state = GeoMindState(
        question=question,
        well_log_path=well_log_path,
        well_log_filename=well_log_filename,
        history=history or [],
        min_thickness_m=min_thickness_m,
        prior_lithology_summary=prior_lithology_summary,
        prior_intervals=prior_intervals,
        prior_curves=prior_curves,
    )

    state = route_node(state)
    
    if state.route == "lithology":
        state = lithology_node(state)
        
    # RAG is disconnected from the flow: the retrieved passages were degrading
    # answers rather than grounding them. retrieve_node and app/rag/ are left
    # intact -- re-enable by restoring this call (and RAG_ENABLED=true).
    # state = await retrieve_node(state)
    state = await generate_node(state)
    state = guard_node(state)

    logger.info("graph: %s", " -> ".join(state.trace))
    
    return GeoMindResult(
        answer=state.answer or "",
        prediction=state.prediction,
        llm_used=state.llm_used,
        lithology_summary=state.lithology_summary,
        warnings=state.warnings,
        trace=state.trace,
        rag_hits=state.rag_hits,
    )
