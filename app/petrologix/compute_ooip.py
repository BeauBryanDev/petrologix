import math
 
# Conversions between units.
ACRE_FT_TO_STB = 7758  # bbl per acre-ft at 100% porosity/saturation
SQFT_PER_ACRE = 43_560
M_TO_FT = 3.28084
 
 
# Deterministic OOIP (Original Oil In Place) calculation via the standard
# volumetric equation.

class OOIPResult:
    def __init__(
        self, area_acres, net_pay_ft, porosity_frac, water_saturation_frac,
        bo_rb_stb, recovery_factor_frac, ooip_stb, recoverable_stb,
    ):
        self.area_acres = area_acres
        self.net_pay_ft = net_pay_ft
        self.porosity_frac = porosity_frac
        self.water_saturation_frac = water_saturation_frac
        self.bo_rb_stb = bo_rb_stb
        self.recovery_factor_frac = recovery_factor_frac
        self.ooip_stb = ooip_stb
        self.recoverable_stb = recoverable_stb
 

# This is the basic equation not fancy NRS or Mass Balance

class OOIPInputError(ValueError):
    """Raised when required inputs are missing or out of physically sane range."""
 
 

def compute_ooip(
    water_saturation_frac: float,
    bo_rb_stb: float,
    recovery_factor_frac: float,
    porosity_frac: float,
    drainage_radius_ft: float | None = None,
    area_acres: float | None = None,
    net_pay_ft: float | None = None,
    z1_m: float | None = None,
    z2_m: float | None = None,
) -> OOIPResult:
    """
    Compute OOIP and recoverable reserves.

    Area comes from either area_acres directly or a circular drainage radius
    in feet. Net pay comes from either net_pay_ft directly, or a depth
    interval z1_m/z2_m in metres (converted here to feet). Exactly one of
    each pair must be supplied.
    """
    if (drainage_radius_ft is None) == (area_acres is None):
        raise OOIPInputError("provide drainage_radius_ft OR area_acres, not both")

    if drainage_radius_ft is not None and drainage_radius_ft <= 0:
        raise OOIPInputError("drainage_radius_ft must be positive")

    if area_acres is not None and area_acres <= 0:
        raise OOIPInputError("area_acres must be positive")
    
    if not (0 < porosity_frac < 0.5):
        raise OOIPInputError(f"porosity_frac={porosity_frac} is outside a physically sane range (0-0.5)")
    
    if not (0 <= water_saturation_frac < 1):
        raise OOIPInputError(f"water_saturation_frac={water_saturation_frac} must be in [0, 1)")
    
    if bo_rb_stb <= 0:
        raise OOIPInputError("bo_rb_stb must be positive")
    
    if not (0 < recovery_factor_frac <= 1):
        raise OOIPInputError(f"recovery_factor_frac={recovery_factor_frac} must be in (0, 1]")
 
    if net_pay_ft is None:
        
        if z1_m is None or z2_m is None:
            raise OOIPInputError(
                "provide either net_pay_ft, or both z1_m and z2_m to derive it"
            )
            
        net_pay_ft = abs(z2_m - z1_m) * M_TO_FT
        
    elif z1_m is not None or z2_m is not None:
        
        raise OOIPInputError("provide net_pay_ft OR z1_m/z2_m, not both")
 
    if area_acres is None:
        area_acres = (math.pi * drainage_radius_ft ** 2) / SQFT_PER_ACRE

    if net_pay_ft <= 0:
        raise OOIPInputError("net pay must be positive")
 
    ooip_stb = (
        ACRE_FT_TO_STB * area_acres * net_pay_ft * porosity_frac
        * (1 - water_saturation_frac) / bo_rb_stb
    )
    recoverable_stb = ooip_stb * recovery_factor_frac
 
    return OOIPResult(
        
        area_acres=round(area_acres, 2),
        net_pay_ft=round(net_pay_ft, 1),
        porosity_frac=porosity_frac,
        water_saturation_frac=water_saturation_frac,
        bo_rb_stb=bo_rb_stb,
        recovery_factor_frac=recovery_factor_frac,
        ooip_stb=round(ooip_stb, 0),
        recoverable_stb=round(recoverable_stb, 0),
    )
 
 
# This is what the LLM sees
def summarize_ooip(r: OOIPResult) -> str:
    """Compact text summary for the tool_result -- inputs echoed back so the
    user can sanity-check the assumptions the calculation actually used."""
    
    return (
        "OOIP calculation (volumetric method):\n"
        f"  Inputs -- drainage area: {r.area_acres} acres, net pay: {r.net_pay_ft} ft, "
        f"porosity: {r.porosity_frac:.3f}, Swi: {r.water_saturation_frac:.3f}, "
        f"Bo: {r.bo_rb_stb} rb/stb, recovery factor: {r.recovery_factor_frac:.2f}\n\n"
        f"  OOIP (oil in place, before recovery factor): {r.ooip_stb:,.0f} STB\n"
        f"  Recoverable reserves (OOIP x recovery factor): {r.recoverable_stb:,.0f} STB\n\n"
        "  Note: OOIP and recoverable reserves are distinct figures -- do not "
        "present one as the other when explaining this to the user. Net pay "
        "derived from a depth interval is gross thickness; no net-to-gross cut "
        "was applied."
    )
 