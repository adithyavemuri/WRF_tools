"""Explicit, composable reductions for researcher-selected WRF fields.

These helpers do not infer comparable domains or silently interpolate grids.
"""
from __future__ import annotations

import numpy as np
import xarray as xr


def mean(data, dims, *, weighting, weights=None, mask=None):
    """Mean over named dimensions, retaining other dimensions and units.

    ``weighting`` is explicitly ``uniform``, ``area`` or ``layer``. The latter
    two require supplied cell areas or layer thicknesses; no mass weighting is
    inferred. A boolean ``mask`` selects an area/layer before reduction.
    Non-finite data are excluded from both numerator and denominator. Empty
    selections return NaN. Inputs must be co-located with exactly matching
    dimension indexes; weights cannot introduce dimensions or negative values.
    """
    dims = [dims] if isinstance(dims, str) else list(dims)
    if not dims or not set(dims) <= set(data.dims):
        raise ValueError("Select existing dimensions to average")
    if weighting not in {"uniform", "area", "layer"}:
        raise ValueError("weighting must be uniform, area or layer")
    if weighting == "uniform":
        if weights is not None:
            raise ValueError("Do not supply weights for uniform averaging")
        weights = xr.DataArray(1.0)
    elif weights is None:
        raise ValueError(f"{weighting} averaging requires explicit weights")
    for name, value in (("weights", weights), ("mask", mask)):
        if value is None:
            continue
        if not isinstance(value, xr.DataArray) or not set(value.dims) <= set(data.dims):
            raise ValueError(f"{name} must be a DataArray on a subset of the data dimensions")
        xr.align(data, value, join="exact", copy=False)
    if not np.isfinite(weights).all() or bool((weights < 0).any()):
        raise ValueError("Weights must be finite and nonnegative")
    valid = np.isfinite(data)
    if mask is not None:
        if mask.dtype.kind != "b":
            raise ValueError("mask must contain boolean selections")
        valid = valid & mask
    denominator = weights.where(valid, 0).sum(dims)
    result = (data.where(valid, 0) * weights).sum(dims) / denominator.where(denominator > 0)
    result.name = data.name
    result.attrs = dict(data.attrs)
    result.attrs["wrf_tools_averaging"] = f"{weighting} mean over {','.join(dims)}; masked={mask is not None}"
    return result


def wrf_cell_area(dataset):
    """Mass-grid area DX*DY/MAPFAC_M**2 (m2) for standard conformal WRF grids.

    Supply independently calculated cell areas for geographic/rotated grids.
    No silent equal-area fallback is made when map factors are unavailable.
    """
    if int(dataset.attrs.get("MAP_PROJ", 0)) not in {1, 2, 3} or "MAPFAC_M" not in dataset:
        raise ValueError("Cell-area helper needs Lambert/polar/Mercator MAPFAC_M; otherwise supply cell areas")
    dx, dy = float(dataset.attrs["DX"]), float(dataset.attrs["DY"])
    factor = dataset.MAPFAC_M
    if not np.isfinite([dx, dy]).all() or min(dx, dy) <= 0 or not np.isfinite(factor).all() or bool((factor <= 0).any()):
        raise ValueError("Grid spacing and map factors must be positive and finite")
    result = dx * dy / factor**2
    result.attrs = {"units": "m2", "long_name": "WRF mass-grid cell area"}
    return result


def layer_thickness(interfaces, lower, upper, *, dim="bottom_top_stag", target_dim="bottom_top"):
    """Thickness of each layer overlapping [lower, upper], in metres.

    Supply physical interface heights in the SAME AGL/MSL reference as the
    bounds. Partial boundary layers are clipped, not counted in full. Values
    averaged with these weights are treated as layer representative; this is
    not interpolation of the field. Columns must increase strictly. Eager.
    """
    if not np.isfinite([lower, upper]).all() or upper <= lower:
        raise ValueError("Layer bounds must be finite and increasing")
    if dim not in interfaces.dims or interfaces.sizes[dim] < 2 or target_dim in interfaces.dims:
        raise ValueError("Supply interface heights with a staggered vertical dimension")
    axis = interfaces.get_axis_num(dim)
    heights = np.asarray(interfaces, float)
    if not np.isfinite(heights).all() or np.any(np.diff(heights, axis=axis) <= 0):
        raise ValueError("Interface heights must be finite and strictly increasing")
    thickness = np.diff(np.clip(heights, lower, upper), axis=axis)
    dims = [target_dim if name == dim else name for name in interfaces.dims]
    coords = {name: value for name, value in interfaces.coords.items() if dim not in value.dims}
    result = xr.DataArray(thickness, dims=dims, coords=coords, name="layer_thickness")
    result.attrs = {"units": "m", "layer_lower_m": float(lower), "layer_upper_m": float(upper),
                    "method": "overlap with supplied physical interfaces"}
    return result


def to_height(data, heights, levels, *, reference, dim="bottom_top"):
    """Interpolate each column to common physical heights before averaging.

    ``heights`` must be co-located metres in the explicitly selected AGL/MSL
    reference. No extrapolation or bridging of missing values. Every column
    must have finite strictly increasing heights. Does not guess height units
    or destagger variables. Returns a labelled ``height`` dimension.
    """
    if reference not in {"AGL", "MSL"}:
        raise ValueError("reference must be AGL or MSL")
    levels = np.asarray(levels, float)
    if levels.ndim != 1 or not levels.size or not np.isfinite(levels).all() or np.any(np.diff(levels) <= 0):
        raise ValueError("Requested heights must be finite and strictly increasing")
    if set(data.dims) != set(heights.dims) or dim not in data.dims or "height" in data.dims:
        raise ValueError("Data and heights need identical co-located dimensions including the vertical dimension")
    data, heights = xr.align(data, heights, join="exact", copy=False)

    def interpolate(values, z):
        if not np.isfinite(z).all() or np.any(np.diff(z) <= 0):
            raise ValueError("Column heights must be finite and strictly increasing")
        return np.interp(levels, z, np.where(np.isfinite(values), values, np.nan), left=np.nan, right=np.nan)

    result = xr.apply_ufunc(interpolate, data, heights,
        input_core_dims=[[dim], [dim]], output_core_dims=[["height"]],
        vectorize=True, dask="forbidden", output_dtypes=[float], keep_attrs=True)
    result = result.assign_coords(height=levels)
    result.height.attrs = {"units": "m", "reference": reference, "positive": "up"}
    result.attrs["wrf_tools_vertical_processing"] = f"Linear interpolation to {reference} heights; no extrapolation"
    return result
