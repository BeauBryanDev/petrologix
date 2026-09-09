
import logging
 
import numpy as np
import pandas as pd
 
from app.schemas.predictions import LithologyInterval
from app.utils.las2csv_parser import parse_upload
 
logger = logging.getLogger(__name__)
"""Deterministic porosity calculation from well log curves."""

MATRIX_DENSITY_G_CC = {
    "Sandstone": 2.65,
    "Sandstone/Shale": 2.68,   # rough blend :: flagged as approximate below
    "Shale": 2.65,   # it does not distinguish between sandstone and shale
    "Limestone": 2.71,
    "Dolomite": 2.87,
    "Chalk": 2.71,
    "Marl": 2.65,
    "Anhydrite": 2.98,  # CaSO4
    "Halite": 2.03,  # NaCl ::lighter than the pore fluid it displaces
    "Coal": 1.80,
    "Tuff": 2.40,
}
 
# Same set the lithology guard already treats as unreliable model output --
# reused here because an ambiguous lithology call means an ambiguous matrix
# density choice too.
UNRELIABLE_LITHOLOGIES = {"Chalk", "Tuff", "Marl", "Dolomite"}

# Density porosity in clay-rich rock counts clay-bound water, which is not
# producible. The figure overstates effective porosity however confident the
# lithology call is, so these are flagged on confidence alone.
CLAY_BOUND_LITHOLOGIES = {"Shale", "Sandstone/Shale", "Marl"}

# Outside this range the result is not a measurement: either the matrix density
# is wrong for the zone or RHOB is bad. Reported rather than clamped -- a
# clamped 0.0% reads as a confident answer and hides the diagnostic.
PLAUSIBLE_POROSITY_FRACTION = (0.0, 0.5)

# Washout detection from the caliper. An enlarged hole puts mud between the
# density pad and the formation; RHOB reads low and density porosity reads
# high, which is the classic way a washed sand fakes a spectacular reservoir.
#
WASHOUT_GAUGE_PERCENTILE = 5
WASHOUT_EXCESS_IN = 1.0 # inches over gauge before a sample counts as washed
WASHOUT_ZONE_FRACTION = 0.25  # share of the zone that must be washed to flag it


def _washout(cali_zone) -> tuple[float, float, float] | None:
    """(washed fraction, gauge diameter, median excess) for one zone, or None.

    None when there is no usable caliper -- absence of the curve is not
    evidence of a good hole, so the caller stays silent rather than implying one.
    """
    valid = cali_zone[np.isfinite(cali_zone) & (cali_zone > 0)]

    if len(valid) < 10:
        return None

    gauge = float(np.percentile(valid, WASHOUT_GAUGE_PERCENTILE))
    excess = valid - gauge
    washed = excess > WASHOUT_EXCESS_IN
    fraction = float(np.mean(washed))

    if not fraction:
        return 0.0, gauge, 0.0

    # Median over the washed samples only. Averaging the whole zone reports a
    # gentler enlargement than the flagged fraction implies, which reads as the
    # two numbers contradicting each other.
    return fraction, gauge, float(np.median(excess[washed]))
 
_DEPTH_CANDIDATES = ("DEPT", "DEPTH_MD", "DEPTH")
 
 
def _depth_column(df: pd.DataFrame) -> str | None:
    
    for c in _DEPTH_CANDIDATES:
        
        
        if c in df.columns:
            
            return c
        
    return None
 
 
class PorosityResult:
    """One interval's calculated porosity, or the reason it couldn't be calculated."""
 
    def __init__(self, top, base, lithology, confidence, porosity_pct, reliable, note):
        self.top = top
        self.base = base
        self.lithology = lithology
        self.confidence = confidence
        self.porosity_pct = porosity_pct
        self.reliable = reliable
        self.note = note
 
 
class WellCurves:
    """The two curves porosity needs, kept so a later turn can recompute.

    The upload is a temp file the prediction router deletes as soon as the
    request ends, so a follow-up "now compute porosity" has no file to read.
    Holding depth and RHOB (float32, a few hundred KB for a full well) is what
    lets the tool answer on a chat turn.
    """

    __slots__ = ("depth", "rhob", "cali", "well_name")

    def __init__(self, depth, rhob, cali=None, well_name: str = ""):
        
        self.depth = np.asarray(depth, dtype=np.float32)
        self.rhob = np.asarray(rhob, dtype=np.float32)
        # Optional: used to flag washed-out hole, where RHOB reads mud instead
        # of rock. None when the log carries no caliper.
        self.cali = None if cali is None else np.asarray(cali, dtype=np.float32)
        self.well_name = well_name

    def __len__(self) -> int:
        return len(self.depth)


def extract_curves(
    well_log_path: str, 
    well_log_filename: str
) -> WellCurves | None:
    """Pull depth and RHOB out of an upload. None when the log has neither.

    Call this while the uploaded file still exists -- see attach_prediction in
    chat_service, which runs before the router deletes it.
    """
    df = parse_upload(well_log_path, well_log_filename)

    depth_col = _depth_column(df)

    if depth_col is None or "RHOB" not in df.columns:

        logger.warning(
            "no depth/RHOB column in %s -- porosity cannot be computed",
            well_log_filename,
        )
        return None

    return WellCurves(
        df[depth_col].to_numpy(),
        df["RHOB"].to_numpy(),
        cali=df["CALI"].to_numpy() if "CALI" in df.columns else None,
        well_name=well_log_filename,
    )


def compute_zone_porosity(
    well_log_path: str,
    well_log_filename: str,
    intervals: list[LithologyInterval],
    fluid_density_g_cc: float = 1.00,
    confidence_threshold: float = 0.7,
) -> list[PorosityResult]:

    """Compute mean density porosity per zone, reading the log from disk."""

    curves = extract_curves(well_log_path, well_log_filename)

    if curves is None:
        return []

    return compute_zone_porosity_from_curves(
        curves, intervals, fluid_density_g_cc, confidence_threshold
    )


def compute_zone_porosity_from_curves(
    curves: WellCurves,
    intervals: list[LithologyInterval],
    fluid_density_g_cc: float = 1.00,
    confidence_threshold: float = 0.7,
) -> list[PorosityResult]:

    """
    Compute mean density porosity per zone from curves already in memory.

    Same maths as compute_zone_porosity -- split out so a cached well can be
    recomputed on a later turn without the original file.
    """
    depth = curves.depth
    rhob = curves.rhob
    cali = curves.cali
 
    results: list[PorosityResult] = []
    
    for iv in intervals:
        
        mask = (depth >= iv.top) & (depth <= iv.base)
        rhob_zone = rhob[mask]
        rhob_zone = rhob_zone[np.isfinite(rhob_zone) & (rhob_zone > 0)]
 
        rho_ma = MATRIX_DENSITY_G_CC.get(iv.lithology)

        # The two ways a zone yields no number are different problems with
        # different fixes, so they no longer share one message.
        if rho_ma is None:

            results.append(PorosityResult(
                iv.top, iv.base, iv.lithology, iv.confidence,
                porosity_pct=None, reliable=False,
                note=f"no matrix density defined for {iv.lithology}",
            ))
            continue

        if len(rhob_zone) == 0:

            results.append(PorosityResult(
                iv.top, iv.base, iv.lithology, iv.confidence,
                porosity_pct=None, reliable=False,
                note="no valid RHOB samples in this interval",
            ))
            continue
        
        # Main Math Equation
        phi = (rho_ma - rhob_zone) / (rho_ma - fluid_density_g_cc)
        mean_phi = float(np.mean(phi))
        mean_phi_pct = round(mean_phi * 100, 1)

        # Every reason this figure should not be read at face value. 
        caveats: list[str] = []

        # Washout first: an enlarged hole is the usual reason a porosity comes
        # back implausible, so naming the cause beats reporting the symptom.
        washed = _washout(cali[mask]) if cali is not None else None

        if washed and washed[0] >= WASHOUT_ZONE_FRACTION:

            fraction, gauge, median_excess = washed
            caveats.append(
                f"{fraction * 100:.0f}% of this zone is washed out -- the hole "
                f"runs about {median_excess:.1f} in over its {gauge:.1f} in "
                "gauge diameter, so the density tool is reading mud as well as "
                "rock. RHOB is biased low and this porosity is biased high"
            )

        low, high = PLAUSIBLE_POROSITY_FRACTION

        if not low <= mean_phi <= high:
            caveats.append(
                f"{mean_phi_pct}% is outside the physically plausible "
                f"{low * 100:.0f}-{high * 100:.0f}% range, so the matrix density "
                f"assumed for {iv.lithology} ({rho_ma} g/cc) is likely wrong for "
                "this zone, or RHOB is unreliable here"
            )

        if iv.lithology in CLAY_BOUND_LITHOLOGIES:
            caveats.append(
                f"density porosity in {iv.lithology} includes clay-bound water, "
                "so this overstates effective (producible) porosity"
            )

        if iv.lithology in UNRELIABLE_LITHOLOGIES:
            caveats.append(
                f"matrix density assumed for {iv.lithology}, a lithology class the "
                "model does not reliably distinguish -- porosity is approximate"
            )

        if iv.confidence < confidence_threshold:
            caveats.append(
                f"lithology confidence {iv.confidence:.2f} is below "
                f"{confidence_threshold} -- porosity approximate"
            )

        results.append(PorosityResult(
            iv.top, iv.base, iv.lithology, iv.confidence,
            porosity_pct=mean_phi_pct,
            reliable=not caveats,
            note="; ".join(caveats) or None,
        ))
 
    return results
 
 
#  this is what the LLM sees
def summarize_porosity(results: list[PorosityResult],
                       max_zones: int = 10
                       ) -> str:
    """Compact text summary -- this, not raw curves, is what the LLM sees."""
    if not results:
        
        return "Porosity could not be calculated: no RHOB curve found in this well log."
 
    lines = ["Density porosity by zone (RHOB-derived, matrix density chosen per predicted lithology):"]
    
    ranked = sorted(results, key=lambda r: r.base - r.top, reverse=True)[:max_zones]
    
    for r in ranked:
        
        if r.porosity_pct is None:
            
            lines.append(
                f"  {r.top:.1f}-{r.base:.1f} m  {r.lithology:<16}  "
                f"conf {r.confidence:.2f}  porosity: n/a ({r.note})"
            )
            
        else:
            
            flag = "" if r.reliable else "  [approximate]"
            
            # Print the lithology confidence even though the caller already has
            # it: the model otherwise reconstructs it from memory for zones it
            # only saw here, and quotes values the prediction never produced.
            lines.append(
                f"  {r.top:.1f}-{r.base:.1f} m  {r.lithology:<16}  "
                f"conf {r.confidence:.2f}  {r.porosity_pct}%{flag}"
            )
            
            if r.note:
                
                lines.append(f"    note: {r.note}")
                
                
    return "\n".join(lines)
 