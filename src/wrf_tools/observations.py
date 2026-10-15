"""Observation normalization and WRF collocation helpers."""
from __future__ import annotations
from datetime import datetime, timezone
import numpy as np
import xarray as xr
from pathlib import Path
from .grid import nearest_grid_point

def from_columns(*, time, variables, attrs=None):
    """Create a labelled observation dataset from column-like arrays."""
    return xr.Dataset({name: ("time", np.asarray(values)) for name, values in variables.items()}, coords={"time": np.asarray(time)}, attrs=attrs or {})

def collocate_grid(field, latitude, longitude, target_latitude, target_longitude):
    """Nearest horizontal cell only; no instrument, height or footprint matching."""
    cell = nearest_grid_point(latitude, longitude, target_latitude, target_longitude)
    return field[..., cell.y, cell.x], cell

def align(model: xr.Dataset, observations: xr.Dataset, *, method="nearest", tolerance=None):
    """Reindex model to observation times; set tolerance to avoid distant matches.

    Normalize times/units/heights/averaging conventions first. Unmatched records
    become NaN. This does not quality-control either input or interpolate gaps.
    """
    if "time" not in model.coords or "time" not in observations.coords:
        raise ValueError("both datasets require a time coordinate")
    for name,dataset in (("model",model),("observations",observations)):
        if dataset.time.dims != ("time",):
            raise ValueError(f"{name}: time must be a one-dimensional coordinate")
        index=dataset.indexes["time"]
        if not len(index) or index.hasnans or not index.is_unique or not index.is_monotonic_increasing:
            raise ValueError(f"{name}: time must be nonempty, valid, unique and increasing; normalize/QC first")
    return model.reindex(time=observations.time, method=method, tolerance=tolerance), observations

def read_csv(path, *, time_column, columns=None, delimiter=","):
    """Read generic RADAR/LiDAR/SCADA/mast tabular observations."""
    table = np.atleast_1d(np.genfromtxt(Path(path), delimiter=delimiter, names=True, dtype=None, encoding="utf-8"))
    names = list(table.dtype.names or ())
    if time_column not in names:
        raise KeyError(f"time column {time_column!r} not found")
    selected = [name for name in (columns or names) if name != time_column]
    return from_columns(time=table[time_column], variables={name: table[name] for name in selected}, attrs={"source": str(Path(path))})

def read_netcdf(path, *, variables=None):
    """Open generic observation NetCDF; caller closes the returned dataset."""
    dataset = xr.open_dataset(path)
    try:
        selected=dataset[list(variables)] if variables else dataset
        if selected is not dataset:
            selected.set_close(dataset.close)
        return selected
    except Exception:
        dataset.close(); raise

def normalize_time(dataset, *, coordinate="time", timezone_offset_hours=0.0, sort=True):
    """Decode ISO timestamps, subtract a fixed UTC offset, optionally sort.

    Timezone-aware ISO strings are converted to UTC; do not combine them with
    a nonzero fixed offset. Naive timestamps use the supplied fixed offset.
    Missing times/numeric offsets without a decoded origin are rejected.
    Does not infer DST rules, remove duplicates or correct instrument clocks.
    """
    if not np.isfinite(timezone_offset_hours):
        raise ValueError("timezone_offset_hours must be finite")
    raw=np.asarray(dataset[coordinate].values)
    if raw.ndim!=1 or not raw.size or raw.dtype.kind in "iufb":
        raise ValueError("Supply nonempty one-dimensional decoded ISO/datetime timestamps, not numeric offsets")
    if raw.dtype.kind=="M":
        values=raw.astype("datetime64[ns]")
    else:
        decoded=[]
        for value in raw:
            if isinstance(value,(bytes,np.bytes_)): value=value.decode("utf-8")
            stamp=value if isinstance(value,datetime) else datetime.fromisoformat(str(value).strip().replace("Z","+00:00"))
            if stamp.tzinfo is not None:
                if timezone_offset_hours!=0:
                    raise ValueError("Timezone-aware timestamps cannot also use a fixed UTC offset")
                stamp=stamp.astimezone(timezone.utc).replace(tzinfo=None)
            decoded.append(stamp)
        values=np.asarray(decoded,dtype="datetime64[ns]")
    if np.isnat(values).any():
        raise ValueError("Observation timestamps must be valid, not NaT/missing")
    values=values-np.timedelta64(int(round(timezone_offset_hours*1e9*3600)),"ns")
    result=dataset.assign_coords({coordinate:values})
    return result.sortby(coordinate) if sort else result
