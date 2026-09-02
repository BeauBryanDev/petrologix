"""Output guards in app/agent/graph.py.
"""

from app.agent.graph import (
    retrieve_node,
    GeoMindState,
    find_blind_spot_claims,
    find_unsupported_confidence,
    find_unsupported_quantities,
    guard_node,
    is_formula_request,
    route_node,
)
from app.core.config import settings


# blind-spot claims
def test_absence_claim_about_the_well_is_flagged():
    assert find_blind_spot_claims("No dolomite is present in this well.") == ["Dolomite"]


def test_absence_claim_after_the_class_name_is_flagged():
    assert find_blind_spot_claims("Chalk was not detected anywhere.") == ["Chalk"]


def test_model_limitation_wording_is_left_alone():
    # The system prompt asks for exactly this sentence; correcting it made the
    # assistant argue with itself.
    answer = "The model cannot reliably detect Chalk, Tuff, Marl or Dolomite."
    assert find_blind_spot_claims(answer) == []


def test_reliable_class_absence_is_not_flagged():
    assert find_blind_spot_claims("There is no halite in this section.") == []


# fabricated petrophysical quantities
def test_numeric_porosity_claim_is_flagged():
    assert "porosity" in find_unsupported_quantities("Porosity is around 17.0%.")


def test_quantity_without_a_number_is_not_flagged():
    assert find_unsupported_quantities("The model does not report porosity.") == []


def test_multiple_quantities_are_reported_sorted():
    answer = "Water saturation is 32.0% and permeability reaches 250 mD."
    assert find_unsupported_quantities(answer) == ["permeability", "saturation"]


def test_cited_sentence_is_exempt_only_when_rag_context_exists():
    answer = "Typical sandstone porosity is 15-25% [2]."
    assert find_unsupported_quantities(answer, has_context=True) == []
    assert find_unsupported_quantities(answer, has_context=False) == ["porosity"]


def test_tool_measured_quantity_is_exempt():
    # Without this the agent prints its own porosity table and then calls it
    # fabricated.
    answer = "Computed density porosity for the sand is 24.8%."
    assert find_unsupported_quantities(answer, computed={"porosity"}) == []


def test_formula_requests_are_recognised():
    assert is_formula_request("What is the equation for density porosity?")
    assert not is_formula_request("What is the porosity of my well?")


# equation questions bypass the corpus
# The books were scanned from pre-LaTeX print, so their equations came through
# OCR as symbol soup. Claude writes these from its own training instead.
def test_named_equations_count_as_formula_requests():
    for q in ("Explain Archie's law.", "How does the Wyllie time-average work?",
              "What is Darcy's law?", "What is the cementation exponent m?"):
        assert is_formula_request(q), q


def test_conceptual_questions_are_not_formula_requests():
    # These are what the corpus is good at, so they must keep their passages.
    for q in ("Where does oil come from underground?",
              "What is a stratigraphic trap?",
              "How does a source rock become mature?"):
        assert not is_formula_request(q), q


def test_a_question_about_the_users_well_is_never_a_formula_request():
    # "calculate" alone must not divert the porosity tool or disarm the guard.
    assert not is_formula_request("Calculate the porosity of my well.")
    assert not is_formula_request("How do you calculate porosity for this log?")


async def test_retrieve_node_skips_the_corpus_for_equations(monkeypatch):
    monkeypatch.setattr(settings, "rag_enabled", True)
    called = False

    async def fail(*a, **kw):
        nonlocal called
        called = True
        return "[1] some OCR'd source\nphi = ...", 1

    monkeypatch.setattr("app.agent.graph.run_geology_search", fail)
    state = await retrieve_node(_state(question="What is Archie's equation?"))

    assert not called
    assert state.rag_context is None and state.rag_hits == 0
    assert "retrieve=skipped (equation request)" in state.trace


async def test_retrieve_node_consults_the_corpus_for_prose_questions(monkeypatch):
    monkeypatch.setattr(settings, "rag_enabled", True)

    async def ok(*a, **kw):
        return "[1] Selley, Elements of Petroleum Geology\nKerogen matures...", 1

    monkeypatch.setattr("app.agent.graph.run_geology_search", ok)
    state = await retrieve_node(_state(question="Where does oil come from underground?"))

    assert state.rag_hits == 1 and "Selley" in state.rag_context


# confidence claims
def test_confidence_with_no_prediction_is_reported():
    no_prediction, mismatched = find_unsupported_confidence("Confidence 0.91.", None)
    assert no_prediction and mismatched == []


def test_confidence_present_in_the_summary_passes():
    summary = "Shale 0.91\nSandstone 0.84"
    assert find_unsupported_confidence("Confidence 0.91.", summary) == (False, [])


def test_confidence_absent_from_the_summary_is_flagged():
    summary = "Shale 0.91"
    assert find_unsupported_confidence("Confidence is 0.55.", summary) == (False, ["0.55"])


def test_tool_output_is_an_accepted_confidence_source():
    # The porosity tool quoting its own 0.7 threshold was flagged as invented
    # before tool_outputs were consulted.
    summary = "Shale 0.91"
    result = find_unsupported_confidence(
        "Zones below 0.70 confidence are approximate.", summary, ["conf 0.70 threshold"]
    )
    assert result == (False, [])


def test_percentage_confidence_is_normalised():
    assert find_unsupported_confidence("Confidence 91%.", "Shale 0.91") == (False, [])


def test_answer_with_no_confidence_claim_is_ignored():
    assert find_unsupported_confidence("Mostly shale.", None) == (False, [])


# guard_node wiring
def _state(**kw):
    kw.setdefault("question", "what rocks are here?")
    kw.setdefault("llm_used", True)
    return GeoMindState(**kw)


def test_guard_node_appends_corrections_without_rewriting_the_answer():
    state = _state(answer="No chalk is present.", lithology_summary="Shale 0.91")
    guard_node(state)
    assert state.answer.startswith("No chalk is present.")
    assert "Correction:" in state.answer
    assert state.warnings


def test_guard_node_is_a_noop_when_the_llm_did_not_answer():
    state = _state(answer="No chalk is present.", llm_used=False)
    guard_node(state)
    assert state.answer == "No chalk is present."


def test_guard_node_skips_the_quantity_check_for_formula_requests():
    state = _state(
        question="What is the formula for porosity?",
        answer="phi = (2.65 - 2.30) / (2.65 - 1.0) = 21.2% porosity.",
        lithology_summary="Shale 0.91",
    )
    guard_node(state)
    assert "Correction:" not in state.answer


# routing
def test_route_node_takes_the_lithology_branch_for_an_upload():
    state = route_node(_state(well_log_path="/tmp/well.las"))
    assert state.route == "lithology"


def test_route_node_restores_prior_session_context_on_a_chat_turn(sandstone_interval,
                                                                 clean_curves):
    state = route_node(_state(
        prior_lithology_summary="Shale 0.91",
        prior_intervals=[sandstone_interval],
        prior_curves=clean_curves,
    ))
    assert state.route == "chat"
    assert state.lithology_summary == "Shale 0.91"
    assert state.intervals == [sandstone_interval]
    assert state.curves is clean_curves
