"""Spec 013b: Drucker-Prager, Cam-Clay / MCC, Softening-Hardening, simple shear.

Checks against closed forms, an independent fine-step integration of the
MCC rate equations, and the worked examples of the theory manuals of the
reference program (Referencias/Bibliografia/Suelos).
"""

from __future__ import annotations

import math

import numpy as np

from ogr_data.core import simulation as sm
from ogr_data.core.models import defaults


def _n(deg: float) -> float:
    s = math.sin(math.radians(deg))
    return (1.0 + s) / (1.0 - s)


def _run(criterion, params, stiffness=None, **test):
    return sm.simulate(criterion, params, stiffness, sm.TestSimulation(**test))


# ------------------------------------------------------------- Drucker-Prager

DP = dict(defaults("drucker_prager"), peak_q=0.5, peak_k=3.0, residual_q=0.5, residual_k=3.0)


def test_drucker_prager_manual_example_and_flow() -> None:
    # worked example of the reference program: drained triaxial from p = 100 kPa, q_phi = 0.5, k = 3 kPa -> q_f ~ 129 kPa
    r = _run("drucker_prager", DP, test_type="triaxial", max_strain=0.04)
    q_f = 53.0 / (1.0 / math.sqrt(3.0) - 0.5 / 3.0)  # q/sqrt(3) = k + q_phi (100 + q/3)
    assert abs(q_f - 129.0531) < 1e-3 and abs(r.q[-1] - q_f) < 1e-6
    # potential sqrt(J2) - q_psi p: de_v^p / de_q^p = -sqrt(3) q_psi; drained plateau slope in e_a
    d = _run("drucker_prager", dict(DP, dilation_parameter=0.2), test_type="triaxial", max_strain=0.04)
    ratio = -math.sqrt(3.0) * 0.2
    slope = (d.eps_v[-1] - d.eps_v[-2]) / (d.axial_strain[-1] - d.axial_strain[-2])
    assert abs(slope - ratio / (1.0 + ratio / 3.0)) < 1e-6
    # undrained, no dilation: p' constant, failure at q = sqrt(3) (k + q_phi p0)
    u = _run("drucker_prager", DP, test_type="triaxial", seepage="Undrained", max_strain=0.04)
    assert np.allclose(u.p, 100.0, atol=1e-6) and abs(u.q[-1] - math.sqrt(3.0) * 53.0) < 1e-6
    # undrained with dilation: negative excess pore pressure raises p' along the surface (manual Fig. 4.3)
    ud = _run("drucker_prager", dict(DP, dilation_parameter=0.2), test_type="triaxial", seepage="Undrained", max_strain=0.04)
    assert ud.p[-1] > 100.0 and ud.pore_pressure[-1] < u.pore_pressure[-1] and ud.q[-1] > u.q[-1]
    # brittle: residual k = 0 drops to q = sqrt(3) q_phi p / (1 - q_phi/sqrt(3)) on the drained path
    b = _run("drucker_prager", dict(DP, set_residual_to_peak=False, residual_k=0.0), test_type="triaxial", max_strain=0.04)
    q_r = 50.0 / (1.0 / math.sqrt(3.0) - 0.5 / 3.0)
    assert abs(b.q[-1] - q_r) < 1e-6
    # tension cut-off (manual eq. 4.3): uniaxial tension stops at -T
    t = _run("drucker_prager", dict(DP, peak_tensile=2.0), test_type="uniaxial", loading="Tension", max_strain=0.01)
    assert abs(t.axial_stress.min() + 2.0) < 1e-9


# ------------------------------------------------------------- Cam-Clay family

MCC_TABLE = {"critical_state_slope": 1.2, "specific_volume_unit_pressure": 1.788, "lambda": 0.077, "kappa": 0.0066}
NU = {"poisson": 0.3}


def _mcc(ocr=1.0, key="modified_cam_clay"):
    return dict(defaults(key), ocr=ocr, **MCC_TABLE)


def _mcc_reference(p0: float, ocr: float, q_end: float, n: int = 200000) -> np.ndarray:
    """Independent fine-step integration of the MCC rate equations (drained triaxial, dp = dq/3).

    Columns: axial strain, volumetric strain, q. Same elasticity (K = v p / kappa,
    constant Poisson's ratio) and hardening (dpc/pc = v de_v^p / (lambda - kappa)).
    """

    M, lam, kap, nu, N = 1.2, 0.077, 0.0066, 0.3, 1.788
    pc = ocr * p0
    v = N - lam * math.log(pc) + kap * math.log(pc / p0)
    p, q, ev, eq = p0, 0.0, 0.0, 0.0
    dq = q_end / n
    rows = [(0.0, 0.0, 0.0)]
    for i in range(n):
        dp = dq / 3.0
        G = 3.0 * (v * p / kap) * (1.0 - 2.0 * nu) / (2.0 * (1.0 + nu))
        dev, deq = kap * dp / (v * p), dq / (3.0 * G)
        if q * q + M * M * p * (p - pc) >= -1e-9 * (M * pc) ** 2:
            fp, fq, fpc = M * M * (2.0 * p - pc), 2.0 * q, -M * M * p
            lam_dot = -(fp * dp + fq * dq) / (fpc * pc * v * fp / (lam - kap))
            pc += pc * v * lam_dot * fp / (lam - kap)
            dev += lam_dot * fp
            deq += lam_dot * fq
        v -= v * dev
        p, q, ev, eq = p + dp, q + dq, ev + dev, eq + deq
        if i % 100 == 0:
            rows.append((eq + ev / 3.0, ev, q))
    return np.array(rows)


def test_mcc_normally_consolidated_against_reference_and_manual() -> None:
    ref = _mcc_reference(200.0, 1.0, 398.0)
    r = _run("modified_cam_clay", _mcc(), NU, test_type="triaxial", confining=200.0, max_strain=0.2, steps=1000)
    for ea in (0.02, 0.05, 0.1, 0.2):
        q_m, q_r = np.interp(ea, r.axial_strain, r.q), np.interp(ea, ref[:, 0], ref[:, 2])
        ev_m, ev_r = np.interp(ea, r.axial_strain, r.eps_v), np.interp(ea, ref[:, 0], ref[:, 1])
        assert abs(q_m / q_r - 1.0) < 0.005 and abs(ev_m / ev_r - 1.0) < 0.005, (ea, q_m, q_r, ev_m, ev_r)
    # the reference program's default 100 steps: within 1 % of the reference at the end of the test
    r100 = _run("modified_cam_clay", _mcc(), NU, test_type="triaxial", confining=200.0, max_strain=0.2)
    assert abs(r100.q[-1] / np.interp(0.2, ref[:, 0], ref[:, 2]) - 1.0) < 0.01
    # documented comparison with the manual (Fig. 8.5, read from the plot): q ~ 385-390 kPa and
    # e_v ~ 0.051 (analytic) / 0.055 (reference program) at e_a = 0.2; OGR: q = 374.6 kPa (3 % lower), e_v = 0.062
    assert abs(r.q[-1] - 387.0) / 387.0 < 0.05 and 0.05 < r.eps_v[-1] < 0.065
    # hardening and compaction towards the critical state q = M p (drained: p = 200 + q/3 -> q_cs = 400)
    assert np.all(np.diff(r.q) > 0.0) and np.all(np.diff(r.eps_v) > 0.0) and r.q[-1] < 400.0


def test_mcc_overconsolidated_and_undrained() -> None:
    # OCR = 2 (manual Fig. 8.7): elastic until the initial surface pc = 200 kPa, then hardening to q_cs = 200
    r = _run("modified_cam_clay", _mcc(2.0), NU, test_type="triaxial", confining=100.0, max_strain=0.2)
    first = int(np.argmax(r.yielded))
    p_y, q_y = r.p[first - 1], r.q[first - 1]
    assert q_y**2 + 1.44 * p_y * (p_y - 200.0) < 0.0  # still inside the initial ellipse
    assert abs(r.q[-1] - 200.0) < 10.0 and r.q[-1] < 200.0
    # OCR = 5 (manual Fig. 8.8): dry side, peak then softening with dilation towards the CSL
    h = _run("modified_cam_clay", _mcc(5.0), NU, test_type="triaxial", confining=100.0, max_strain=0.2)
    assert h.peak_q > 1.2 * h.q[-1] and h.eps_v[-1] < 0.0 and abs(h.q[-1] - 200.0) < 15.0
    # undrained NC: no volume change, ends on the CSL q = M p' with positive excess pore pressure
    u = _run("modified_cam_clay", _mcc(), NU, test_type="triaxial", seepage="Undrained", confining=200.0, max_strain=0.2)
    assert np.allclose(u.eps_v, 0.0, atol=1e-14) and abs(u.q[-1] / u.p[-1] - 1.2) < 0.01
    assert u.pore_pressure[-1] > 0.0 and abs(u.pore_pressure[-1] - (200.0 - u.stress[-1, 1])) < 1e-9
    # swelling line (K = v p / kappa integrated exactly over the step): OCR 2 starts elastic,
    # e_v = kappa / v0 ln(p1 / p0)
    v0 = 1.788 - 0.077 * math.log(200.0) + 0.0066 * math.log(2.0)
    assert not r.yielded[1] and abs(r.eps_v[1] / (0.0066 / v0 * math.log(r.p[1] / 100.0)) - 1.0) < 1e-9


def test_original_cam_clay() -> None:
    cc = _mcc(key="cam_clay")
    r = _run("cam_clay", cc, NU, test_type="triaxial", confining=200.0, max_strain=0.3)
    # starts at the tip of the log curve (a corner), hardens and compacts towards q = M p
    assert np.all(np.diff(r.q) > -1e-9) and r.eps_v[-1] > 0.0
    p, q = r.p[-1], r.q[-1]
    assert q / p < 1.2 and q / p > 1.1
    # stress state on the current yield surface q + M p ln(p / pc) = 0 with pc from the hardening law
    assert np.all(r.yielded[1:])


# --------------------------------------------------------- Softening-Hardening

SH = dict(defaults("softening_hardening"), peak_cohesion=0.0, peak_friction=35.0, hardening_property=0.0038)
HOSTUN = {"young": 180000.0, "poisson": 0.35}


def test_softening_hardening_hyperbolic_law() -> None:
    """Drained triaxial, c = 0: sigma1/sigma3 = N(phi_m) with tan(phi_m) = tan(phi_f) k/(k + A), eq. 11.4."""

    # the Mohr-Coulomb potential, explicit since spec 026 made compaction-dilation the default
    r = _run("softening_hardening", dict(SH, cone_dilation_type="Mohr-Coulomb"), HOSTUN, test_type="triaxial", confining=300.0, max_strain=0.15)
    G = 180000.0 / (2.0 * 1.35)
    kappa = r.eps_q - r.q / (3.0 * G)  # deviatoric plastic strain (triaxial: e_q = e_q^e + e_q^p)
    tan_f = math.tan(math.radians(35.0))
    for i in (10, 30, 100):
        phi_m = math.degrees(math.atan(tan_f * kappa[i] / (kappa[i] + 0.0038)))
        assert abs(r.sigma1[i] / r.sigma3[i] - _n(phi_m)) < 2e-3, (i, r.sigma1[i] / r.sigma3[i], _n(phi_m))
    # plastic from the start (manual §11: no initial elastic range), q tends to (N(35) - 1) 300 = 807 kPa
    assert r.yielded[1] and 700.0 < r.q[-1] < 807.0
    # psi = 0 with the Mohr-Coulomb potential: no plastic volume change
    e_el = (r.p - 300.0) / (180000.0 / (3.0 * (1.0 - 0.7)))
    assert np.allclose(r.eps_v, e_el, atol=1e-9)


def test_softening_hardening_loose_hostun_manual_example() -> None:
    # Manual Fig. 11.4 (loose Hostun sand): E = 180 MPa, nu = 0.35, phi_f = 35, psi = 33.5, A = 0.0038,
    # compaction-dilation potential, sigma3 = 300 kPa. Read from the plot: q ~ 760 kPa at e_q ~ 0.15,
    # e_v rising to ~0.010-0.011 then decreasing (compaction, then dilation once eta > M_psi).
    sh = dict(SH, dilation_angle=33.5, cone_dilation_type="Compaction-Dilation")
    r = _run("softening_hardening", sh, HOSTUN, test_type="triaxial", confining=300.0, max_strain=0.15)
    assert abs(r.q[-1] - 760.0) / 760.0 < 0.03
    peak = int(np.argmax(r.eps_v))
    assert 0.009 < r.eps_v[peak] < 0.013 and 0 < peak < len(r.eps_v) - 1 and r.eps_v[-1] < r.eps_v[peak]
    # tension cut-off is part of the model (manual eq. 11.11)
    t = _run("softening_hardening", dict(SH, peak_cohesion=10.0, peak_tensile=1.5), HOSTUN, test_type="uniaxial", loading="Tension", max_strain=0.001)
    assert abs(t.axial_stress.min() + 1.5) < 1e-6


# ----------------------------------------------------------------- simple shear


def test_simple_shear_davis_and_elastic() -> None:
    mc = dict(defaults("mohr_coulomb"), peak_cohesion=0.0, peak_friction=30.0)
    for psi in (0.0, 10.0):
        r = _run("mohr_coulomb", dict(mc, dilation=psi), test_type="simple_shear", confining=100.0, max_strain=0.1)
        f, p = math.radians(30.0), math.radians(psi)
        davis = math.sin(f) * math.cos(p) / (1.0 - math.sin(f) * math.sin(p))  # Davis (1968), coaxial plane strain
        assert abs(r.shear_stress[-1] / r.stress[-1, 0] / davis - 1.0) < 1e-4  # asymptote reached
        assert np.allclose(r.stress[:, 0], 100.0, atol=1e-6)  # drained: constant vertical stress
        assert np.allclose(r.strain[:, 1:3], 0.0)  # no lateral strains
    # elastic start: tau = G gamma
    G = 20000.0 / 2.6
    assert abs(r.shear_stress[1] / r.shear_strain[1] / G - 1.0) < 1e-6
    # undrained MCC simple shear ends on the critical state line
    u = _run("modified_cam_clay", _mcc(), NU, test_type="simple_shear", seepage="Undrained", confining=200.0, max_strain=0.2)
    assert np.allclose(u.eps_v, 0.0) and abs(u.q[-1] / u.p[-1] - 1.2) < 0.01
    assert abs(u.pore_pressure[-1] - (200.0 - u.stress[-1, 0])) < 1e-9
    # Tension = reverse shear
    neg = _run("mohr_coulomb", mc, test_type="simple_shear", loading="Tension", confining=100.0, max_strain=0.1)
    assert neg.shear_stress[-1] < 0.0 and neg.eps_q[-1] < 0.0


def test_softening_hardening_enum_options() -> None:
    fields = {f.key: f for f in __import__("ogr_data.core.models", fromlist=["CRITERIA"]).CRITERIA["softening_hardening"].fields}
    assert fields["cone_dilation_type"].options == sm.CONE_DILATION_TYPES
    assert fields["cap_type"].options == ("None", "Vertical", "Elliptical")
    assert fields["cone_hardening_type"].options == ("Hyperbolic", "Tabular")
    # files saved before 13b carry "default": read as the Mohr-Coulomb potential
    old = dict(SH, cone_dilation_type="default")
    a = _run("softening_hardening", old, HOSTUN, test_type="triaxial", confining=300.0, max_strain=0.02)
    b = _run("softening_hardening", dict(SH, cone_dilation_type="Mohr-Coulomb"), HOSTUN, test_type="triaxial", confining=300.0, max_strain=0.02)
    assert np.allclose(a.q, b.q)
