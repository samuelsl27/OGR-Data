"""Registry of the ten RSData strength criteria.

Field values (defaults) were captured from the Define Material Models dialog
of RSData on 2026-11-22; see the analysis in the suite references
(RSData_analisis/01_modelos_material.md). Stress units are kPa and degrees,
as shown in the RSData dialogs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    default: Union[float, bool, str]
    unit: str = ""
    kind: str = "float"  # "float" | "bool" | "enum"
    options: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in ("float", "bool", "enum"):
            raise ValueError(f"unknown field kind {self.kind!r}")


@dataclass(frozen=True)
class Criterion:
    key: str
    label: str
    category: str  # "rock" | "soil"
    envelope: str  # "principal" | "shear" | "none"
    fields: tuple[Field, ...]


def _peak_residual_tensile() -> tuple[Field, ...]:
    return (
        Field("peak_tensile", "Peak Tensile Strength", 0.0, "kPa"),
        Field("set_residual_to_peak", "Set Residual to Peak", True, kind="bool"),
        Field("residual_tensile", "Residual Tensile Strength", 0.0, "kPa"),
    )


CRITERIA: dict[str, Criterion] = {
    "mohr_coulomb": Criterion(
        "mohr_coulomb",
        "Mohr Coulomb",
        "soil",
        "principal",
        (
            Field("material_type", "Material Type", "Plastic", kind="enum", options=("Plastic",)),
            Field("peak_cohesion", "Peak Cohesion", 10.5, "kPa"),
            Field("peak_friction", "Peak Friction Angle", 35.0, "deg"),
            *_peak_residual_tensile(),
            Field("residual_cohesion", "Residual Cohesion", 10.5, "kPa"),
            Field("residual_friction", "Residual Friction Angle", 35.0, "deg"),
            Field("dilation", "Dilation Angle", 0.0, "deg"),
        ),
    ),
    "hoek_brown": Criterion(
        "hoek_brown",
        "Hoek Brown",
        "rock",
        "principal",
        (
            Field("material_type", "Material Type", "Plastic", kind="enum", options=("Plastic",)),
            Field("compressive_strength", "Compressive Strength", 100000.0, "kPa"),
            Field("mb", "mb Parameter", 1.0),
            Field("s", "s Parameter", 0.001),
            Field("set_residual_to_peak", "Set Residual to Peak", True, kind="bool"),
            Field("residual_mb", "Residual mb Parameter", 1.0),
            Field("residual_s", "Residual s Parameter", 0.001),
            Field("dilation_parameter", "Dilation Parameter", 0.0),
        ),
    ),
    "drucker_prager": Criterion(
        "drucker_prager",
        "Drucker-Prager",
        "soil",
        "principal",
        (
            Field("peak_q", "Peak q Parameter", 0.005),
            Field("peak_k", "Peak k Parameter", 35.0, "kPa"),
            *_peak_residual_tensile(),
            Field("residual_q", "Residual q Parameter", 0.005),
            Field("residual_k", "Residual k Parameter", 35.0, "kPa"),
            Field("dilation_parameter", "Dilation Parameter", 0.0),
        ),
    ),
    "generalized_hoek_brown": Criterion(
        "generalized_hoek_brown",
        "Generalized Hoek Brown",
        "rock",
        "principal",
        (
            Field("define_by", "Define by", "GSI", kind="enum", options=("GSI",)),
            Field("sigci", "UCS of intact rock", 100000.0, "kPa"),
            Field("gsi", "GSI", 50.0),
            Field("mi", "mi", 10.0),
            Field("d", "D", 0.0),
            Field("set_residual_to_peak", "Set Residual to Peak", True, kind="bool"),
            Field("gsi_residual", "GSI Residual", 50.0),
            Field("mi_residual", "mi Residual", 10.0),
            Field("d_residual", "D Residual", 0.0),
            Field("tensile_cutoff_type", "Tensile Cutoff Type", "None", kind="enum", options=("None",)),
        ),
    ),
    "cam_clay": Criterion(
        "cam_clay",
        "Cam-Clay",
        "soil",
        "principal",
        (
            Field("critical_state_slope", "Critical State Slope", 1.3),
            Field("specific_volume_unit_pressure", "Specific Volume at Unit Pressure", 2.61),
            Field("kappa", "Kappa", 0.025),
            Field("ocr", "Overconsolidation Ratio", 2.0),
            Field("lambda", "Lambda", 0.15),
        ),
    ),
    "modified_cam_clay": Criterion(
        "modified_cam_clay",
        "Modified Cam-Clay",
        "soil",
        "principal",
        (
            Field("critical_state_slope", "Critical State Slope", 1.3),
            Field("specific_volume_unit_pressure", "Specific Volume at Unit Pressure", 2.61),
            Field("kappa", "Kappa", 0.025),
            Field("ocr", "Overconsolidation Ratio", 2.0),
            Field("lambda", "Lambda", 0.15),
        ),
    ),
    "softening_hardening": Criterion(
        "softening_hardening",
        "Softening Hardening",
        "soil",
        "principal",
        (
            Field("peak_tensile", "Peak Tensile Strength", 0.0, "kPa"),
            Field("peak_friction", "Peak Friction Angle", 35.0, "deg"),
            Field("peak_cohesion", "Peak Cohesion", 10.5, "kPa"),
            Field("cone_hardening_type", "Cone Hardening Type", "default", kind="enum", options=("default",)),
            Field("hardening_property", "Hardening Property", 0.005),
            Field("dilation_angle", "Dilation Angle", 0.0, "deg"),
            Field("cone_dilation_type", "Cone Dilation Type", "default", kind="enum", options=("default",)),
            Field("cap_type", "Cap Type", "default", kind="enum", options=("default",)),
            Field("cap_hardening_type", "Cap Hardening Type", "default", kind="enum", options=("default",)),
            Field("initial_mean_stress", "Initial Mean Stress", 1000.0, "kPa"),
            Field("lambda_kappa", "Lambda Kappa", 0.0),
        ),
    ),
    "norsand": Criterion(
        "norsand",
        "NorSand",
        "soil",
        "none",
        (
            Field("m_tc", "M_TC - Critical Friction Ratio", 1.4),
            Field("lambda", "Lambda - Slope of CSL (natural log)", 0.06),
            Field("h0", "H0 - Plastic Hardening Modulus", 75.0),
            Field("chi_tc", "Chi_TC - Dilation Coefficient", 3.2),
            Field("n", "N - Volumetric Coupling Coefficient", 0.05),
            Field("hy", "Hy - Change in Hardening Modulus", 0.0),
            Field("psi0", "Psi0 - Initial State Parameter", -0.025),
            Field("gamma", "Gamma - Altitude of CSL at 1 kPa", 1.2),
            Field("ocr", "OCR", 1.0, "kPa"),
            Field("cap_softening", "Cap Softening", 0.0),
        ),
    ),
    "power_curve": Criterion(
        "power_curve",
        "Power Curve",
        "soil",
        "shear",
        (
            Field("a", "a Parameter", 0.7),
            Field("b", "b Parameter", 1.0),
            Field("c", "c Parameter", 0.0, "kPa"),
            Field("d", "d Parameter", 0.0, "kPa"),
            Field("waviness", "Waviness", 0.0, "deg"),
            Field("residual_a", "Residual a Parameter", 0.7),
            Field("residual_b", "Residual b Parameter", 1.0),
            Field("residual_c", "Residual c Parameter", 0.0, "kPa"),
            Field("residual_d", "Residual d Parameter", 0.0, "kPa"),
            Field("residual_waviness", "Residual Waviness", 0.0, "deg"),
            Field("dilation_ratio", "Dilation Ratio", 0.5),
        ),
    ),
    "barton_bandis": Criterion(
        "barton_bandis",
        "Barton Bandis",
        "rock",
        "shear",
        (
            Field("phi_r", "Phi r", 30.0, "deg"),
            Field("jrc", "JRC", 10.0),
            Field("jcs", "JCS", 1e7, "kPa"),
            Field("residual_dilation", "Dilation Angle", 0.0, "deg"),
            Field("residual_strength", "Residual Strength", 0.0),
        ),
    ),
}


def defaults(key: str) -> dict[str, Union[float, bool, str]]:
    """Default parameter values of a criterion."""

    return {f.key: f.default for f in CRITERIA[key].fields}
