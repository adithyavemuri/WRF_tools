#!/usr/bin/env python3
"""Editable example: compare site wind from named simulations; plots only.

Try synthetic data first (does not run WRF):
    .venv/bin/python examples/compare_simulations.py --demo

Compare real runs:
    .venv/bin/python examples/compare_simulations.py \
      --case Baseline=/path/to/control/wrf --case MYNN=/path/to/mynn/wrf \
      --domain d02 --latitude 52 --longitude 5 --baseline Baseline

Each run may have its own grid. This example selects the nearest cell separately,
prints its actual location, matches real times, then interpolates site profiles
to common physical heights. It never subtracts different horizontal grids.

For editable horizontal, selected-area, vertical and time means, see the separate
average_wrf_fields.py example. Its reduced profiles/time series can be supplied
to these same comparison plotting functions; this file deliberately uses sites.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import xarray as xr

from wrf_tools.averaging import to_height
from wrf_tools.comparison import align_cases, plot_profiles, plot_timeseries
from wrf_tools.grid import nearest_grid_point
from wrf_tools.io import discover_wrfout, open_wrf_sequence
from wrf_tools.visualization import GRAVITY, history_times


# STEP 1: Choose the common profile heights in metres AGL.
# No extrapolation: heights below the lowest mass level remain missing.
HEIGHTS_AGL = np.arange(50., 2001., 50.)
# The example compares profiles at the LAST COMMON timestamp. Change that here.
PROFILE_TIME_INDEX = -1


def read_site(run_directory, domain, latitude, longitude):
    """STEP 2: Select what to compare. Edit this function for your research.

    Here: 10 m speed time series + 3-D mass-grid wind-speed site profiles.
    For T2, PBLH, or TKE, replace the selected field and retain its units.
    Destagger U/V before computing speed; never use a single staggered component
    as a mass-grid speed. We read site columns, not the full 3-D domain.
    """
    with open_wrf_sequence(discover_wrfout(run_directory, domain=domain)) as ds:
        cell = nearest_grid_point(ds.XLAT.isel(Time=0), ds.XLONG.isel(Time=0), latitude, longitude)
        print(f"  {run_directory}: nearest cell {cell.latitude:.4f}, {cell.longitude:.4f}; x={cell.x}, y={cell.y}")
        position = {"south_north": cell.y, "west_east": cell.x}
        times = np.array(history_times(ds), dtype="datetime64[s]")
        surface = np.hypot(ds.U10.isel(position).values, ds.V10.isel(position).values)
        series = xr.DataArray(surface, dims="Time", coords={"Time": times}, attrs={"units": "m s-1"})
        u = ds.U.isel(south_north=cell.y, west_east_stag=slice(cell.x, cell.x+2)).values.mean(axis=-1)
        v = ds.V.isel(south_north_stag=slice(cell.y, cell.y+2), west_east=cell.x).values.mean(axis=-1)
        z_stag = (ds.PH.isel(position).values + ds.PHB.isel(position).values) / GRAVITY
        z = .5 * (z_stag[:, :-1] + z_stag[:, 1:]) - ds.HGT.isel(position).values[:, None]
        speed = xr.DataArray(np.hypot(u, v), dims=("Time", "bottom_top"),
                             coords={"Time": times}, attrs={"units": "m s-1"})
        height = xr.DataArray(z, dims=speed.dims, coords=speed.coords)
        profiles = to_height(speed, height, HEIGHTS_AGL, reference="AGL").transpose("Time", "height")
        return series, profiles


def demo_cases():
    """Known artificial signals: useful for checking plots, not physics evidence."""
    times = np.arange(np.datetime64("2025-01-01T00"), np.datetime64("2025-01-01T07"), np.timedelta64(1, "h"))
    series, profiles = {}, {}
    for name, offset in (("Synthetic baseline", 0.), ("Synthetic +1 m/s", 1.)):
        series[name] = xr.DataArray(5 + np.sin(np.arange(7)) + offset,
            dims="Time", coords={"Time": times}, attrs={"units": "m s-1"})
        profiles[name] = xr.DataArray(np.broadcast_to(4 + HEIGHTS_AGL[None, :] * .004 + offset, (7, len(HEIGHTS_AGL))),
            dims=("Time", "height"), coords={"Time": times, "height": HEIGHTS_AGL}, attrs={"units": "m s-1"})
        profiles[name].height.attrs = {"units": "m", "reference": "AGL"}
    return series, profiles


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", action="append", default=[], metavar="NAME=WRF_DIRECTORY")
    parser.add_argument("--demo", action="store_true", help="use explicitly synthetic data")
    parser.add_argument("--domain", default="d02")
    parser.add_argument("--latitude", type=float, default=52.)
    parser.add_argument("--longitude", type=float, default=5.)
    parser.add_argument("--alignment", choices=("exact", "intersection"), default="exact")
    parser.add_argument("--baseline", help="also save each case minus this named baseline")
    parser.add_argument("--output", type=Path, default=Path("example_results/comparison"))
    args = parser.parse_args()
    if args.demo and args.case:
        parser.error("choose --demo OR real --case paths")
    if args.demo:
        series, profiles = demo_cases()
        baseline = args.baseline or "Synthetic baseline"
        prefix = "SYNTHETIC DEMONSTRATION | "
    else:
        paths = {}
        for item in args.case:
            name, separator, path = item.partition("=")
            if not separator or not name.strip() or not path or name in paths:
                parser.error("each --case must have a unique nonempty NAME=WRF_DIRECTORY")
            paths[name] = Path(path).expanduser()
        if len(paths) < 2:
            parser.error("provide at least two --case values, or use --demo")
        series, profiles = {}, {}
        for name, path in paths.items():
            print(name)
            series[name], profiles[name] = read_site(path, args.domain, args.latitude, args.longitude)
        baseline, prefix = args.baseline, ""

    # STEP 3: Match timestamps explicitly. Intersection never interpolates time.
    series = align_cases(series, coordinate="Time", alignment=args.alignment)
    stamps = next(iter(series.values())).Time
    print(f"Comparing {len(series)} cases at {len(stamps)} matched timestamps")
    selected_time = stamps.values[PROFILE_TIME_INDEX]
    profiles = {name: data.sel(Time=selected_time) for name, data in profiles.items()}
    print(f"Profile time: {selected_time} UTC")

    # STEP 4: Save figures; edit axes freely or embed these calls in your notebook.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    args.output.mkdir(parents=True, exist_ok=True)
    for suffix, reference in (("overlay", None), ("difference", baseline)):
        if suffix == "difference" and reference is None:
            continue
        for kind, function, cases, title in (
            ("timeseries", plot_timeseries, series, "10 m wind at nearest site cells"),
            ("profiles", plot_profiles, profiles, f"Site wind profiles at {selected_time} UTC"),
        ):
            fig, ax = function(cases, baseline=reference, title=prefix+title, value_label="Wind speed")
            for extension in ("png", "svg"):
                path = args.output / f"{kind}_{suffix}.{extension}"
                fig.savefig(path, dpi=180)
                print(f"Saved {path}")
            plt.close(fig)


if __name__ == "__main__":
    main()
