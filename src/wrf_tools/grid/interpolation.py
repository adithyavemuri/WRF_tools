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
    """Linearly interpolate co-located columns, without extrapolation or NaN bridging.

    Coordinates must be finite and strictly monotonic (increasing heights or
    decreasing pressures). Invalid/folded columns are rejected, not sorted into
    plausible profiles. A scalar level removes the vertical dimension; multiple
    levels are returned on the leading axis, with other axes in original order.
    """
    values = np.asarray(field, dtype=float)
    vertical = np.asarray(vertical_coordinate, dtype=float)
    if values.shape != vertical.shape:
        raise ValueError("field and vertical_coordinate must have identical shapes")
    targets = np.atleast_1d(np.asarray(levels, dtype=float))
    if targets.ndim != 1 or not targets.size or not np.isfinite(targets).all():
        raise ValueError("levels must contain finite scalar or one-dimensional targets")
    moved_values = np.moveaxis(values, axis, 0)
    moved_vertical = np.moveaxis(vertical, axis, 0)
    output = np.full((targets.size,) + moved_values.shape[1:], np.nan, dtype=float)
    for index in np.ndindex(moved_values.shape[1:]):
        z = moved_vertical[(slice(None),) + index]
        v = moved_values[(slice(None),) + index]
        if z.size < 2 or not np.isfinite(z).all():
            raise ValueError("Each vertical coordinate column needs at least two finite samples")
        delta = np.diff(z)
        if np.all(delta < 0):
            z, v = z[::-1], v[::-1]
        elif not np.all(delta > 0):
            raise ValueError("Vertical coordinates must be strictly monotonic, without duplicate levels")
        output[(slice(None),) + index] = np.interp(
            targets, z, np.where(np.isfinite(v), v, np.nan), left=np.nan, right=np.nan
        )
    return output[0] if np.isscalar(levels) else output

def regrid_regular(field: Any, source_x: Any, source_y: Any, target_x: Any, target_y: Any) -> np.ndarray:
    """Bilinearly interpolate a regular 2-D grid without optional dependencies."""
    values=np.asarray(field,float); sx,sy=np.asarray(source_x,float),np.asarray(source_y,float); tx,ty=np.asarray(target_x,float),np.asarray(target_y,float)
    if values.shape[-2:]!=(sy.size,sx.size): raise ValueError("field shape must match source_y/source_x")
    if min(sx.size,sy.size)<2 or not all(a.ndim==1 and np.isfinite(a).all() for a in (sx,sy,tx,ty)):
        raise ValueError("Source axes need >=2 finite coordinates; targets must be finite 1-D")
    if np.any(np.diff(sx)<=0) or np.any(np.diff(sy)<=0): raise ValueError("source coordinates must increase")
    if np.any((tx<sx[0])|(tx>sx[-1])) or np.any((ty<sy[0])|(ty>sy[-1])):
        raise ValueError("Target coordinates fall outside the source; extrapolation is not supported")
    ix=np.clip(np.searchsorted(sx,tx)-1,0,sx.size-2); iy=np.clip(np.searchsorted(sy,ty)-1,0,sy.size-2)
    wx=(tx-sx[ix])/(sx[ix+1]-sx[ix]); wy=(ty-sy[iy])/(sy[iy+1]-sy[iy])
    a=values[...,iy[:,None],ix[None,:]]; b=values[...,iy[:,None],ix[None,:]+1]; c=values[...,iy[:,None]+1,ix[None,:]]; d=values[...,iy[:,None]+1,ix[None,:]+1]
    return (1-wy[:,None])*((1-wx[None,:])*a+wx[None,:]*b)+wy[:,None]*((1-wx[None,:])*c+wx[None,:]*d)
