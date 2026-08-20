from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import xarray as xr


def open_wrf(path: str | Path, *, chunks: dict[str, int] | None = None, **kwargs: Any) -> xr.Dataset:
    """Open one WRF NetCDF file while preserving native metadata."""
    return xr.open_dataset(Path(path), chunks=chunks, **kwargs)


def open_wrf_sequence(
    paths: Iterable[str | Path],
    *,
    concat_dim: str = "Time",
    chunks: dict[str, int] | None = None,
    **kwargs: Any,
) -> xr.Dataset:
    files = [str(Path(path)) for path in paths]
    if not files:
        raise ValueError("At least one WRF file is required")
    return xr.open_mfdataset(
        files,
        combine="nested",
        concat_dim=concat_dim,
        chunks=chunks,
        **kwargs,
    )


def get_variable(
    dataset: xr.Dataset,
    name: str,
    *,
    time: int | slice | None = None,
) -> xr.DataArray:
    """Read a native WRF variable using metadata-aware dimension selection."""
    if name not in dataset:
        available = ", ".join(sorted(dataset.data_vars)[:20])
        raise KeyError(f"{name!r} is not present; available variables include: {available}")
    data = dataset[name]
    if time is not None and "Time" in data.dims:
        data = data.isel(Time=time)
    return data
