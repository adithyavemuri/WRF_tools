"""Observation normalization and WRF collocation helpers."""
from __future__ import annotations
import numpy as np
import xarray as xr
from pathlib import Path
from .grid import nearest_grid_point

def from_columns(*, time, variables, attrs=None):
    """Create a labelled observation dataset from column-like arrays."""
    return xr.Dataset({name: ("time", np.asarray(values)) for name, values in variables.items()}, coords={"time": np.asarray(time)}, attrs=attrs or {})

def collocate_grid(field, latitude, longitude, target_latitude, target_longitude):
    cell = nearest_grid_point(latitude, longitude, target_latitude, target_longitude)
    return field[..., cell.y, cell.x], cell

def align(model: xr.Dataset, observations: xr.Dataset, *, method="nearest", tolerance=None):
    if "time" not in model.coords or "time" not in observations.coords:
        raise ValueError("both datasets require a time coordinate")
    return model.reindex(time=observations.time, method=method, tolerance=tolerance), observations

def read_csv(path, *, time_column, columns=None, delimiter=","):
    """Read generic RADAR/LiDAR/SCADA/mast tabular observations."""
    table = np.genfromtxt(Path(path), delimiter=delimiter, names=True, dtype=None, encoding="utf-8")
    names = list(table.dtype.names or ())
    if time_column not in names:
        raise KeyError(f"time column {time_column!r} not found")
    selected = [name for name in (columns or names) if name != time_column]
    return from_columns(time=table[time_column], variables={name: table[name] for name in selected}, attrs={"source": str(Path(path))})

def read_netcdf(path, *, variables=None):
    dataset = xr.open_dataset(path)
    return dataset[list(variables)] if variables else dataset

def normalize_time(dataset, *, coordinate="time", timezone_offset_hours=0.0, sort=True):
    result=dataset.copy(); values=np.asarray(result[coordinate].values,dtype="datetime64[ns]")-np.timedelta64(int(round(timezone_offset_hours*1e9*3600)),"ns"); result=result.assign_coords({coordinate:values})
    return result.sortby(coordinate) if sort else result
