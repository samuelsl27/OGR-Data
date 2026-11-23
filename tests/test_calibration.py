"""Spec 014: calibration against failure states.

Verification case from RSData 1.009 (RSData_analisis/07, section 4):
triaxial (0; 40.3), (100; 409), (200; 778), (300; 1500) kPa.
"""

from __future__ import annotations

import math

import numpy as np

from ogr_data.core import calibration as cal
from ogr_data.core import states as st
from ogr_data.core.hoek_brown import HbInput, hoek_brown_constants

RSDATA = [st.TestPoint(0, 40.3), st.TestPoint(100, 409), st.TestPoint(200, 778), st.TestPoint(300, 1500)]


def _settings(strength="mohr_coulomb", algorithm="levenberg_marquardt", **kw):
    return cal.CalibrationSettings(strength_type=strength, algorithm=algorithm, **kw)


def _state_from(pairs_kpa, test_type="triaxial", name="S"):
    return st.FailureState(name=name, test_type=test_type, points=[st.TestPoint(x, y) for x, y in pairs_kpa])


def test_rsdata_case_with_excluded_point() -> None:
    state = st.FailureState(points=RSDATA[:3] + [st.TestPoint(300, 1500, True)])
    for algorithm in ("linear", "levenberg_marquardt", "simplex"):
        r = cal.calibrate([state], _settings(algorithm=algorithm))
        assert abs(r.parameters["peak_cohesion"] - 10.4788) < 1e-3, algorithm
        assert abs(r.parameters["peak_friction"] - 34.9894) < 1e-3, algorithm
        assert r.n_points == 3 and r.criterion == "mohr_coulomb"
        assert r.parameters["residual_friction"] == r.parameters["peak_friction"]


def test_rsdata_case_all_points_bounded() -> None:
    state = st.FailureState(points=RSDATA)
    # unconstrained optimum has c = -6.97 kPa (non physical): bounded solution c = 0
    r = cal.calibrate([state], _settings())
    assert r.parameters["peak_cohesion"] < 1e-6
    assert abs(r.fitted["friction_deg"] - 40.0902) < 1e-3  # RSData shows 40.5662 (not reproducible)
    assert "bound" in r.method_note
    # Linear Regression has no valid MC line here (negative intercept); RSData
    # kept the starting model in that case
    try:
        cal.calibrate([state], _settings(algorithm="linear"))
    except ValueError as exc:
        assert "valid Mohr-Coulomb" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_two_states_give_parameters_in_between() -> None:
    rng = np.random.default_rng(14)
    s3 = np.linspace(0.0, 400.0, 6)

    def mc(c, phi):
        k = (1 + math.sin(math.radians(phi))) / (1 - math.sin(math.radians(phi)))
        return 2 * c * math.sqrt(k) + k * s3

    a = _state_from(zip(s3, mc(20.0, 30.0) + rng.normal(0, 3, 6)), name="A")
    b = _state_from(zip(s3, mc(40.0, 36.0) + rng.normal(0, 3, 6)), name="B")
    r = cal.calibrate([a, b], _settings())
    assert 20.0 < r.parameters["peak_cohesion"] < 40.0
    assert 30.0 < r.parameters["peak_friction"] < 36.0
    assert r.n_points == 12 and r.rms > 0.0


def test_hoek_brown_lab_and_rock_mass() -> None:
    s3 = np.linspace(0.0, 10.0, 9)
    intact = _state_from(zip(s3 * 1000, (s3 + 120 * np.sqrt(15 * s3 / 120 + 1)) * 1000))
    for algorithm in ("linear", "levenberg_marquardt", "simplex"):
        r = cal.calibrate([intact], _settings("generalized_hoek_brown", algorithm))
        assert abs(r.parameters["sigci"] - 120000.0) < 1.0 and abs(r.parameters["mi"] - 15.0) < 1e-4, algorithm
        assert (r.parameters["gsi"], r.parameters["d"]) == (100.0, 0.0)  # lab data = intact rock
    mb, s, a = hoek_brown_constants(HbInput(sigci=50, gsi=45, mi=12, disturbance=0.5))
    mass = _state_from(zip(s3 * 1000, (s3 + 50 * (mb * s3 / 50 + s) ** a) * 1000))
    settings = _settings("generalized_hoek_brown", data_type="Rock Mass Data", sigci_kpa=50000.0, disturbance=0.5)
    r = cal.calibrate([mass], settings)
    assert abs(r.parameters["gsi"] - 45.0) < 1e-4 and abs(r.parameters["mi"] - 12.0) < 1e-4
    assert (r.parameters["sigci"], r.parameters["d"]) == (50000.0, 0.5)
    settings.algorithm = "linear"
    try:
        cal.calibrate([mass], settings)
    except ValueError as exc:
        assert "rock mass" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_direct_shear_models() -> None:
    sn = np.linspace(0.1, 2.0, 8)
    pc = _state_from(zip(sn * 1000, 0.9 * (sn + 0.05) ** 0.85 * 1000), "direct_shear")
    r = cal.calibrate([pc], _settings("power_curve"))
    assert np.allclose([r.parameters["a"], r.parameters["b"], r.parameters["d"]], [0.9, 0.85, 50.0], atol=1e-4)
    bb = _state_from(zip(sn * 1000, sn * np.tan(np.radians(30 + 12 * np.log10(80 / sn))) * 1000), "direct_shear")
    r = cal.calibrate([bb], _settings("barton_bandis", phi_b_deg=30.0))
    assert abs(r.parameters["jrc"] - 12.0) < 1e-4 and abs(r.parameters["jcs"] - 80000.0) < 1.0
    assert r.parameters["phi_r"] == 30.0
    mc = _state_from(zip(sn * 1000, (0.1 + sn * math.tan(math.radians(35))) * 1000), "direct_shear")
    r = cal.calibrate([mc], _settings(algorithm="linear"))
    assert abs(r.parameters["peak_cohesion"] - 100.0) < 1e-6 and abs(r.parameters["peak_friction"] - 35.0) < 1e-9


def test_relative_error_and_validation() -> None:
    noisy = _state_from([(0, 50), (100, 400), (200, 820), (300, 1100)])
    absolute = cal.calibrate([noisy], _settings())
    relative = cal.calibrate([noisy], _settings(error_type="Relative"))
    assert abs(absolute.parameters["peak_friction"] - relative.parameters["peak_friction"]) > 0.01
    lin_rel = cal.calibrate([noisy], _settings(algorithm="linear", error_type="Relative"))
    assert abs(lin_rel.parameters["peak_friction"] - relative.parameters["peak_friction"]) < 1e-3
    cases = [
        ([noisy, _state_from([(1, 2), (2, 3)], "direct_shear")], _settings(), "together"),
        ([_state_from([(1, 2), (2, 3)], "direct_shear")], _settings("generalized_hoek_brown"), "cannot be calibrated"),
        ([st.FailureState()], _settings(), "no (non-excluded) points"),
        ([noisy], _settings("generalized_hoek_brown", "linear", error_type="Relative"), "transformed"),
    ]
    for states, settings, message in cases:
        try:
            cal.calibrate(states, settings)
        except ValueError as exc:
            assert message in str(exc), (message, exc)
        else:
            raise AssertionError(f"expected ValueError ({message})")
    # a general (tensor) state contributes its principal stresses
    general = st.FailureState(test_type="general", tensors=[(40.3, 0, 0, 0, 0, 0), (409, 100, 100, 0, 0, 0), (778, 200, 200, 0, 0, 0)])
    r = cal.calibrate([general], _settings())
    assert abs(r.parameters["peak_friction"] - 34.9894) < 1e-3


def test_calibration_dialog_creates_material() -> None:
    from PySide6.QtWidgets import QApplication, QDialogButtonBox

    from ogr_data.gui.calibration_dialog import CalibrationDialog
    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        w._set_stress_unit("kPa")
        titles = [a.text() for a in w.menuBar().actions()]
        assert "Calibrate" in titles
        w.set_failure_states([st.FailureState(points=RSDATA[:3] + [st.TestPoint(300, 1500, True)])])
        source_params = dict(w._current_material().parameters)
        dlg = CalibrationDialog(w, w._project, w._current, "kPa")
        try:
            assert dlg.strength.currentData() == "generalized_hoek_brown"  # RSData default
            assert dlg.name.text() == "Calibrated Material"
            assert dlg.states.count() == 1
            dlg.strength.setCurrentIndex(dlg.strength.findData("mohr_coulomb"))
            assert dlg.result is not None and "10.4788" in dlg.output.text()
            assert not dlg.data_type.isEnabled()
            # no state selected: error shown, OK disabled
            from PySide6.QtCore import Qt

            dlg.states.item(0).setCheckState(Qt.CheckState.Unchecked)
            assert dlg.result is None and not dlg._buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
            dlg.states.item(0).setCheckState(Qt.CheckState.Checked)
            dlg.strength.setCurrentIndex(dlg.strength.findData("generalized_hoek_brown"))
            dlg.data_type.setCurrentIndex(1)
            assert dlg._states_form.isRowVisible(dlg.sigci)
            dlg.strength.setCurrentIndex(dlg.strength.findData("mohr_coulomb"))
            assert dlg.data_type.currentIndex() == 0
            result, name = dlg.result, dlg.name.text()
        finally:
            dlg.deleteLater()
        index = w.add_calibrated_material(name, result)
        app.processEvents()
        assert index == 1 and w._current == 1 and w._tree.topLevelItemCount() == 2
        new = w._project.materials[1]
        assert new.name == "Calibrated Material" and new.criterion == "mohr_coulomb"
        assert abs(new.parameters["peak_cohesion"] - 10.4788) < 1e-3
        assert abs(w._widgets["peak_friction"].value() - 34.9894) < 1e-3
        assert w._project.materials[0].parameters == source_params  # source untouched
    finally:
        w.deleteLater()
