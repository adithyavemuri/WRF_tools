"""Composable extraction from labelled WRF datasets."""
from __future__ import annotations
from typing import Mapping
import numpy as np
import xarray as xr
from .grid import destagger_wrf, interpolate_to_levels, nearest_grid_point


def _prepare_grid(data: xr.DataArray, destagger_native: bool) -> xr.DataArray:
    if destagger_native:
        return destagger_wrf(data)
    result = data.copy(deep=False)
    result.attrs = dict(result.attrs)
    result.attrs["wrf_tools_grid_processing"] = "native WRF grid preserved"
    return result

def point(dataset: xr.Dataset, latitude: float, longitude: float, *, variables=None, time=None, lat_name="XLAT", lon_name="XLONG", destagger_native=False) -> xr.Dataset:
    """Extract the nearest geographic cell, optionally on the WRF mass grid."""
    lat = dataset[lat_name].isel(Time=0) if "Time" in dataset[lat_name].dims else dataset[lat_name]
    lon = dataset[lon_name].isel(Time=0) if "Time" in dataset[lon_name].dims else dataset[lon_name]
    cell = nearest_grid_point(lat, lon, latitude, longitude)
    result = dataset[list(variables)] if variables else dataset
    if destagger_native:
        result = xr.Dataset({name: destagger_wrf(data) for name, data in result.data_vars.items()}, attrs=result.attrs)
    else:
        result = result.copy(deep=False)
        for name in result.data_vars:
            result[name].attrs = dict(result[name].attrs)
            result[name].attrs["wrf_tools_grid_processing"] = "native WRF grid preserved"
    indexers = {d: cell.y for d in result.dims if d in {"south_north", "south_north_stag"}}
    indexers.update({d: cell.x for d in result.dims if d in {"west_east", "west_east_stag"}})
    if time is not None and "Time" in result.dims:
        indexers["Time"] = time
    return result.isel(indexers)

def vertical_profile(dataset: xr.Dataset, variable: str, *, x: int, y: int, time=0, destagger_native=False) -> xr.DataArray:
    """Extract a profile; set ``destagger_native=True`` for the mass grid."""
    data = _prepare_grid(dataset[variable], destagger_native)
    indexers = {d: y for d in data.dims if d.startswith("south_north")}
    indexers.update({d: x for d in data.dims if d.startswith("west_east")})
    if "Time" in data.dims:
        indexers["Time"] = time
    return data.isel(indexers)

def to_levels(data, coordinate, levels, *, axis=-1):
    return interpolate_to_levels(data, coordinate, levels, axis=axis)

def variables(dataset: xr.Dataset, mapping: Mapping[str, str]) -> xr.Dataset:
    missing = [source for source in mapping.values() if source not in dataset]
    if missing:
        raise KeyError(f"Missing WRF variables: {', '.join(missing)}")
    return xr.Dataset({target: dataset[source] for target, source in mapping.items()})

def horizontal_plane(dataset: xr.Dataset, variable: str, *, level=None, time=0, destagger_native=False) -> xr.DataArray:
    """Extract a plane; set ``destagger_native=True`` for the mass grid."""
    data=_prepare_grid(dataset[variable], destagger_native); indexers={}
    if "Time" in data.dims: indexers["Time"]=time
    vertical=next((d for d in data.dims if d in {"bottom_top","bottom_top_stag"}),None)
    if level is not None and vertical: indexers[vertical]=level
    return data.isel(indexers)

def transect(data, start, end, *, points=100):
    """Sample a 2-D array along an index-space transect using bilinear interpolation."""
    values=np.asarray(data,float); y=np.linspace(start[0],end[0],points); x=np.linspace(start[1],end[1],points)
    y0=np.floor(y).astype(int); x0=np.floor(x).astype(int); y1=np.clip(y0+1,0,values.shape[-2]-1); x1=np.clip(x0+1,0,values.shape[-1]-1); y0=np.clip(y0,0,values.shape[-2]-1); x0=np.clip(x0,0,values.shape[-1]-1)
    wy=y-y0; wx=x-x0
    sampled=(1-wy)*(1-wx)*values[...,y0,x0]+(1-wy)*wx*values[...,y0,x1]+wy*(1-wx)*values[...,y1,x0]+wy*wx*values[...,y1,x1]
    return sampled,y,x
