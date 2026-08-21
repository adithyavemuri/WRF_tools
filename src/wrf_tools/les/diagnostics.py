from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import xarray as xr

from ..diagnostics.turbulence import resolved_tke, reynolds_flux
from ..grid import destagger
from ..filters import butterworth_spatial, top_hat_coarsen


def load_velocity(
    dataset: xr.Dataset,
    *,
    names: Mapping[str, str] | None = None,
    destagger_native: bool = True,
) -> tuple[Any, Any, Any]:
    """Load velocity components using configurable WRF variable mappings."""
    mapping = {"u": "U", "v": "V", "w": "W"}
    if names:
        mapping.update(names)
    u, v, w = (dataset[mapping[key]] for key in ("u", "v", "w"))
    if destagger_native:
        staggered = [dim for dim in u.dims if dim.endswith("_stag")]
        if staggered:
            u = destagger(u, staggered[-1])
        staggered = [dim for dim in v.dims if dim.endswith("_stag")]
        if staggered:
            v = destagger(v, staggered[-1])
        staggered = [dim for dim in w.dims if dim.endswith("_stag")]
        if staggered:
            w = destagger(w, staggered[-1])
    return u, v, w


def calculate_fluxes(u: Any, v: Any, w: Any, *, axis: int = 0) -> dict[str, np.ndarray]:
    return {
        "uu": reynolds_flux(u, u, axis=axis),
        "vv": reynolds_flux(v, v, axis=axis),
        "ww": reynolds_flux(w, w, axis=axis),
        "uv": reynolds_flux(u, v, axis=axis),
        "uw": reynolds_flux(u, w, axis=axis),
        "vw": reynolds_flux(v, w, axis=axis),
    }


def calculate_total_tke(
    u: Any,
    v: Any,
    w: Any,
    *,
    subgrid_tke: Any | None = None,
    axis: int = 0,
) -> np.ndarray:
    total = resolved_tke(u, v, w, axis=axis)
    if subgrid_tke is not None:
        total = total + np.asarray(subgrid_tke)
    return total


def load_sgs_stress(dataset: xr.Dataset, *, names: Mapping[str, str] | None = None) -> dict[str, xr.DataArray]:
    """Load the six independent WRF SGS stress components."""
    mapping = {name: name for name in ("m11", "m12", "m13", "m22", "m23", "m33")}
    if names:
        mapping.update(names)
    missing = [source for source in mapping.values() if source not in dataset]
    if missing:
        raise KeyError(f"Missing SGS stress variables: {', '.join(missing)}")
    return {key: dataset[source] for key, source in mapping.items()}


def sgs_tke(stress: Mapping[str, Any]) -> np.ndarray:
    """Return SGS TKE from normal stress components."""
    return 0.5 * (np.asarray(stress["m11"]) + np.asarray(stress["m22"]) + np.asarray(stress["m33"]))


def filtered_tke(u: Any, v: Any, w: Any, *, method: str = "butterworth", spatial_axes=(-2, -1), **kwargs: Any) -> np.ndarray:
    """Calculate resolved TKE after a spatial filter/coarsening operation."""
    if method == "butterworth":
        filtered = [butterworth_spatial(value, axes=spatial_axes, **kwargs) for value in (u, v, w)]
    elif method in {"top_hat", "honnert"}:
        filtered = [top_hat_coarsen(value, axes=spatial_axes, **kwargs) for value in (u, v, w)]
    else:
        raise ValueError("method must be butterworth, top_hat, or honnert")
    return resolved_tke(*filtered, axis=spatial_axes)
