
from app.petrologix.compute_porosity import (
    compute_zone_porosity,
    compute_zone_porosity_from_curves,
    summarize_porosity,
)
"""Agent-callable tool: compute density porosity from the well log's RHOB
curve, per predicted lithology zone.
"""


MEASURES = {"porosity"}

TOOL_SCHEMA = {
    "name": "compute_porosity",
    "description": (
        "Calculate density porosity (from the RHOB curve) for each predicted "
        "lithology zone in the currently loaded well log. This tool reads the "
        "well's curve data itself, server-side -- you do not need to provide "
        "any curve values, depths, or file contents as input; just call it. "
        "Use it when the user explicitly asks to calculate, compute, or "
        "estimate porosity FOR THEIR WELL. Do not use it for general questions "
        "about porosity theory, equations, or worked examples -- answer those "
        "directly from your own knowledge instead."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "fluid_density_g_cc": {
                "type": "number",
                "description": (
                    "Pore fluid density in g/cc. Default 1.00 (fresh mud "
                    "filtrate). Use ~1.1 if the user mentions saline/salt mud."
                ),
            }
        },
        "required": [],
    },
}
 
# This is what the LLM sees
def run(state, tool_input: dict) -> str:
    """Execute the tool against the current request's well log and lithology.
 
    `state` is the GeoMindState for this request -- needs well_log_path,
    well_log_filename, and intervals populated (from this turn's upload, or
    from cached session data on a follow-up turn -- see graph.py/chat_service.py).
    """
    if not state.intervals:
        return (
            "No well log is currently loaded for this session, so porosity "
            "cannot be calculated. Tell the user to upload a .las or .csv "
            "file with a RHOB curve first."
        )

    fluid_density = tool_input.get("fluid_density_g_cc", 1.00)

    # Curves cached by the session come first: on a follow-up turn the upload
    # has already been deleted, and this is the only copy left.
    if state.curves is not None:
        
        results = compute_zone_porosity_from_curves(
            state.curves, state.intervals, 
            fluid_density_g_cc=fluid_density,
        )

    elif state.well_log_path:
        
        results = compute_zone_porosity(
            state.well_log_path, 
            state.well_log_filename, 
            state.intervals,
            fluid_density_g_cc=fluid_density,
        )

    else:
        return (
            "The density curve for this well is no longer available, so "
            "porosity cannot be recalculated. Tell the user to re-upload the "
            "log."
        )

    return summarize_porosity(results)
 