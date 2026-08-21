"""Readers for WRF station time-series output families."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import xarray as xr

SURFACE_COLUMNS = ("id", "ts_hour", "id_tsloc", "ix", "iy", "t", "q", "u", "v", "psfc", "glw", "gsw", "hfx", "lh", "tsk", "tslb", "rainc", "rainnc", "clw")

def read_station_header(path):
    line = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()[0]
    return {"station_name": line[0:25].strip(), "grid_id": (int(line[26:29]), int(line[29:32])), "station_id": line[33:38].strip(), "station_latitude": float(line[39:46]), "station_longitude": float(line[47:55]), "grid_indices": (int(line[58:62]), int(line[63:67])), "grid_latitude": float(line[70:77]), "grid_longitude": float(line[78:86]), "grid_elevation": float(line[88:94]), "elevation_units": line[95:].strip()}

def read_station_surface(path):
    source = Path(path)
    values = np.genfromtxt(source, skip_header=1)
    values = np.atleast_2d(values)
    if values.shape[1] < len(SURFACE_COLUMNS):
        raise ValueError(f"Expected {len(SURFACE_COLUMNS)} station columns, found {values.shape[1]}")
    attrs = read_station_header(source)
    return xr.Dataset({name: ("time", values[:, index]) for index, name in enumerate(SURFACE_COLUMNS) if name != "ts_hour"}, coords={"time": values[:, 1]}, attrs=attrs)

def read_station_profile(path):
    values = np.genfromtxt(path)
    values = np.atleast_2d(values)
    return xr.DataArray(values[:, 1:], dims=("time", "level"), coords={"time": values[:, 0]}, name=Path(path).suffix.lstrip(".").lower())

def read_station_family(surface_path, profile_codes=("UU", "VV", "WW", "PH", "TH", "QV", "PR")):
    source = Path(surface_path)
    dataset = read_station_surface(source)
    prefix = str(source)[:-2] if source.suffix.upper() == ".TS" else str(source) + "."
    for code in profile_codes:
        candidate = Path(prefix + code)
        if candidate.exists():
            dataset[code.lower()] = read_station_profile(candidate)
    return dataset
