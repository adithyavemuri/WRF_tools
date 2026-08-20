from __future__ import annotations

from typing import Any

import numpy as np


def destagger(
    data: Any,
    dimension: str | int,
    *,
    target_dimension: str | None = None,
) -> Any:
    """Average adjacent points along any staggered dimension.

    NumPy arrays use an integer axis. Xarray DataArrays may use either an axis
    number or a dimension name and retain coordinates and metadata. WRF names
    ending in ``_stag`` are automatically renamed to the corresponding mass
    dimension; an explicit ``target_dimension`` may be supplied otherwise.
    """
    if hasattr(data, "dims") and isinstance(dimension, str):
        axis = data.get_axis_num(dimension)
    elif isinstance(dimension, int):
        axis = dimension
    else:
        raise TypeError("dimension must be an axis number or xarray dimension name")
    if data.shape[axis] < 2:
        raise ValueError("Cannot destagger a dimension with fewer than two points")
    first = [slice(None)] * data.ndim
    second = [slice(None)] * data.ndim
    first[axis] = slice(0, -1)
    second[axis] = slice(1, None)
    if hasattr(data, "isel"):
        dim_name = data.dims[axis]
        left = data.isel({dim_name: slice(0, -1)}).copy()
        right = np.asarray(data.isel({dim_name: slice(1, None)}))
        left.data = (np.asarray(left) + right) / 2.0
        mass_dimension = target_dimension
        if mass_dimension is None and dim_name.endswith("_stag"):
            mass_dimension = dim_name.removesuffix("_stag")
        if mass_dimension and mass_dimension != dim_name:
            left = left.rename({dim_name: mass_dimension})
        return left
    array = np.asarray(data)
    return (array[tuple(first)] + array[tuple(second)]) / 2.0
