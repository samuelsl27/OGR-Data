# SPDX-License-Identifier: AGPL-3.0-or-later
"""Spec 026: anomalies of the material parameters.

Invariants:

- defaults inside the published ranges (NorSand N, Barton-Bandis JCS);
- every registry field is read by some calculation, or is marked
  ``used=False`` and shown disabled with its reason (rule 7 of AGENTS.md);
- Power Curve: tau = a (sigma_n + d)^b + c + sigma_n tan(i), every stress
  in kPa (a as well), with old projects converted when opened;
- an Elastic material never yields in a test simulation.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np

from ogr_data.core import criteria_envelopes as ce
from ogr_data.core.models import CRITERIA, defaults

ROOT = Path(__file__).resolve().parent.parent


def test_defaults_inside_published_ranges() -> None:
    """RF-1, RF-2, RF-6."""

    assert defaults("norsand")["n"] == 0.43  # Fraser River sand (Jefferies, Shuttle & Been 2015, Table 2)
    assert 0.2 <= defaults("norsand")["n"] <= 0.5
    assert defaults("barton_bandis")["jcs"] == 100000.0  # kPa: the default intact UCS (Barton & Choubey 1977)
    assert defaults("barton_bandis")["jcs"] == defaults("generalized_hoek_brown")["sigci"]
    assert defaults("softening_hardening")["cone_dilation_type"] == "Compaction-Dilation"


def test_every_field_is_used_or_marked_unused() -> None:
    """RF-10: a field no calculation reads is marked, and a marked one is really not read."""

    # calculations only: the registry and the file readers (which convert old files) do not count
    skip = {"models.py", "project.py", "roc_import.py"}
    code = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "ogr_data" / "core").glob("*.py") if p.name not in skip)
    wrong = []
    for criterion, model in CRITERIA.items():
        for field in model.fields:
            # a read: params["key"], params.get("key", ...), _f(params, "key") — not a dict-literal write
            pattern = r"(?:\[|get\(|_f\(\s*\w+\s*,\s*)[\"']" + re.escape(field.key) + r"[\"']\s*[\]),]"
            read = re.search(pattern, code) is not None
            if read != field.used:
                wrong.append((criterion, field.key, "read" if read else "not read", "used" if field.used else "unused"))
    assert not wrong, wrong


def test_unused_fields_are_disabled_with_their_reason() -> None:
    """RF-3."""

    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w.ask_unsaved = lambda: "discard"
    try:
        w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("norsand"))
        app.processEvents()
        widget = w._widgets["fluid_bulk_modulus"]
        assert not widget.isEnabled() and "does not use" in widget.toolTip()
        assert w._widgets["n"].isEnabled()
    finally:
        w.close()
        w.deleteLater()


def test_power_curve_in_kpa_with_c_and_waviness() -> None:
    """RF-4, RF-5: every term in kPa; c lifts the curve, i adds sigma_n tan(i)."""

    params = defaults("power_curve")
    params.update({"a": 2.0, "b": 0.8, "c": 30.0, "d": 50.0, "waviness": 5.0})
    normal, shear = ce.shear_curve("power_curve", params, 2.0)  # MPa in, MPa out
    n_kpa = normal * 1000.0
    expected = (2.0 * (n_kpa + 50.0) ** 0.8 + 30.0 + n_kpa * math.tan(math.radians(5.0))) / 1000.0
    assert np.allclose(shear, expected, rtol=1e-12)


def test_power_curve_a_is_converted_from_old_files_and_fits() -> None:
    """RF-5: a fitted or saved with stresses in MPa becomes the kPa value (a_kPa = a_MPa 1000^(1-b))."""

    from ogr_data.core import project as projects

    old = {
        "format": "ogr-data-project/2",
        "materials": [{"name": "PC", "criterion": "power_curve",
                       "parameters": dict(defaults("power_curve"), a=0.9, b=0.85, d=50.0, residual_a=0.5, residual_b=0.7)}],
    }
    material = projects.Project.from_dict(old).materials[0]
    assert math.isclose(material.parameters["a"], 0.9 * 1000.0 ** 0.15)
    assert math.isclose(material.parameters["residual_a"], 0.5 * 1000.0 ** 0.3)
    # the same envelope as before, now with every stress in kPa
    normal, shear = ce.shear_curve("power_curve", material.parameters, 2.0)
    assert np.allclose(shear, 0.9 * (normal + 0.05) ** 0.85, rtol=1e-12)
    # saving writes the new format; opening it converts nothing
    again = projects.Project.from_dict(projects.Project.from_dict(old).to_dict()).materials[0]
    assert math.isclose(again.parameters["a"], material.parameters["a"])


def test_elastic_material_never_yields() -> None:
    """RF-8: with Material Type Elastic the test simulation stays on the elastic line."""

    from ogr_data.core import simulation as sm

    params = defaults("mohr_coulomb")
    assert "Elastic" in next(f for f in CRITERIA["mohr_coulomb"].fields if f.key == "material_type").options
    test = sm.TestSimulation(name="T", test_type="triaxial", confining=100.0, max_strain=0.05)
    plastic = sm.simulate("mohr_coulomb", params, None, test)
    elastic = sm.simulate("mohr_coulomb", dict(params, material_type="Elastic"), None, test)
    assert max(elastic.q) > 2.0 * max(plastic.q)  # the plastic one stops at failure
    ratio = elastic.q[1:] / elastic.axial_strain[1:]
    assert np.allclose(ratio, ratio[0], rtol=1e-6)  # linear: constant slope
