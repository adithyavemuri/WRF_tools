from __future__ import annotations

from typing import Any

import numpy as np


def fluctuations(data: Any, *, axis: int | tuple[int, ...] = 0) -> np.ndarray:
    """Subtract an equal-sample mean on explicit axes; justify the decomposition."""
    array = np.asarray(data, dtype=float)
    return array - np.mean(array, axis=axis, keepdims=True)


def resolved_tke(u: Any, v: Any, w: Any, *, axis: int | tuple[int, ...] = 0) -> np.ndarray:
    """Return resolved TKE ``0.5 <u'^2 + v'^2 + w'^2>``.

    See Pope (2000), *Turbulent Flows*, doi:10.1017/CBO9780511840531.
    """
    if not (np.shape(u) == np.shape(v) == np.shape(w)):
        raise ValueError("Velocity components must have identical co-located shapes")
    up = fluctuations(u, axis=axis)
    vp = fluctuations(v, axis=axis)
    wp = fluctuations(w, axis=axis)
    return 0.5 * np.mean(up * up + vp * vp + wp * wp, axis=axis)


def reynolds_flux(first: Any, second: Any, *, axis: int | tuple[int, ...] = 0) -> np.ndarray:
    """Return a Reynolds covariance ``<a'b'>`` (Pope, 2000)."""
    if np.shape(first) != np.shape(second):
        raise ValueError("Flux components must have identical co-located shapes")
    return np.mean(fluctuations(first, axis=axis) * fluctuations(second, axis=axis), axis=axis)


def turbulence_intensity(velocity: Any, *, axis: int = 0, percent: bool = True) -> np.ndarray:
    """Return component TI ``sigma_U / |mean(U)|``; zero mean gives NaN."""
    array = np.asarray(velocity, dtype=float)
    scale = np.abs(np.mean(array, axis=axis))
    intensity = np.divide(np.std(array, axis=axis),scale,out=np.full(np.shape(scale),np.nan),where=scale>0)
    return intensity * 100.0 if percent else intensity
