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
    default: Union[float, bool, str, tuple]
    unit: str = ""
    kind: str = "float"  # "float" | "bool" | "enum" | "table"
    options: tuple[str, ...] = ()  # enum options, or the column names of a table
    pick: str = ""  # picker key: "sigci_grades" | "mi_values" | "gsi_chart"
    # table columns holding stresses (kPa), for display units (spec 013)
    stress_columns: tuple[bool, ...] = ()
    # spec 026: False while no calculation of OGR Data reads the field; the
    # form shows it disabled with that reason (rule 7: no setting that does nothing)
    used: bool = True

    def __post_init__(self) -> None:
        if self.kind not in ("float", "bool", "enum", "table"):
            raise ValueError(f"unknown field kind {self.kind!r}")


@dataclass(frozen=True)
class Criterion:
    key: str
    label: str
    category: str  # "rock" | "soil"
    envelope: str  # "principal" | "shear" | "none"
    fields: tuple[Field, ...]


# Cam-Clay / MCC combos of RSData (Modified Cam Clay tutorial, spec 013)
VOLUME_REFERENCES = ("Normal Compression Line (N)", "Critical State Line (Gamma)")
CONSOLIDATION_STATES = ("OCR", "Preconsolidation Pressure (Po)")

# Rock mass modulus methods (labels as in ORMAS; spec 022), same order as
# core.hoek_brown.ModulusMethod.
MODULUS_METHODS = (
    "Generalized Hoek & Diederichs (2006)",
    "Simplified Hoek & Diederichs (2006)",
    "Hoek, Carranza-Torres & Corkum (2002)",
)


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
            Field("material_type", "Material Type", "Plastic", kind="enum", options=("Plastic", "Elastic")),
            Field("peak_cohesion", "Peak Cohesion", 10.5, "kPa", pick="compacted_soil"),
            Field("peak_friction", "Peak Friction Angle", 35.0, "deg", pick="compacted_soil"),
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
            Field("material_type", "Material Type", "Plastic", kind="enum", options=("Plastic", "Elastic")),
            Field("compressive_strength", "Compressive Strength", 100000.0, "kPa", pick="sigci_grades"),
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
            Field("define_by", "Define by", "GSI", kind="enum", options=("GSI",), used=False),
            Field("sigci", "UCS of intact rock", 100000.0, "kPa", pick="sigci_grades"),
            Field("gsi", "GSI", 50.0, pick="gsi_chart"),
            Field("mi", "mi", 10.0, pick="mi_values"),
            Field("d", "D", 0.0, pick="disturbance"),
            # spec 022: intact modulus and rock mass modulus method (ORMAS-like;
            # RSData uses a hidden fixed Ei). Default Ei = ORMAS default.
            Field("ei", "Intact modulus Ei", 12000000.0, "kPa", pick="modulus_ratio"),
            Field("modulus_method", "Erm method", MODULUS_METHODS[0], kind="enum", options=MODULUS_METHODS),
            Field("set_residual_to_peak", "Set Residual to Peak", True, kind="bool"),
            Field("gsi_residual", "GSI Residual", 50.0),
            Field("mi_residual", "mi Residual", 10.0),
            Field("d_residual", "D Residual", 0.0),
            Field("tensile_cutoff_type", "Tensile Cutoff Type", "None", kind="enum", options=("None",), used=False),
        ),
    ),
    "cam_clay": Criterion(
        "cam_clay",
        "Cam-Clay",
        "soil",
        "principal",
        (
            Field("critical_state_slope", "Critical State Slope", 1.3),
            # spec 013: RSData combo (MCC tutorial): the value is N or Gamma
            Field("volume_reference", "Specific Volume Reference", VOLUME_REFERENCES[0], kind="enum", options=VOLUME_REFERENCES),
            Field("specific_volume_unit_pressure", "Specific Volume at Unit Pressure", 2.61),
            Field("kappa", "Kappa", 0.025),
            Field("initial_consolidation", "Initial State of Consolidation", CONSOLIDATION_STATES[0], kind="enum", options=CONSOLIDATION_STATES),
            Field("ocr", "Overconsolidation Ratio", 2.0),
            Field("preconsolidation_stress", "Preconsolidation Stress", 200.0, "kPa"),
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
            # spec 013: RSData combo (MCC tutorial): the value is N or Gamma
            Field("volume_reference", "Specific Volume Reference", VOLUME_REFERENCES[0], kind="enum", options=VOLUME_REFERENCES),
            Field("specific_volume_unit_pressure", "Specific Volume at Unit Pressure", 2.61),
            Field("kappa", "Kappa", 0.025),
            Field("initial_consolidation", "Initial State of Consolidation", CONSOLIDATION_STATES[0], kind="enum", options=CONSOLIDATION_STATES),
            Field("ocr", "Overconsolidation Ratio", 2.0),
            Field("preconsolidation_stress", "Preconsolidation Stress", 200.0, "kPa"),
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
            Field("peak_friction", "Peak Friction Angle", 35.0, "deg", pick="compacted_soil"),
            Field("peak_cohesion", "Peak Cohesion", 10.5, "kPa", pick="compacted_soil"),
            # spec 013b: options named after the RS2 manual (§11; RSData combo values not captured)
            Field("cone_hardening_type", "Cone Hardening Type", "Hyperbolic", kind="enum", options=("Hyperbolic", "Tabular")),
            Field("hardening_property", "Hardening Property", 0.005),
            # Tabular cone hardening (manual §11.1): mobilized friction angle and
            # cohesion versus deviatoric plastic strain, piecewise linear
            Field(
                "cone_hardening_table", "Cone Hardening Table", ((0.0, 0.0, 0.0), (0.01, 35.0, 10.5)), kind="table",
                options=("Plastic Deviatoric Strain", "Friction Angle (deg)", "Cohesion"), stress_columns=(False, False, True),
            ),
            Field("dilation_angle", "Dilation Angle", 0.0, "deg"),
            Field("cone_dilation_type", "Cone Dilation Type", "Compaction-Dilation", kind="enum", options=("Mohr-Coulomb", "Compaction-Dilation")),
            Field("cap_type", "Cap Type", "None", kind="enum", options=("None", "Vertical", "Elliptical")),
            Field("cap_hardening_type", "Cap Hardening Type", "Cam-Clay", kind="enum", options=("Cam-Clay", "Tabular")),
            Field("initial_mean_stress", "Initial Mean Stress", 1000.0, "kPa"),
            Field("lambda_kappa", "Lambda Kappa", 0.0),
            # Tabular cap hardening (manual §11.2): pc versus volumetric plastic strain
            Field(
                "cap_hardening_table", "Cap Hardening Table", ((0.0, 1000.0), (0.05, 2000.0)), kind="table",
                options=("Plastic Volumetric Strain", "Cap Pressure pc"), stress_columns=(False, True),
            ),
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
            Field("n", "N - Volumetric Coupling Coefficient", 0.43),  # spec 026: Fraser River sand (Jefferies, Shuttle & Been 2015)
            Field("hy", "Hy - Change in Hardening Modulus", 0.0),
            Field("psi0", "Psi0 - Initial State Parameter", -0.025),
            Field("gamma", "Gamma - Altitude of CSL at 1 kPa", 1.2),
            # RSData labels OCR "(kPa)" (tutorial capture); it is a ratio
            Field("initial_consolidation_condition", "Initial Consolidation Condition", "OCR", kind="enum", options=("OCR",), used=False),
            Field("ocr", "OCR", 1.0),
            Field("cap_softening", "Cap Softening", False, kind="bool", used=False),
            Field("fluid_bulk_modulus", "Fluid Bulk Modulus", 1e9, "kPa", used=False),
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
            Field("residual_a", "Residual a Parameter", 0.7, used=False),
            Field("residual_b", "Residual b Parameter", 1.0, used=False),
            Field("residual_c", "Residual c Parameter", 0.0, "kPa", used=False),
            Field("residual_d", "Residual d Parameter", 0.0, "kPa", used=False),
            Field("residual_waviness", "Residual Waviness", 0.0, "deg", used=False),
            Field("dilation_ratio", "Dilation Ratio", 0.5, used=False),
        ),
    ),
    "barton_bandis": Criterion(
        "barton_bandis",
        "Barton Bandis",
        "rock",
        "shear",
        (
            Field("phi_r", "Phi r", 30.0, "deg", pick="barton_phi"),
            Field("jrc", "JRC", 10.0, pick="barton_jrc"),
            Field("jcs", "JCS", 1e5, "kPa", pick="barton_jcs"),  # spec 026: fresh walls = intact UCS (Barton & Choubey 1977)
            Field("residual_dilation", "Dilation Angle", 0.0, "deg", used=False),
            Field("residual_strength", "Residual Strength", 0.0, used=False),
        ),
    ),
}


def defaults(key: str) -> dict[str, Union[float, bool, str]]:
    """Default parameter values of a criterion."""

    return {f.key: ([list(row) for row in f.default] if f.kind == "table" else f.default) for f in CRITERIA[key].fields}
