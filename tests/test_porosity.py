"""Density porosity: the maths, and the caveats that keep a washed sand from
reading as a spectacular reservoir.
"""

import numpy as np
import pytest

from app.agent.tools import porosity_tool
from app.agent.graph import GeoMindState
from app.petrologix.compute_porosity import (
    WellCurves,
    compute_zone_porosity_from_curves,
    summarize_porosity,
)
from tests.conftest import make_interval


def _one(curves, interval, **kw):
    results = compute_zone_porosity_from_curves(curves, [interval], **kw)
    assert len(results) == 1
    return results[0]


def test_density_porosity_matches_the_hand_calculation(clean_curves, sandstone_interval):
    # (2.65 - 2.25) / (2.65 - 1.00) = 0.2424
    r = _one(clean_curves, sandstone_interval)
    assert r.porosity_pct == pytest.approx(24.2, abs=0.1)
    assert r.reliable and r.note is None


def test_fluid_density_changes_the_result(clean_curves, sandstone_interval):
    salty = _one(clean_curves, sandstone_interval, fluid_density_g_cc=1.1)
    fresh = _one(clean_curves, sandstone_interval)
    assert salty.porosity_pct > fresh.porosity_pct


def test_unknown_lithology_yields_no_number(clean_curves):
    r = _one(clean_curves, make_interval(lithology="Basalt"))
    assert r.porosity_pct is None and "matrix density" in r.note


def test_zone_with_no_valid_rhob_yields_no_number(clean_curves):
    r = _one(clean_curves, make_interval(top=5000.0, base=5100.0))
    assert r.porosity_pct is None and "no valid RHOB" in r.note


def test_shale_is_flagged_for_clay_bound_water(clean_curves):
    r = _one(clean_curves, make_interval(lithology="Shale"))
    assert not r.reliable and "clay-bound water" in r.note


def test_blind_spot_lithology_is_flagged_as_approximate(clean_curves):
    r = _one(clean_curves, make_interval(lithology="Dolomite"))
    assert not r.reliable and "does not reliably distinguish" in r.note


def test_low_lithology_confidence_is_flagged(clean_curves):
    r = _one(clean_curves, make_interval(confidence=0.51))
    assert not r.reliable and "below 0.7" in r.note


def test_implausible_porosity_is_reported_not_clamped():
    depth = np.arange(1000.0, 1100.1, 0.5)
    curves = WellCurves(depth, np.full(depth.shape, 1.20))   # far too light
    r = _one(curves, make_interval())
    assert r.porosity_pct > 50 and "physically plausible" in r.note


def test_washout_is_flagged_and_named_first():
    depth = np.arange(1000.0, 1100.1, 0.5)
    cali = np.full(depth.shape, 8.5)
    cali[: int(len(cali) * 0.8)] = 13.5          # 5 in over gauge
    curves = WellCurves(depth, np.full(depth.shape, 1.97), cali=cali)
    r = _one(curves, make_interval())
    assert r.note.startswith("80% of this zone is washed out")
    assert "biased high" in r.note


def test_no_caliper_makes_no_washout_claim(clean_curves, sandstone_interval):
    curves = WellCurves(clean_curves.depth, clean_curves.rhob)
    assert "washed" not in (_one(curves, sandstone_interval).note or "")


def test_summary_prints_confidence_per_zone(clean_curves, sandstone_interval):
    text = summarize_porosity(compute_zone_porosity_from_curves(
        clean_curves, [sandstone_interval]))
    assert "conf 0.95" in text and "24.2%" in text


def test_summary_of_no_results_says_why():
    assert "no RHOB curve" in summarize_porosity([])


def test_tool_prefers_cached_curves_over_a_missing_file(clean_curves,
                                                        sandstone_interval):
    state = GeoMindState(question="compute porosity")
    state.intervals = [sandstone_interval]
    state.curves = clean_curves
    state.well_log_path = "/nonexistent/well.las"
    assert "24.2%" in porosity_tool.run(state, {})


def test_tool_refuses_without_a_loaded_well():
    state = GeoMindState(question="compute porosity")
    assert "No well log is currently loaded" in porosity_tool.run(state, {})
