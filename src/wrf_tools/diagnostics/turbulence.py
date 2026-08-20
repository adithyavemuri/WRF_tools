from __future__ import annotations

from typing import Any

import numpy as np


def fluctuations(data: Any, *, axis: int | tuple[int, ...] = 0) -> np.ndarray:
    array = np.asarray(data, dtype=float)
    return array - np.mean(array, axis=axis, keepdims=True)


def resolved_tke(u: Any, v: Any, w: Any, *, axis: int | tuple[int, ...] = 0) -> np.ndarray:
    up = fluctuations(u, axis=axis)
    vp = fluctuations(v, axis=axis)
    wp = fluctuations(w, axis=axis)
    return 0.5 * np.mean(up * up + vp * vp + wp * wp, axis=axis)


def reynolds_flux(first: Any, second: Any, *, axis: int | tuple[int, ...] = 0) -> np.ndarray:
    return np.mean(fluctuations(first, axis=axis) * fluctuations(second, axis=axis), axis=axis)


def turbulence_intensity(velocity: Any, *, axis: int = 0, percent: bool = True) -> np.ndarray:
    array = np.asarray(velocity, dtype=float)
    intensity = np.std(array, axis=axis) / np.abs(np.mean(array, axis=axis))
    return intensity * 100.0 if percent else intensity
