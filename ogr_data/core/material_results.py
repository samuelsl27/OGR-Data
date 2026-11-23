"""Derived results of a material, shared by the window and the API (spec 019).

These lived in the main window (spec 009 sigma3max by application, the
Generalized Hoek-Brown "Computed" values copied to the clipboard, the
equivalent / best-fit MC overlay, applying a fit to the form). They are
moved here so that the window, the operations layer (``ogr_data.api``)
and the MCP server compute them with the SAME functions (spec 019:
"mismas funciones de núcleo, sin duplicar lógica").

Units: registry parameters in kPa and degrees; results in MPa (core
convention); unit weight in MN/m3, depth in m.
"""

from __future__ import annotations

from typing import Mapping, Union

from . import application
from . import criteria_envelopes as ce
from . import samplers
from .hoek_brown import HbInput, ModulusMethod, compute, equivalent_mc, global_strength, hoek_brown_constants
from .models import MODULUS_METHODS

Params = Mapping[str, Union[float, bool, str, list]]

HB_FAMILY = ("generalized_hoek_brown", "hoek_brown")
DEFAULT_EI_KPA = 12000000.0


def modulus_method(params: Params) -> ModulusMethod:
    """Erm method chosen in the GHB form (ORMAS labels, spec 022)."""

    label = params.get("modulus_method", MODULUS_METHODS[0])
    index = MODULUS_METHODS.index(label) if label in MODULUS_METHODS else 0
    return list(ModulusMethod)[index]


def ghb_input(params: Params, sig3max_mpa: float) -> HbInput:
    """Generalized Hoek-Brown input (MPa) from the registry parameters (kPa)."""

    return HbInput(
        sigci=float(params["sigci"]) / 1000.0,
        gsi=float(params["gsi"]),
        mi=float(params["mi"]),
        disturbance=float(params["d"]),
        ei=float(params.get("ei", DEFAULT_EI_KPA)) / 1000.0,
        sig3max=sig3max_mpa,
    )


def hb_terms(criterion: str, params: Params, sig3max_mpa: float) -> tuple[float, float, float, float]:
    """(sigci_mpa, mb, s, a) of a Hoek-Brown criterion; classic HB is a = 0.5."""

    if criterion == "generalized_hoek_brown":
        inp = ghb_input(params, sig3max_mpa)
        mb, s, a = hoek_brown_constants(inp)
        return inp.sigci, mb, s, a
    if criterion == "hoek_brown":
        return float(params["compressive_strength"]) / 1000.0, float(params["mb"]), float(params["s"]), 0.5
    raise ValueError(f"{criterion} is not a Hoek-Brown criterion")


def rock_mass_strength_mpa(criterion: str, params: Params, sig3max_mpa: float) -> float | None:
    """Global rock mass strength sigcm (MPa), for HB-family criteria only."""

    if criterion == "generalized_hoek_brown":
        return compute(ghb_input(params, sig3max_mpa), modulus_method(params)).sigcm
    if criterion == "hoek_brown":
        sigci, mb, s, a = hb_terms(criterion, params, sig3max_mpa)
        inp = HbInput(sigci=sigci, gsi=50.0, mi=10.0, disturbance=0.0, sig3max=sig3max_mpa)
        return global_strength(inp, mb, s, a)
    return None


def application_sig3max(criterion: str, params: Params, mode: str, unit_weight_mn_m3: float, depth_m: float,
                        sig3max_mpa: float) -> float | None:
    """sigma3max (MPa) from the application (spec 009), or None for custom / non-HB criteria."""

    if mode == "custom" or criterion not in HB_FAMILY:
        return None
    sigcm = rock_mass_strength_mpa(criterion, params, sig3max_mpa)
    if sigcm is None or sigcm <= 0.0:
        return None
    if mode == "tunnel":
        return application.sig3max_tunnel(sigcm, unit_weight_mn_m3, depth_m)
    if mode == "slope":
        return application.sig3max_slope(sigcm, unit_weight_mn_m3, depth_m)
    raise ValueError(f"unknown application mode {mode!r}")


def ghb_computed(criterion: str, params: Params, sig3max_mpa: float) -> dict[str, float]:
    """GHB computed values of the clipboard contract (empty for other criteria)."""

    if criterion != "generalized_hoek_brown":
        return {}
    r = compute(ghb_input(params, sig3max_mpa), modulus_method(params))
    return {
        "mb": r.mb,
        "s": r.s,
        "a": r.a,
        "sigt_mpa": r.sigt,
        "sigc_mpa": r.sigc,
        "sigcm_mpa": r.sigcm,
        "c_mpa": r.mc.cohesion,
        "phi_deg": r.mc.friction_deg,
        "erm_mpa": r.erm,
    }


def overlay_mc(criterion: str, params: Params, sig3max_mpa: float, shear_curve=None) -> samplers.InstantaneousMC | None:
    """Equivalent MC (HB family, Hoek 2002) or best-fit MC (Power Curve, Barton-Bandis; RocData 2004 p. 10)."""

    if criterion in HB_FAMILY:
        sigci, mb, s, a = hb_terms(criterion, params, sig3max_mpa)
        # Hoek (2002) closed form over sigt < sigma3 < sig3max; only sigci and
        # sig3max of the input are used by the formulation.
        inp = HbInput(sigci=sigci, gsi=50.0, mi=10.0, disturbance=0.0, sig3max=sig3max_mpa)
        mc = equivalent_mc(inp, mb, s, a)
        return samplers.InstantaneousMC(mc.cohesion, mc.friction_deg, 0.0, 0.0, 0.0)
    if criterion in ("power_curve", "barton_bandis"):
        curve = shear_curve if shear_curve is not None else ce.shear_curve(criterion, params, sig3max_mpa)
        if curve is None:
            return None
        return samplers.best_fit_mc(*curve)
    return None


def computed(criterion: str, params: Params, sig3max_mpa: float) -> dict[str, float]:
    """All derived values of a material, as the Computed panel (MPa, degrees).

    GHB: the clipboard values. Classic HB: sigcm and the equivalent MC.
    Power Curve and Barton-Bandis: the best-fit MC over the range.
    """

    if criterion == "generalized_hoek_brown":
        return ghb_computed(criterion, params, sig3max_mpa)
    if criterion == "hoek_brown":
        mc = overlay_mc(criterion, params, sig3max_mpa)
        return {"sigcm_mpa": rock_mass_strength_mpa(criterion, params, sig3max_mpa), "c_mpa": mc.cohesion_mpa, "phi_deg": mc.friction_deg}
    if criterion in ("power_curve", "barton_bandis"):
        mc = overlay_mc(criterion, params, sig3max_mpa)
        return {} if mc is None else {"c_mpa": mc.cohesion_mpa, "phi_deg": mc.friction_deg}
    return {}


# Fit parameter -> (criterion of the form, {fit key: (registry field, factor to kPa)}): spec 006.
FIT_TO_FORM: dict[str, tuple[str, dict[str, tuple[str, float]]]] = {
    "mohr_coulomb": ("mohr_coulomb", {"cohesion_mpa": ("peak_cohesion", 1000.0), "friction_deg": ("peak_friction", 1.0)}),
    "hoek_brown": ("hoek_brown", {"sigci_mpa": ("compressive_strength", 1000.0), "mi": ("mb", 1.0)}),
    # the GHB rock-mass fit gives mb and s: it fills classic HB (a = 0.5 there)
    "generalized_hoek_brown": ("hoek_brown", {"mb": ("mb", 1.0), "s": ("s", 1.0)}),
    "barton_bandis": ("barton_bandis", {"jrc": ("jrc", 1.0), "jcs_mpa": ("jcs", 1000.0)}),
    "power_curve": ("power_curve", {"a": ("a", 1.0), "b": ("b", 1.0), "d_mpa": ("d", 1000.0)}),
}


def fit_to_parameters(result) -> tuple[str, dict[str, float]]:
    """(criterion, registry values in kPa/deg) that applying a FitResult writes into the form."""

    target, fields = FIT_TO_FORM[result.criterion]
    values = {field: float(result.parameters[key]) * factor for key, (field, factor) in fields.items() if key in result.parameters}
    if target == "hoek_brown" and result.criterion == "hoek_brown":
        values["s"] = 1.0  # intact rock
    if target == "barton_bandis" and result.fixed and "phi_b_deg" in result.fixed:
        values["phi_r"] = float(result.fixed["phi_b_deg"])
    return target, values
