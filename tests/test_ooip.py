"""Volumetric OOIP: the arithmetic and the input contract the model must meet."""

import pytest

from app.agent.tools import ooip_tool
from app.petrologix.compute_ooip import OOIPInputError, compute_ooip


def test_textbook_case():
    # 640 acres, 50 ft, phi 0.20, Sw 0.30, Bo 1.2 -> 7758*640*50*0.2*0.7/1.2
    r = compute_ooip(area_acres=640, net_pay_ft=50, porosity_frac=0.20,
                     water_saturation_frac=0.30, bo_rb_stb=1.2, recovery_factor_frac=0.35)
    assert r.ooip_stb == pytest.approx(28_963_200, rel=1e-6)
    assert r.recoverable_stb == pytest.approx(r.ooip_stb * 0.35, rel=1e-4)


def test_radius_and_interval_are_converted():
    r = compute_ooip(drainage_radius_ft=1000, z1_m=700, z2_m=730, porosity_frac=0.2,
                     water_saturation_frac=0.3, bo_rb_stb=1.2, recovery_factor_frac=0.3)
    assert r.area_acres == pytest.approx(72.12, abs=0.01)
    assert r.net_pay_ft == pytest.approx(98.4, abs=0.1)


@pytest.mark.parametrize("kw", [
    dict(area_acres=10, drainage_radius_ft=100, net_pay_ft=10),   # both area forms
    dict(net_pay_ft=10),                                           # no area
    dict(area_acres=10),                                           # no thickness
    dict(area_acres=10, net_pay_ft=10, z1_m=1, z2_m=2),            # both thickness forms
    dict(area_acres=10, net_pay_ft=10, porosity_frac=0.9),         # implausible porosity
])
def test_bad_inputs_are_rejected(kw):
    base = dict(porosity_frac=0.2, water_saturation_frac=0.3, bo_rb_stb=1.2,
                recovery_factor_frac=0.3)
    with pytest.raises(OOIPInputError):
        compute_ooip(**{**base, **kw})


def test_tool_reports_bad_input_as_text():
    text = ooip_tool.run({"porosity_frac": 0.2, "water_saturation_frac": 0.3,
                          "bo_rb_stb": 1.2, "recovery_factor_frac": 0.3})
    assert text.startswith("OOIP could not be calculated")


def test_tool_summary_separates_ooip_from_recoverable():
    text = ooip_tool.run({"area_acres": 640, "net_pay_ft": 50, "porosity_frac": 0.2,
                          "water_saturation_frac": 0.3, "bo_rb_stb": 1.2,
                          "recovery_factor_frac": 0.35})
    assert "OOIP" in text and "Recoverable reserves" in text
    assert "28,963,200" in text
