from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
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
    """Open chronological outputs from one compatible WRF domain.

    Mixed domains and incompatible grids are rejected. Dask is not required.
    """
    files = [str(Path(path)) for path in paths]
    if not files:
        raise ValueError("At least one WRF file is required")
    datasets = [xr.open_dataset(path, chunks=chunks, **kwargs) for path in files]
    try:
        reference = datasets[0]
        grid_attrs = ("GRID_ID", "DX", "DY", "MAP_PROJ", "CEN_LAT", "CEN_LON")
        horizontal = ("west_east", "south_north", "west_east_stag", "south_north_stag")
        for dataset, path in zip(datasets[1:], files[1:]):
            differing = [name for name in grid_attrs if reference.attrs.get(name) != dataset.attrs.get(name)]
            differing += [name for name in horizontal if reference.sizes.get(name) != dataset.sizes.get(name)]
            if differing:
                raise ValueError(f"Incompatible WRF domain/grid in {path}: {', '.join(sorted(set(differing)))}")
        combined = xr.concat(datasets, dim=concat_dim, data_vars="minimal", coords="minimal", compat="override")
        if "Times" in combined:
            raw = combined["Times"].values
            if raw.ndim == 2:
                text = [b"".join(row).decode().strip().replace("_", "T", 1) for row in raw]
                stamps = np.array(text, dtype="datetime64[s]")
                if np.any(np.diff(stamps.astype("int64")) <= 0):
                    raise ValueError("WRF file sequence contains overlapping or non-monotonic times")
        combined.set_close(lambda: [dataset.close() for dataset in datasets])
        return combined
    except Exception:
        for dataset in datasets:
            dataset.close()
        raise


def get_variable(
    dataset: xr.Dataset,
    name: str,
    *,
    time: int | slice | None = None,
    destagger_native: bool = False,
) -> xr.DataArray:
    """Read a WRF variable with optional conversion to the mass grid.

    By default the native WRF grid is preserved. Set ``destagger_native=True``
    to average every dimension ending in ``_stag`` onto its corresponding mass
    dimension. The result records the operation in
    ``wrf_tools_grid_processing``.
    """
    if name not in dataset:
        available = ", ".join(sorted(dataset.data_vars)[:20])
        raise KeyError(f"{name!r} is not present; available variables include: {available}")
    data = dataset[name]
    if time is not None and "Time" in data.dims:
        data = data.isel(Time=time)
    if destagger_native:
        from ..grid import destagger_wrf
        data = destagger_wrf(data)
    else:
        data = data.copy(deep=False)
        data.attrs = dict(data.attrs)
        data.attrs["wrf_tools_grid_processing"] = "native WRF grid preserved"
    return data
