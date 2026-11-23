"""catalog: what the program offers, for an agent to discover before it edits."""

from __future__ import annotations

from ...core import calibration as cal
from ...core import fitting
from ...core import gsi_charts
from ...core import report as rpt
from ...core import simulation as sm
from ...core import states as st
from ...core import units
from ...core.models import CRITERIA, MODULUS_METHODS
from ...core.project import APPLICATION_MODES, SYMBOLS, TEMPLATES
from ..errors import choice
from . import operation
from ._common import UNITS, fields_schema

KINDS = (
    "criteria", "templates", "application_modes", "modulus_methods", "fits", "calibration",
    "failure_states", "stress_paths", "test_simulations", "tables", "gsi_charts", "stress_units",
    "report_sections", "symbols",
)

# table name -> description (table_get reads them)
TABLES = {
    "sigci_grades": "Field estimates of uniaxial compressive strength, grades R0-R6 (Hoek, Table 2)",
    "mi_values": "Hoek-Brown constant mi for intact rock (Hoek, Table 3)",
    "gsi_2000_ranges": "GSI ranges by structure x surface condition (Hoek & Marinos 2000 chart)",
    "disturbance_factor": "Disturbance factor D (Practical Rock Engineering 2023, Fig. 9)",
    "modulus_ratio": "Modulus ratio MR = Ei/sigci (Practical Rock Engineering 2023, Fig. 13)",
    "basic_friction_angle": "Basic friction angles phi_b (FHWA-TS-89-045, after Barton)",
    "soil_field_strength": "Soil grades S1-S5 (FHWA-TS-89-045, Table II)",
    "uscs_compacted_properties": "Typical properties of compacted soils by USCS group (UFC 3-220-01N Table 8-3.1)",
}


@operation("catalog", toolset="info")
def catalog(ws, kind: str = "criteria") -> dict:
    """What the program offers: criteria with their parameters, fits, test types, tables..."""

    choice("kind", kind, KINDS)
    if kind == "criteria":
        return {"units": UNITS, "criteria": [
            {"key": c.key, "label": c.label, "category": c.category, "envelope": c.envelope,
             "fits": list(fitting.available_fits(c.key)), "simulated": c.key in sm.SIMULATED_CRITERIA,
             "fields": fields_schema(c.key)}
            for c in CRITERIA.values()]}
    if kind == "templates":
        return {"templates": {k: {"name": n, "criterion": c} for k, (n, c) in TEMPLATES.items()},
                "note": "rock adds an empty failure state; soil adds a test simulation and a stress path (RSData templates)."}
    if kind == "application_modes":
        return {"modes": list(APPLICATION_MODES),
                "note": "tunnel / slope compute sigma3max from sigcm, unit weight and depth (Hoek 2002 / Marinos-Hoek); "
                        "only for generalized_hoek_brown and hoek_brown. custom: sig3max is given."}
    if kind == "modulus_methods":
        return {"modulus_methods": list(MODULUS_METHODS), "parameter": "modulus_method (generalized_hoek_brown)"}
    if kind == "fits":
        return {"fits": [{"criterion": c, "data_kind": k} for c, k in fitting.FITS],
                "methods": [fitting.LINEAR, fitting.LEVENBERG_MARQUARDT, fitting.SIMPLEX],
                "fixed_inputs": {"generalized_hoek_brown": ["sigci_kpa", "disturbance"], "barton_bandis": ["phi_b_deg"]},
                "data_kinds": {fitting.TRIAXIAL: "x = sigma3, y = sigma1 (kPa)", fitting.DIRECT: "x = normal stress, y = shear stress (kPa)"}}
    if kind == "calibration":
        return {"strength_types": cal.STRENGTH_TYPES, "algorithms": cal.ALGORITHMS,
                "error_types": list(cal.ERROR_TYPES), "data_types": list(cal.DATA_TYPES)}
    if kind == "failure_states":
        return {"test_types": st.FAILURE_TEST_TYPES,
                "columns": {"triaxial": ["Sigma3", "Sigma1"], "direct_shear": ["SigmaN", "Tau"], "general": list(st.GENERAL_COLUMNS)},
                "note": "points [[x, y]] or [[x, y, exclude]] in kPa; general: tensors [[sxx, syy, szz, txy, tyz, txz]] in kPa."}
    if kind == "stress_paths":
        return {"test_types": st.PATH_TEST_TYPES, "seepage": list(st.SEEPAGE_CONDITIONS),
                "loading_directions": list(st.LOADING_DIRECTIONS), "strain_types": list(st.STRAIN_TYPES),
                "note": "the step columns depend on the configuration; stress_path_set answers with them."}
    if kind == "test_simulations":
        return {"test_types": sm.TEST_TYPES, "seepage": list(sm.SEEPAGE), "loading": list(sm.LOADING),
                "strain_components": list(sm.STRAIN_COMPONENTS), "simulated_criteria": list(sm.SIMULATED_CRITERIA),
                "stiffness_types": list(sm.STIFFNESS_TYPES), "default_stiffness": dict(sm.DEFAULT_STIFFNESS)}
    if kind == "tables":
        return {"tables": TABLES}
    if kind == "gsi_charts":
        return {"charts": [{"chart": cid, "title": gsi_charts.texts(cid, "en")["title"],
                            "types": gsi_charts.chart_types(cid)} for cid in gsi_charts.CHART_IDS],
                "languages": list(gsi_charts.LANGUAGES),
                "frame": "u = 0 left edge of VERY GOOD .. 1 right edge of VERY POOR; v = 0 top of the first structure row .. 1 bottom of the last."}
    if kind == "stress_units":
        return {"display_units": list(units.STRESS_FACTORS), "api_units": UNITS}
    if kind == "report_sections":
        return {"sections": dict(rpt.SECTIONS)}
    return {"symbols": SYMBOLS}
