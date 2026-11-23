"""Generalized Hoek-Brown criterion (2002 edition).

Formulas from Hoek, Carranza-Torres & Corkum (2002), validated against
ORMAS V2.0 (see spec 001). Internal stress unit: MPa.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

import numpy as np


class ModulusMethod(Enum):
    """Empirical rock mass modulus estimation methods."""

    HOEK_DIEDERICHS_2006 = "hoek_diederichs_2006"
    HOEK_DIEDERICHS_2006_SIMPLIFIED = "hoek_diederichs_2006_simplified"
    HOEK_CARRANZA_TORRES_CORKUM_2002 = "hoek_carranza_torres_corkum_2002"


@dataclass(frozen=True)
class HbInput:
    """Inputs of the generalized Hoek-Brown criterion.

    sigci: intact uniaxial compressive strength (MPa)
    gsi: Geological Strength Index
    mi: intact rock material constant
    disturbance: disturbance factor D (0 to 1)
    sig3max: upper bound of the fitting range sigma3 (MPa)
    ei: intact elastic modulus (MPa), used by modulus methods
    """

    sigci: float = 30.0
    gsi: float = 50.0
    mi: float = 10.0
    disturbance: float = 0.0
    sig3max: float = 7.5
    ei: float = 12000.0

    def __post_init__(self) -> None:
        if self.sigci <= 0:
            raise ValueError("sigci must be positive")
        if not 1 <= self.gsi <= 100:
            raise ValueError("gsi must be in [1, 100]")
        if self.mi <= 0:
            raise ValueError("mi must be positive")
        if not 0 <= self.disturbance <= 1:
            raise ValueError("disturbance D must be in [0, 1]")
        if self.sig3max <= 0:
            raise ValueError("sig3max must be positive")


@dataclass(frozen=True)
class McEquivalent:
    """Mohr-Coulomb parameters equivalent to a curved envelope."""

    cohesion: float
    friction_deg: float


@dataclass(frozen=True)
class HbResult:
    """Computed Hoek-Brown rock mass parameters (MPa, degrees)."""

    mb: float
    s: float
    a: float
    sigt: float
    sigc: float
    sigcm: float
    mc: McEquivalent
    erm: float


def hoek_brown_constants(inp: HbInput) -> tuple[float, float, float]:
    """mb, s and a of the generalized Hoek-Brown criterion (2002)."""

    mb = inp.mi * math.exp((inp.gsi - 100.0) / (28.0 - 14.0 * inp.disturbance))
    s = math.exp((inp.gsi - 100.0) / (9.0 - 3.0 * inp.disturbance))
    a = 0.5 + (math.exp(-inp.gsi / 15.0) - math.exp(-20.0 / 3.0)) / 6.0
    return mb, s, a


def major_principal_stress(inp: HbInput, mb: float, s: float, a: float, sig3: np.ndarray) -> np.ndarray:
    """sigma1 of the Hoek-Brown envelope for the given sigma3 values (MPa)."""

    return sig3 + inp.sigci * (mb * sig3 / inp.sigci + s) ** a


def tensile_strength(inp: HbInput, mb: float, s: float) -> float:
    """Rock mass tensile strength sigt (MPa, negative)."""

    return -s * inp.sigci / mb


def uniaxial_compressive_strength(inp: HbInput, s: float, a: float) -> float:
    """Rock mass uniaxial compressive strength sigc (MPa)."""

    return inp.sigci * s**a


def global_strength(inp: HbInput, mb: float, s: float, a: float) -> float:
    """Global rock mass compressive strength sigcm (MPa)."""

    return (
        inp.sigci
        * ((mb + 4.0 * s - a * (mb - 8.0 * s)) * (mb / 4.0 + s) ** (a - 1.0))
        / (2.0 * (1.0 + a) * (2.0 + a))
    )


def equivalent_mc(inp: HbInput, mb: float, s: float, a: float, points: int = 200) -> McEquivalent:
    """Equivalent Mohr-Coulomb parameters over sigt < sigma3 < sig3max.

    Hoek, Carranza-Torres & Corkum (2002), eqs. 12 and 13, with
    sigma3n = sig3max / sigci:

        X = 6 a mb (s + mb sigma3n)^(a-1)
        sin(phi') = X / (2(1+a)(2+a) + X)                                (12)
        c' = sigci [(1+2a) s + (1-a) mb sigma3n] (s + mb sigma3n)^(a-1)
             / ((1+a)(2+a) sqrt(1 + X / ((1+a)(2+a))))                  (13)

    Validated against ORMAS V2.0 for the Custom (sig3max = 7.5 MPa),
    Tunnel and Slope cases (specs 001 and 009). The earlier form
    c' = sigcm (1 - sin phi') / (2 cos phi') is only valid for
    sig3max = sigci/4, the range of eq. 17 that defines sigcm.
    """

    sig3n = inp.sig3max / inp.sigci
    k = (1.0 + a) * (2.0 + a)
    base = (s + mb * sig3n) ** (a - 1.0)
    x_term = 6.0 * a * mb * base
    sin_phi = x_term / (2.0 * k + x_term)
    friction = math.degrees(math.asin(sin_phi))
    cohesion = (
        inp.sigci * ((1.0 + 2.0 * a) * s + (1.0 - a) * mb * sig3n) * base
        / (k * math.sqrt(1.0 + x_term / k))
    )
    return McEquivalent(cohesion=cohesion, friction_deg=friction)


def rock_mass_modulus(inp: HbInput, method: ModulusMethod = ModulusMethod.HOEK_DIEDERICHS_2006) -> float:
    """Rock mass deformation modulus Erm (MPa).

    - Generalized Hoek & Diederichs (2006): Ei (0.02 + (1-D/2) /
      (1 + e^((60+15D-GSI)/11)))  (Practical Rock Engineering 2023, eq. 22)
    - Simplified Hoek & Diederichs (2006): 100000 (1-D/2) /
      (1 + e^((75+25D-GSI)/11))  (idem, eq. 20; no 0.02 term)
    - Hoek, Carranza-Torres & Corkum (2002), eq. 11: Em (GPa) = (1-D/2)
      sqrt(sigci/100) 10^((GSI-10)/40); for sigci > 100 MPa the square root
      term is 1 (Practical Rock Engineering 2023, rock mass spreadsheet:
      IF(sigci>100, 1000*10^((GSI-10)/40), ...)). Returned in MPa.
    All three agree with ORMAS V2.0 (its code, saved in ORMAS_analisis).
    """

    d = inp.disturbance
    if method is ModulusMethod.HOEK_DIEDERICHS_2006:
        return inp.ei * (0.02 + (1.0 - d / 2.0) / (1.0 + math.exp((60.0 + 15.0 * d - inp.gsi) / 11.0)))
    if method is ModulusMethod.HOEK_DIEDERICHS_2006_SIMPLIFIED:
        return 100000.0 * (1.0 - d / 2.0) / (1.0 + math.exp((75.0 + 25.0 * d - inp.gsi) / 11.0))
    strength_term = math.sqrt(min(inp.sigci, 100.0) / 100.0)
    return 1000.0 * (1.0 - d / 2.0) * strength_term * 10.0 ** ((inp.gsi - 10.0) / 40.0)


def compute(inp: HbInput, method: ModulusMethod = ModulusMethod.HOEK_DIEDERICHS_2006) -> HbResult:
    """Full Hoek-Brown rock mass parameter set."""

    mb, s, a = hoek_brown_constants(inp)
    return HbResult(
        mb=mb,
        s=s,
        a=a,
        sigt=tensile_strength(inp, mb, s),
        sigc=uniaxial_compressive_strength(inp, s, a),
        sigcm=global_strength(inp, mb, s, a),
        mc=equivalent_mc(inp, mb, s, a),
        erm=rock_mass_modulus(inp, method),
    )
