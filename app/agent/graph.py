
import logging
import re
from collections.abc import Collection
from dataclasses import dataclass, field
from typing import Literal

from app.agent.prompts import (
    GENERAL_SYSTEM_PROMPT,
    GEOLOGY_SEARCH_RULE,
    LITHOLOGY_RULES,
    MARKET_TOOL_RULE,
    MATH_RULES,
    NO_WELL_RULE,
    OOIP_TOOL_RULE,
    POROSITY_TOOL_RULE,
)
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
from app.agent.tools import registry
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
    # Hard stop behind MATH_RULES: the corpus cannot serve equations.
    corpus_available: bool = True
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
    # treating them as unsourceable.
    computed_quantities: set[str] = field(default_factory=set)
    # Raw text of every tool result handed to the model this turn. The guards
    # check the answer against what the model was actually shown, so anything
    # missing from here gets reported as invented .
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


async def generate_node(state: GeoMindState, on_event=None) -> GeoMindState:
    """Build system + user turns and call Claude.

    On LLM failure the tool summary is returned directly. The prediction is the
    expensive, trustworthy part of the answer; losing it because the API is down
    would be the wrong trade.
    """
    question = state.question.strip()

    # Byte-identical every turn, so it stays in the cached prefix with the tool
    # schemas. Per-turn rules go in the second block or the cache misses.
    stable_rules = [
        GENERAL_SYSTEM_PROMPT,
        POROSITY_TOOL_RULE,
        OOIP_TOOL_RULE,
        MARKET_TOOL_RULE,
        GEOLOGY_SEARCH_RULE,
    ]
    turn_rules: list[str] = []
    blocks: list[str] = []

    if state.lithology_summary:

        turn_rules.append(LITHOLOGY_RULES)

        blocks.append(
            "Lithology prediction for the uploaded well log:\n\n"
            f"{state.lithology_summary}\n\n"
            "This table has already been shown to the user, so do not repeat it."
        )

    # The tool list never changes, so this is how compute_porosity is withdrawn.
    if not (state.intervals and (state.well_log_path or state.curves)):
        turn_rules.append(NO_WELL_RULE)

    if is_formula_request(question):
        turn_rules.append(MATH_RULES)
        state.corpus_available = False
        state.note("math: answering from model knowledge")

    if not settings.rag_enabled:
        state.corpus_available = False

    system = [
        {"type": "text", "text": "\n\n".join(stable_rules),
         "cache_control": {"type": "ephemeral"}},
    ]
    if turn_rules:
        system.append({"type": "text", "text": "\n\n".join(turn_rules)})

    user_message = "\n\n".join([*blocks, f"Question: {question}"]) if blocks else question

    state.note(f"prompt~{len(user_message) // 4}tok")

    async def execute_tool(name: str, tool_input: dict) -> str:
        """Run whichever tool the model picked. Claude never sees the LAS --
        the tool reads it here and returns only its text summary."""
        tool = registry.BY_NAME.get(name)

        if tool is None:
            logger.warning("model requested unknown tool %r", name)
            return f"No such tool: {name}"

        try:
            summary = await tool.run(state, tool_input)

        except Exception:
            # A failed tool must not lose the turn: hand the model the failure so
            # it can say so, rather than raising and dropping the whole answer.
            logger.exception("tool %s failed", name)
            return (
                f"The {name} tool failed. Tell the user it could not be "
                "computed; do not estimate a value."
            )

        # Without these the guards flag the tool's own numbers as invented.
        state.computed_quantities |= tool.measures
        state.tool_outputs.append(summary)
        state.note(f"tool: {name}")

        return summary

    try:
        state.answer = await get_llm_client().generate_with_tools(
            user_message,
            system=system,
            tools=registry.SCHEMAS,
            tool_executor=execute_tool,
            history=state.history,
            on_event=on_event,
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
    r"\b(equation|formula|expression for|how (?:do you|is it) calculat(?:e|ing|ion)?|"
    r"how to calculate|how is .{0,30}\b(?:calculated|derived|computed)\b|"
    r"derivation|derive|what is the (?:equation|formula)|worked example|"
    r"solve for|rearrange|cementation exponent|saturation exponent|tortuosity factor)\b",
    re.I,
)

# Equations petroleum geology names after people. These come up as bare names
# ("what is Archie?", "explain Wyllie") with none of the wording above, and they
# are exactly the requests the corpus answers worst.
_NAMED_EQUATION_RE = re.compile(
    r"\b(archie|wyllie|humble|timur|coates|larionov|steiber|clavier|gardner|"
    r"waxman[- ]smits|dual[- ]water|simandoux|indonesia equation|darcy'?s? law|"
    r"buckley[- ]leverett|kozeny[- ]carman|dean[- ]stark)\b",
    re.I,
)

# A question tied to the loaded well is an interpretation request, not a request
# for a general equation -- "calculate the porosity of my well" must stay on the
# tool path and keep the fabrication guard armed.
_WELL_SPECIFIC_RE = re.compile(
    r"\b(my|this|the)\s+(well|log|logs|upload|file|data|zone|interval|reservoir)\b"
    r"|\bfor my\b|\buploaded\b",
    re.I,
)

# MY CORPUS FAILS TO RETRIEVE FORMULAS AND MATH EXPRESSIONS
def is_formula_request(question: str) -> bool:
    """True when the user wants a general equation or derivation rather than an
    interpretation of this well's measured properties.

    Two things hang off this. The unsupported-quantity guard stands down,
    because a worked example uses illustrative numbers rather than claims about
    the well. And the corpus-search tool refuses to run: the books were
    scanned from pre-LaTeX print, so equations came through chunking as symbol
    soup, and a retrieved passage is actively worse than Claude's own recall for
    this one class of question. See _NAMED_EQUATION_RE for why bare names count.

    A question that names the user's own well is never a formula request, even
    when it says "calculate" -- that one belongs to the porosity tool.
    """
    if _WELL_SPECIFIC_RE.search(question):
        return False

    return bool(
        _FORMULA_REQUEST_RE.search(question) or _NAMED_EQUATION_RE.search(question)
    )


# A bracketed passage number, e.g. "[2]". GEOLOGY_SEARCH_RULE requires one next to any
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
        once compute_porosity has run). 
    """
    text = _uncited_text(answer) if has_context else answer
    exempt = {q.lower() for q in (computed or ())}

    return sorted(
        {q for q, rx in _QUANTITY_RE if q not in exempt and rx.search(text)}
    )


_CONFIDENCE_RE = re.compile(
    r"\b(?:confidence|probability|certainty)\b[^.\n|]{0,30}?(\d\d?\d?(?:\.\d+)?)\s*(%?)"
    r"|(\d\d?\d?(?:\.\d+)?)\s*(%?)[^.\n|]{0,20}?\b(?:confidence|probability|certainty)\b",
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
# "low confidence" is a qualitative label, so a number before it belongs to
# something else -- a porosity cell, a washout fraction.
_QUALITATIVE_RE = re.compile(
    r"\b(?:low|lower|high|higher|poor|good|weak|strong|moderate)[-\s]"
    r"(?:confidence|probability|certainty)\b",
    re.I,
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
        
        if m.group(1):
            raw, pct = m.group(1), m.group(2)
        else:
            # number-before-keyword: only a real claim if the keyword is unqualified
            if _QUALITATIVE_RE.search(m.group(0)):
                continue
            raw, pct = m.group(3), m.group(4)
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
    on_event=None,
) -> GeoMindResult:
    """Execute the flow.

        route -> [lithology] -> generate -> guard

    Retrieval, porosity, OOIP and prices are tools the model calls from inside
    generate, not steps in this pipeline.

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
        
    # RAG is a tool now, not a node: the model decides when to search.
    state = await generate_node(state, on_event=on_event)
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
