"""General atmospheric diagnostics used by the migrated scripts."""
from __future__ import annotations

from typing import Any

import numpy as np

RD = 287.05
CP = 1004.0
G = 9.80665
P0 = 100000.0


def potential_temperature(perturbation_theta: Any, base_theta: float = 300.0) -> np.ndarray:
    return np.asarray(perturbation_theta) + base_theta


def temperature_from_potential(theta: Any, pressure: Any) -> np.ndarray:
    return np.asarray(theta) * (np.asarray(pressure) / P0) ** (RD / CP)


def virtual_temperature(temperature: Any, water_vapor: Any) -> np.ndarray:
    return np.asarray(temperature) * (1.0 + 0.61 * np.asarray(water_vapor))


def air_density(pressure: Any, temperature: Any, water_vapor: Any = 0.0) -> np.ndarray:
    return np.asarray(pressure) / (RD * virtual_temperature(temperature, water_vapor))


def geopotential_height(perturbation: Any, base: Any = 0.0) -> np.ndarray:
    return (np.asarray(perturbation) + np.asarray(base)) / G


def bulk_richardson_number(theta_v_low: Any, theta_v_high: Any, z_low: Any, z_high: Any, u_low: Any, u_high: Any, v_low: Any, v_high: Any) -> np.ndarray:
    theta_ref = 0.5 * (np.asarray(theta_v_low) + np.asarray(theta_v_high))
    shear2 = (np.asarray(u_high)-np.asarray(u_low))**2 + (np.asarray(v_high)-np.asarray(v_low))**2
    return (G / theta_ref) * (np.asarray(theta_v_high)-np.asarray(theta_v_low)) * (np.asarray(z_high)-np.asarray(z_low)) / np.maximum(shear2, np.finfo(float).eps)


def power_law_exponent(speed_low: Any, speed_high: Any, z_low: Any, z_high: Any) -> np.ndarray:
    return np.log(np.asarray(speed_high) / np.asarray(speed_low)) / np.log(np.asarray(z_high) / np.asarray(z_low))


def interval_precipitation(accumulated: Any, *, axis: int = 0, prepend_zero: bool = False) -> np.ndarray:
    values = np.asarray(accumulated)
    prepend = 0.0 if prepend_zero else np.take(values, [0], axis=axis)
    return np.diff(values, axis=axis, prepend=prepend)


def reflectivity_to_rain_rate(dbz: Any, *, coefficient: float = 200.0, exponent: float = 1.6) -> np.ndarray:
    return (10.0 ** (np.asarray(dbz) / 10.0) / coefficient) ** (1.0 / exponent)


def friction_velocity(surface_stress: Any, density: Any) -> np.ndarray:
    return np.sqrt(np.abs(np.asarray(surface_stress)) / np.asarray(density))


def monin_obukhov_length(theta_v: Any, friction_velocity_value: Any, heat_flux: Any, *, kappa: float = 0.4) -> np.ndarray:
    denominator = kappa * G * np.asarray(heat_flux)
    return -np.asarray(theta_v) * np.asarray(friction_velocity_value) ** 3 / np.where(denominator == 0, np.nan, denominator)


def circular_mean(direction: Any, *, weights: Any | None = None, axis: int | None = None) -> np.ndarray:
    angle = np.deg2rad(direction)
    weight = 1.0 if weights is None else np.asarray(weights)
    sine = np.sum(weight*np.sin(angle), axis=axis)
    cosine = np.sum(weight*np.cos(angle), axis=axis)
    return np.rad2deg(np.arctan2(sine, cosine)) % 360.0

def roughness_length(speed: Any, height: Any, friction_velocity_value: Any, *, kappa: float = 0.4) -> np.ndarray:
    return np.asarray(height)*np.exp(-kappa*np.asarray(speed)/np.asarray(friction_velocity_value))

def log_wind_profile(height: Any, *, friction_velocity_value: Any, roughness: Any, displacement: float = 0.0, kappa: float = 0.4) -> np.ndarray:
    return np.asarray(friction_velocity_value)/kappa*np.log((np.asarray(height)-displacement)/np.asarray(roughness))

def mixing_ratio_to_specific_humidity(mixing_ratio: Any) -> np.ndarray:
    value=np.asarray(mixing_ratio); return value/(1+value)
