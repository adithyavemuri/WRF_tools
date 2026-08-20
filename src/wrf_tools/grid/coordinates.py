from __future__ import annotations

from typing import Any

import numpy as np

from ..types import GeoBounds, GridPoint


def nearest_grid_point(
    latitude: Any,
    longitude: Any,
    target_latitude: float,
    target_longitude: float,
) -> GridPoint:
    """Return the nearest horizontal grid cell using great-circle geometry."""
    lat = np.asarray(latitude, dtype=float).squeeze()
    lon = np.asarray(longitude, dtype=float).squeeze()
    if lat.shape != lon.shape or lat.ndim != 2:
        raise ValueError("latitude and longitude must be equally shaped 2-D arrays")
    lat1 = np.deg2rad(lat)
    lat2 = np.deg2rad(target_latitude)
    dlat = lat1 - lat2
    dlon = np.deg2rad(lon - target_longitude)
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    y, x = np.unravel_index(int(np.nanargmin(a)), a.shape)
    return GridPoint(x=x, y=y, latitude=float(lat[y, x]), longitude=float(lon[y, x]))


def subset_by_bounds(
    data: Any,
    latitude: Any,
    longitude: Any,
    bounds: GeoBounds,
    *,
    padding: int = 0,
) -> tuple[Any, tuple[slice, slice]]:
    """Take the smallest rectangular grid subset containing geographic bounds."""
    lat = np.asarray(latitude).squeeze()
    lon = np.asarray(longitude).squeeze()
    mask = (
        (lat >= bounds.south)
        & (lat <= bounds.north)
        & (lon >= bounds.west)
        & (lon <= bounds.east)
    )
    if not np.any(mask):
        raise ValueError("Bounds do not intersect the supplied grid")
    ys, xs = np.where(mask)
    y_slice = slice(max(int(ys.min()) - padding, 0), min(int(ys.max()) + padding + 1, lat.shape[0]))
    x_slice = slice(max(int(xs.min()) - padding, 0), min(int(xs.max()) + padding + 1, lat.shape[1]))
    return data[..., y_slice, x_slice], (y_slice, x_slice)
