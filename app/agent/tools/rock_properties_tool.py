
import json

from app.petrologix.rock_properties import (
    RockNotFoundError,
    get_rock_properties,
    list_rocks,
    rock_names,
    units,
)

# The table carries porosity ranges per rock; without this the guard calls the
# model's quote of them fabricated. Density and resistivity are not guarded.
MEASURES = {"porosity"}
# Agent-callable tool: reference properties of rock types from a fixed table.

# General geology, not the loaded well. Factual retrieval only, the model does
# the reasoning over what comes back.
TOOL_SCHEMA = {
    "name": "get_rock_properties",
    "description": (
        "Look up representative physical properties of rock types: density "
        "range and average, electrical resistivity and conductivity ranges, "
        "porosity range, Mohs hardness, mineral composition, formation "
        "environment and geophysical signature. General reference values for "
        "the rock type, not measurements from the user's well. Pass "
        "rock_names for specific rocks. Leave rock_names empty to get the "
        "numeric properties of every rock in the table (optionally narrowed "
        "by lithology_class) for comparison questions such as which rocks are "
        "dense and resistive, or conductive when water-saturated."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "rock_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Rocks to look up, e.g. [\"Sandstone\", \"Granite\"].",
            },
            "lithology_class": {
                "type": "string",
                "enum": ["Sedimentary", "Igneous", "Metamorphic"],
                "description": "Only with empty rock_names: restrict the table to one class.",
            },
        },
        "required": [],
    },
}

_FOOTER = (
    "These are representative ranges for each rock type, not measurements from "
    "the user's well. Conductivity is the reciprocal of resistivity."
)

# This is what the LLM sees
def run(tool_input: dict) -> str:
    """Execute the tool. An unknown rock comes back as text with the list of
    names the table holds, so the model can retry or answer unaided."""
    names = tool_input.get("rock_names") or []
    
    if isinstance(names, str):
        names = [names]

    if not names:
        rocks = list_rocks(tool_input.get("lithology_class"))
        header = f"Rock properties table ({len(rocks)} rocks, numeric fields):"
        missing: list[str] = []
        
    else:
        rocks, missing = [], []
        for name in names:
            try:
                rocks.append(get_rock_properties(name))
                
            except RockNotFoundError:
                missing.append(name)
        header = "Rock properties:"

    parts = []
    if rocks:
        # One compact JSON object per line: the full table stays small in the prompt.
        body = "\n".join(json.dumps(r, ensure_ascii=False) for r in rocks)
        parts += [header, f"Units: {json.dumps(units())}", body, _FOOTER]
        
    if missing:
        parts.append(
            f"No table entry for: {', '.join(missing)}. The table holds: "
            f"{', '.join(rock_names())}. For other rocks answer from your own "
            "knowledge and say it is not from the reference table."
        )
    return "\n\n".join(parts)
