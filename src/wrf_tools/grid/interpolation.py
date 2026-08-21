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

def regrid_regular(field: Any, source_x: Any, source_y: Any, target_x: Any, target_y: Any) -> np.ndarray:
    """Bilinearly interpolate a regular 2-D grid without optional dependencies."""
    values=np.asarray(field,float); sx,sy=np.asarray(source_x,float),np.asarray(source_y,float); tx,ty=np.asarray(target_x,float),np.asarray(target_y,float)
    if values.shape[-2:]!=(sy.size,sx.size): raise ValueError("field shape must match source_y/source_x")
    if np.any(np.diff(sx)<=0) or np.any(np.diff(sy)<=0): raise ValueError("source coordinates must increase")
    ix=np.clip(np.searchsorted(sx,tx)-1,0,sx.size-2); iy=np.clip(np.searchsorted(sy,ty)-1,0,sy.size-2)
    wx=(tx-sx[ix])/(sx[ix+1]-sx[ix]); wy=(ty-sy[iy])/(sy[iy+1]-sy[iy])
    a=values[...,iy[:,None],ix[None,:]]; b=values[...,iy[:,None],ix[None,:]+1]; c=values[...,iy[:,None]+1,ix[None,:]]; d=values[...,iy[:,None]+1,ix[None,:]+1]
    return (1-wy[:,None])*((1-wx[None,:])*a+wx[None,:]*b)+wy[:,None]*((1-wx[None,:])*c+wx[None,:]*d)
