"""Rock properties table: names match the lithology model, values are consistent."""

import json

import pytest
from petrologix.config import LITHOLOGY_LABELS

from app.agent.tools import registry, rock_properties_tool
from app.petrologix.rock_properties import (
    DATA_PATH,
    RockNotFoundError,
    get_rock_properties,
    list_rocks,
    rock_names,
)

ROCKS = json.loads(DATA_PATH.read_text(encoding="utf-8"))["rocks"]


@pytest.mark.parametrize("label", sorted(LITHOLOGY_LABELS.values()))
def test_every_model_class_has_an_entry(label):
    assert get_rock_properties(label)["rock_name"] == label


def test_names_are_unique():
    assert len(rock_names()) == len(set(rock_names()))


@pytest.mark.parametrize("rock", ROCKS, ids=lambda r: r["rock_name"])
def test_ranges_are_consistent(rock):
    c_lo, c_hi = rock["conductivity_min_max"]
    r_lo, r_hi = rock["resistivity_min_max"]
    assert r_lo == pytest.approx(1 / c_hi, rel=0.01)
    assert r_hi == pytest.approx(1 / c_lo, rel=0.01)
    d_lo, d_hi = rock["density_min_max"]
    assert d_lo <= rock["avg_density"] <= d_hi
    for f in ("porosity", "mohs_hardness"):
        assert rock[f][0] <= rock[f][1]


@pytest.mark.parametrize("query, expected", [
    ("SANDSTONE", "Sandstone"),
    ("dolostone", "Dolomite"),
    ("Rock salt", "Halite"),
    ("sandstone / shale", "Sandstone/Shale"),
    ("shaly sand", "Sandstone/Shale"),
    ("granites", "Granite"),
    ("Gneiss", "Gneiss"),
])
def test_lookup_accepts_common_forms(query, expected):
    assert get_rock_properties(query)["rock_name"] == expected


def test_unknown_rock_raises():
    with pytest.raises(RockNotFoundError):
        get_rock_properties("kryptonite")


def test_class_filter():
    names = {r["rock_name"] for r in list_rocks("Igneous")}
    assert {"Granite", "Basalt", "Basement"} <= names
    assert "Shale" not in names


def test_tool_returns_full_record_for_named_rock():
    text = rock_properties_tool.run({"rock_names": ["Granite"]})
    assert '"rock_name": "Granite"' in text
    assert "mineral_composition" in text
    assert "not measurements from the user's well" in text


def test_tool_without_names_returns_compact_table():
    text = rock_properties_tool.run({})
    assert '"rock_name": "Basement"' in text
    assert "mineral_composition" not in text


def test_tool_reports_unknown_rock_as_text():
    text = rock_properties_tool.run({"rock_names": ["Granite", "kryptonite"]})
    assert '"rock_name": "Granite"' in text
    assert "No table entry for: kryptonite" in text


def test_registered():
    tool = registry.BY_NAME["get_rock_properties"]
    assert tool.measures == {"porosity"}
