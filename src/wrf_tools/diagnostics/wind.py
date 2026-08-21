from __future__ import annotations

from typing import Any

import numpy as np


def wind_speed(u: Any, v: Any) -> np.ndarray:
    """Return horizontal speed ``sqrt(u^2 + v^2)``."""
    return np.hypot(u, v)


def wind_direction(u: Any, v: Any) -> np.ndarray:
    """Return meteorological direction *from* which wind blows, degrees.

    Uses ``(270 - atan2(v, u) deg) mod 360`` for eastward ``u`` and northward
    ``v`` components, consistent with WMO meteorological convention.
    """
    """Meteorological direction in degrees from which the wind blows."""
    return (270.0 - np.degrees(np.arctan2(v, u))) % 360.0


def wind_speed_direction_to_uv(speed: Any, direction: Any) -> tuple[np.ndarray, np.ndarray]:
    """Convert meteorological wind direction and speed to east/north vectors."""
    radians = np.radians(direction)
    return -np.asarray(speed) * np.sin(radians), -np.asarray(speed) * np.cos(radians)


def angle_between(first: Any, second: Any, *, degrees: bool = True) -> np.ndarray:
    """Return the smallest signed circular displacement from first to second."""
    a = np.asarray(first, dtype=float)
    b = np.asarray(second, dtype=float)
    dot = np.sum(a * b, axis=-1)
    norm = np.linalg.norm(a, axis=-1) * np.linalg.norm(b, axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        angle = np.arccos(np.clip(dot / norm, -1.0, 1.0))
    return np.degrees(angle) if degrees else angle
