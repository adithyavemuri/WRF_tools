from __future__ import annotations

import xarray as xr

from ..exceptions import DataValidationError


def validate_wrf_dataset(dataset: xr.Dataset) -> None:
    """Validate the minimum coordinate information expected from WRF output."""
    dimensions = set(dataset.dims)
    if not ({"south_north", "west_east"} <= dimensions):
        raise DataValidationError("Dataset lacks WRF horizontal dimensions")
    if not any(name in dataset for name in ("XLAT", "XLAT_M")):
        raise DataValidationError("Dataset lacks a WRF latitude variable")
    if not any(name in dataset for name in ("XLONG", "XLONG_M")):
        raise DataValidationError("Dataset lacks a WRF longitude variable")
