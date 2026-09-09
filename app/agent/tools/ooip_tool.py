from app.petrologix.compute_ooip import OOIPInputError, compute_ooip, summarize_ooip
"""Agent-callable tool: volumetric OOIP (original oil in place) and
recoverable reserves from user-supplied reservoir parameters.
"""

# Every figure the tool echoes back. The fabrication guard would otherwise
# flag the model for quoting the inputs it was asked to use.
MEASURES = {"reserves", "net pay", "saturation", "porosity"}

TOOL_SCHEMA = {
    "name": "compute_ooip",
    "description": (
        "Estimate original oil in place (OOIP) and recoverable reserves with "
        "the volumetric equation N = 7758 * A * h * phi * (1 - Sw) / Bo. "
        "Use it when the user asks to compute, estimate or calculate OOIP, "
        "oil in place, STOIIP or reserves. It needs no well log: every input "
        "is a number the user gave, or a porosity and interval taken from an "
        "earlier compute_porosity result in this conversation. Give area as "
        "either area_acres or drainage_radius_ft, and thickness as either "
        "net_pay_ft or the interval z1_m/z2_m."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "porosity_frac": {
                "type": "number",
                "description": "Porosity as a fraction (0.20, not 20).",
            },
            "water_saturation_frac": {
                "type": "number",
                "description": "Initial water saturation Sw as a fraction.",
            },
            "bo_rb_stb": {
                "type": "number",
                "description": "Oil formation volume factor Bo in rb/stb.",
            },
            "recovery_factor_frac": {
                "type": "number",
                "description": "Recovery factor as a fraction.",
            },
            "area_acres": {"type": "number", "description": "Drainage area in acres."},
            "drainage_radius_ft": {
                
                
                
                
                "type": "number",
                "description": "Circular drainage radius in feet, instead of area_acres.",
            },
            "net_pay_ft": {"type": "number", "description": "Net pay thickness in feet."},
            "z1_m": {"type": "number", "description": "Interval top in metres, instead of net_pay_ft."},
            "z2_m": {"type": "number", "description": "Interval base in metres, with z1_m."},
        },
        "required": [
            "porosity_frac", "water_saturation_frac", "bo_rb_stb", "recovery_factor_frac",
        ],
    },
}

# This is what the LLM sees
def run(tool_input: dict) -> str:
    """Execute the tool. Bad inputs come back as text for the model to relay,
    not as an exception -- the user typed them and needs to hear which one."""
    try:
        return summarize_ooip(compute_ooip(**tool_input))

    except (OOIPInputError, TypeError) as e:
        return f"OOIP could not be calculated: {e}. Ask the user to correct the input."
