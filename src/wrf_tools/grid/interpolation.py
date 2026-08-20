from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def interpolate_to_levels(
    field: Any,
    vertical_coordinate: Any,
    levels: float | Iterable[float],
    *,
    axis: int = -3,
) -> np.ndarray:
    """Linearly interpolate a field to arbitrary vertical levels column by column."""
    values = np.asarray(field, dtype=float)
    vertical = np.asarray(vertical_coordinate, dtype=float)
    if values.shape != vertical.shape:
        raise ValueError("field and vertical_coordinate must have identical shapes")
    targets = np.atleast_1d(np.asarray(levels, dtype=float))
    moved_values = np.moveaxis(values, axis, 0)
    moved_vertical = np.moveaxis(vertical, axis, 0)
    output = np.full((targets.size,) + moved_values.shape[1:], np.nan, dtype=float)
    for index in np.ndindex(moved_values.shape[1:]):
        z = moved_vertical[(slice(None),) + index]
        v = moved_values[(slice(None),) + index]
        valid = np.isfinite(z) & np.isfinite(v)
        if np.count_nonzero(valid) < 2:
            continue
        order = np.argsort(z[valid])
        output[(slice(None),) + index] = np.interp(
            targets, z[valid][order], v[valid][order], left=np.nan, right=np.nan
        )
    return output[0] if np.isscalar(levels) else output
