"""Small plotting helpers for already-selected, named simulation results.

No PDF, automatic regridding, scientific interpretation or unit conversion.
"""
from __future__ import annotations

from collections.abc import Mapping
import numpy as np
import xarray as xr

from .plotting import _plt


def align_cases(cases, *, coordinate, alignment="exact"):
    """Match labelled 1-D results at exact or explicitly intersected samples.

    ``exact`` rejects mismatched indexes. ``intersection`` retains only common
    samples without interpolation. Units must be present and identical. This
    checks numerical coordinates, not experimental comparability or geography.
    """
    if not isinstance(cases, Mapping) or len(cases) < 2:
        raise ValueError("Provide at least two named simulation results")
    if alignment not in {"exact", "intersection"}:
        raise ValueError("alignment must be exact or intersection")
    units = []
    references = []
    for label, data in cases.items():
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Each simulation needs a nonempty name")
        if not isinstance(data, xr.DataArray) or data.dims != (coordinate,) or coordinate not in data.coords:
            raise ValueError(f"{label}: select a 1-D DataArray with explicit {coordinate} coordinates")
        index = data.get_index(coordinate)
        if not len(index) or index.hasnans or not index.is_unique or not index.is_monotonic_increasing:
            raise ValueError(f"{label}: coordinates must be nonempty, valid, unique and increasing")
        units.append(data.attrs.get("units"))
        references.append(data[coordinate].attrs.get("reference"))
    if any(not unit for unit in units) or len(set(units)) != 1:
        raise ValueError("Provide identical explicit units; convert fields before comparison")
    if len(set(references)) != 1:
        raise ValueError("Coordinate references differ; do not mix AGL and MSL heights")
    try:
        arrays = xr.align(*cases.values(), join="exact" if alignment == "exact" else "inner", copy=False)
    except ValueError as exc:
        raise ValueError("Samples differ: select common samples or explicitly choose alignment='intersection'") from exc
    if not arrays[0].sizes[coordinate]:
        raise ValueError("No common samples remain")
    return dict(zip(cases, arrays))


def _plot(cases, coordinate, *, alignment, baseline, ax, title, value_label, profiles):
    cases = align_cases(cases, coordinate=coordinate, alignment=alignment)
    if baseline is not None:
        if baseline not in cases:
            raise ValueError(f"Unknown baseline {baseline!r}")
        reference = cases[baseline]
        cases = {name: data - reference for name, data in cases.items() if name != baseline}
        # Subtraction may discard attrs; the displayed unit was validated first.
        units = reference.attrs["units"]
        value_label = f"Difference from {baseline}: {value_label}"
    else:
        units = next(iter(cases.values())).attrs["units"]
    plt = _plt()
    ax = ax if ax is not None else plt.subplots(figsize=(8, 5), layout="constrained")[1]
    styles = ("-", "--", "-.", ":")
    for index, (label, data) in enumerate(cases.items()):
        x, y = (data.values, data[coordinate].values) if profiles else (data[coordinate].values, data.values)
        ax.plot(x, y, label=label, linewidth=1.8, linestyle=styles[index % len(styles)])
    axis_label = f"{value_label} ({units})"
    if profiles:
        height_reference = next(iter(cases.values()))[coordinate].attrs.get("reference", "")
        ax.set(xlabel=axis_label, ylabel=f"Height {height_reference} (m)")
        if baseline is not None:
            ax.axvline(0, color="0.5", linewidth=.8)
    else:
        import matplotlib.dates as mdates
        locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        ax.set(xlabel="Time (UTC)", ylabel=axis_label)
        if baseline is not None:
            ax.axhline(0, color="0.5", linewidth=.8)
    ax.set_title(title or ("Simulation profile comparison" if profiles else "Simulation time-series comparison"))
    ax.grid(alpha=.25)
    ax.legend(frameon=False)
    return ax.figure, ax


def plot_timeseries(cases, *, coordinate="Time", alignment="exact", baseline=None,
                    ax=None, title=None, value_label="Value"):
    """Overlay named time series, or plot case-minus-baseline differences.

    Inputs are 1-D DataArrays with datetime coordinates and explicit units.
    Return editable Matplotlib figure/axes; saving is the caller's choice.
    """
    for label, data in cases.items():
        if coordinate in data.coords and not np.issubdtype(data[coordinate].dtype, np.datetime64):
            raise ValueError(f"{label}: supply decoded datetime coordinates, not time indices")
    return _plot(cases, coordinate, alignment=alignment, baseline=baseline, ax=ax,
                 title=title, value_label=value_label, profiles=False)


def plot_profiles(cases, *, coordinate="height", alignment="exact", baseline=None,
                  ax=None, title=None, value_label="Value"):
    """Overlay profiles on explicitly matched physical heights in metres.

    Coordinate attrs must contain units='m' and reference='AGL' or 'MSL'. Use
    averaging.to_height first when native vertical grids differ. No automatic
    interpolation, eta-level equivalence or vertical averaging is assumed.
    """
    for label, data in cases.items():
        if coordinate in data.coords and (data[coordinate].attrs.get("units") != "m"
                or data[coordinate].attrs.get("reference") not in {"AGL", "MSL"}):
            raise ValueError(f"{label}: height coordinates need units='m' and reference='AGL' or 'MSL'")
    return _plot(cases, coordinate, alignment=alignment, baseline=baseline, ax=ax,
                 title=title, value_label=value_label, profiles=True)
