"""General atmospheric diagnostics used by the migrated scripts."""
from __future__ import annotations

from typing import Any

import numpy as np

RD = 287.05
CP = 1004.0
G = 9.80665
P0 = 100000.0


def potential_temperature(perturbation_theta: Any, base_theta: float = 300.0) -> np.ndarray:
    """Recover WRF potential temperature as ``theta = T + T0``.

    WRF stores perturbation potential temperature and normally uses
    ``T0 = 300 K``. See Skamarock et al. (2019), ARW v4 Technical Note,
    doi:10.5065/1dfh-6p97, section 2.1.
    """
    return np.asarray(perturbation_theta) + base_theta


def temperature_from_potential(theta: Any, pressure: Any) -> np.ndarray:
    """Convert potential temperature to temperature using Poisson's equation.

    ``T = theta (p/p0)^(Rd/cp)``. See Wallace and Hobbs (2006),
    *Atmospheric Science*, 2nd ed., doi:10.1016/C2009-0-00034-8.
    """
    return np.asarray(theta) * (np.asarray(pressure) / P0) ** (RD / CP)


def virtual_temperature(temperature: Any, water_vapor: Any) -> np.ndarray:
    """Approximate virtual temperature for water-vapor mixing ratio ``r``.

    Uses ``Tv = T (1 + 0.61 r)``, neglecting condensate. See Wallace and
    Hobbs (2006), doi:10.1016/C2009-0-00034-8.
    """
    return np.asarray(temperature) * (1.0 + 0.61 * np.asarray(water_vapor))


def air_density(pressure: Any, temperature: Any, water_vapor: Any = 0.0) -> np.ndarray:
    """Return moist-air density from ``rho = p/(Rd Tv)``."""
    return np.asarray(pressure) / (RD * virtual_temperature(temperature, water_vapor))


def geopotential_height(perturbation: Any, base: Any = 0.0) -> np.ndarray:
    """Convert WRF total geopotential ``PH + PHB`` to height using ``z=Phi/g``.

    See Skamarock et al. (2019), doi:10.5065/1dfh-6p97.
    """
    return (np.asarray(perturbation) + np.asarray(base)) / G


def bulk_richardson_number(theta_v_low: Any, theta_v_high: Any, z_low: Any, z_high: Any, u_low: Any, u_high: Any, v_low: Any, v_high: Any) -> np.ndarray:
    """Calculate the finite-difference bulk Richardson number.

    The reference virtual potential temperature is the layer mean. See Stull
    (1988), *An Introduction to Boundary Layer Meteorology*,
    doi:10.1007/978-94-009-3027-8.
    """
    theta_ref = 0.5 * (np.asarray(theta_v_low) + np.asarray(theta_v_high))
    shear2 = (np.asarray(u_high)-np.asarray(u_low))**2 + (np.asarray(v_high)-np.asarray(v_low))**2
    return (G / theta_ref) * (np.asarray(theta_v_high)-np.asarray(theta_v_low)) * (np.asarray(z_high)-np.asarray(z_low)) / np.maximum(shear2, np.finfo(float).eps)


def power_law_exponent(speed_low: Any, speed_high: Any, z_low: Any, z_high: Any) -> np.ndarray:
    """Infer the two-height wind-profile exponent ``alpha`` from ``U ~ z^alpha``."""
    return np.log(np.asarray(speed_high) / np.asarray(speed_low)) / np.log(np.asarray(z_high) / np.asarray(z_low))


def interval_precipitation(accumulated: Any, *, axis: int = 0, prepend_zero: bool = False) -> np.ndarray:
    values = np.asarray(accumulated)
    prepend = 0.0 if prepend_zero else np.take(values, [0], axis=axis)
    return np.diff(values, axis=axis, prepend=prepend)


def reflectivity_to_rain_rate(dbz: Any, *, coefficient: float = 200.0, exponent: float = 1.6) -> np.ndarray:
    """Convert dBZ using ``Z = a R^b`` (defaults: ``a=200``, ``b=1.6``).

    The defaults are the conventional Marshall-Palmer stratiform-rain
    relation; coefficients are climate and event dependent. See Marshall,
    Hitschfeld, and Gunn (1955),
    doi:10.1175/1520-0469(1955)012<0322:AOTDOP>2.0.CO;2.
    """
    return (10.0 ** (np.asarray(dbz) / 10.0) / coefficient) ** (1.0 / exponent)


def friction_velocity(surface_stress: Any, density: Any) -> np.ndarray:
    """Return friction velocity ``u* = sqrt(|tau|/rho)`` (Stull, 1988)."""
    return np.sqrt(np.abs(np.asarray(surface_stress)) / np.asarray(density))


def monin_obukhov_length(theta_v: Any, friction_velocity_value: Any, heat_flux: Any, *, kappa: float = 0.4) -> np.ndarray:
    """Return Monin-Obukhov length for kinematic virtual heat flux.

    ``L = -theta_v u*^3 / (kappa g w'theta_v')``. ``heat_flux`` must be in
    K m s-1, not W m-2. See Monin and Obukhov (1954) and Foken (2006),
    doi:10.1007/s10546-006-9048-6.
    """
    denominator = kappa * G * np.asarray(heat_flux)
    return -np.asarray(theta_v) * np.asarray(friction_velocity_value) ** 3 / np.where(denominator == 0, np.nan, denominator)


def circular_mean(direction: Any, *, weights: Any | None = None, axis: int | None = None) -> np.ndarray:
    """Return the vector mean of circular directions (Fisher, 1993)."""
    angle = np.deg2rad(direction)
    weight = 1.0 if weights is None else np.asarray(weights)
    sine = np.sum(weight*np.sin(angle), axis=axis)
    cosine = np.sum(weight*np.cos(angle), axis=axis)
    return np.rad2deg(np.arctan2(sine, cosine)) % 360.0

def roughness_length(speed: Any, height: Any, friction_velocity_value: Any, *, kappa: float = 0.4) -> np.ndarray:
    """Invert the neutral logarithmic wind law for roughness length."""
    return np.asarray(height)*np.exp(-kappa*np.asarray(speed)/np.asarray(friction_velocity_value))

def log_wind_profile(height: Any, *, friction_velocity_value: Any, roughness: Any, displacement: float = 0.0, kappa: float = 0.4) -> np.ndarray:
    """Evaluate the neutral logarithmic wind profile (Stull, 1988)."""
    return np.asarray(friction_velocity_value)/kappa*np.log((np.asarray(height)-displacement)/np.asarray(roughness))

def mixing_ratio_to_specific_humidity(mixing_ratio: Any) -> np.ndarray:
    value=np.asarray(mixing_ratio); return value/(1+value)
