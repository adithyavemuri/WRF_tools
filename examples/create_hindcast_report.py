#!/usr/bin/env python3
"""Beginner example: inspect WRF variables and create a hindcast report.

What this example teaches:

1. Point WRF_tools at a folder containing wrfout_d??_* files.
2. Print the variables that are actually available in those files.
3. Generate the standard compact multi-domain PDF report.
4. Optionally make one additional map from a variable you choose.

Start with:

    .venv/bin/python examples/create_hindcast_report.py /path/to/wrf/run \
        --domain d02 --list-variables

Then add a custom map, for example:

    .venv/bin/python examples/create_hindcast_report.py /path/to/wrf/run \
        --domain d02 --plot-variable PBLH

The standard PDF uses a scientifically reviewed default set of plots. The
optional custom map is saved beside it as a separate PNG so experimentation
does not silently change the standard report.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from wrf_tools.hindcast import create_hindcast_report
from wrf_tools.io import discover_wrfout, open_wrf_sequence
from wrf_tools.maps import add_cached_features


# =============================================================================
# STEP 1: EDIT THESE DEFAULTS IF YOU PREFER RUNNING FROM AN IDE
# =============================================================================
# Command-line arguments always override these settings.
RUN_DIRECTORY: Path | None = None
OUTPUT_DIRECTORY = Path("example_results/hindcast_report")
PRIMARY_DOMAIN = "d01"

# Leave both as None to use the geographical centre of each domain.
TARGET_LATITUDE: float | None = None
TARGET_LONGITUDE: float | None = None

# Examples: "PBLH", "HFX", "LH", "PSFC", "T2", "RAINC", or "RAINNC".
# Leave as None when you only want the standard report.
EXTRA_MAP_VARIABLE: str | None = None
EXTRA_MAP_TIME_INDEX = -1
EXTRA_MAP_LEVEL_INDEX = 0


def parse_arguments() -> argparse.Namespace:
    """Read friendly command-line options while retaining editable defaults."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", nargs="?", type=Path,
                        help="folder containing wrfout_d01_*, wrfout_d02_*, etc.")
    parser.add_argument("--output", type=Path, default=OUTPUT_DIRECTORY,
                        help=f"output folder (default: {OUTPUT_DIRECTORY})")
    parser.add_argument("--domain", default=PRIMARY_DOMAIN,
                        help=f"domain used for the custom map (default: {PRIMARY_DOMAIN})")
    parser.add_argument("--latitude", type=float, default=TARGET_LATITUDE)
    parser.add_argument("--longitude", type=float, default=TARGET_LONGITUDE)
    parser.add_argument("--list-variables", action="store_true",
                        help="print every available variable and its dimensions")
    parser.add_argument("--plot-variable", default=EXTRA_MAP_VARIABLE,
                        help="also save a map of this variable, for example PBLH")
    parser.add_argument("--time-index", type=int, default=EXTRA_MAP_TIME_INDEX,
                        help="time index for the custom map; -1 means final time")
    parser.add_argument("--level-index", type=int, default=EXTRA_MAP_LEVEL_INDEX,
                        help="vertical/model/soil level for a 3-D variable")
    arguments = parser.parse_args()

    arguments.run_directory = arguments.run_directory or RUN_DIRECTORY
    if arguments.run_directory is None:
        parser.error("provide RUN_DIRECTORY or edit it in STEP 1")
    if (arguments.latitude is None) != (arguments.longitude is None):
        parser.error("--latitude and --longitude must be supplied together")
    return arguments


def describe_variables(dataset) -> None:
    """Print names and dimensions so users do not have to guess variable names."""
    print("\nAvailable WRF variables:")
    for name in sorted(dataset.data_vars):
        dimensions = ", ".join(f"{dim}={dataset[name].sizes[dim]}" for dim in dataset[name].dims)
        units = dataset[name].attrs.get("units", "units not recorded")
        print(f"  {name:20s} [{dimensions}]  {units}")


def select_horizontal_field(dataset, variable: str, time_index: int, level_index: int):
    """Select one ordinary mass-grid horizontal slice for a custom map."""
    if variable not in dataset:
        available = ", ".join(sorted(dataset.data_vars))
        raise ValueError(f"{variable!r} is unavailable. Available variables: {available}")

    field = dataset[variable]
    if "Time" in field.dims:
        field = field.isel(Time=time_index)

    # A WRF 3-D field needs one model or soil level before it becomes a map.
    vertical_dimensions = ("bottom_top", "bottom_top_stag", "soil_layers_stag")
    for dimension in vertical_dimensions:
        if dimension in field.dims:
            field = field.isel({dimension: level_index})

    field = field.squeeze(drop=True)
    expected = {"south_north", "west_east"}
    if set(field.dims) != expected:
        raise ValueError(
            f"{variable} has remaining dimensions {field.dims}. This beginner "
            "example plots ordinary mass-grid fields only. Staggered U/V/W fields "
            "must first be destaggered with the WRF_tools grid API."
        )
    return field.transpose("south_north", "west_east")


def save_custom_map(dataset, variable: str, output: Path, time_index: int, level_index: int) -> Path:
    """Create one map selected by the user without modifying the standard PDF."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs

    field = select_horizontal_field(dataset, variable, time_index, level_index)
    latitude = np.asarray(dataset.XLAT.isel(Time=0))
    longitude = np.asarray(dataset.XLONG.isel(Time=0))

    projection = ccrs.PlateCarree()
    figure, axis = plt.subplots(figsize=(8, 5.5), subplot_kw={"projection": projection})
    add_cached_features(axis)
    colours = axis.pcolormesh(longitude, latitude, np.asarray(field),
                              shading="auto", transform=projection)
    axis.set_extent([float(longitude.min()), float(longitude.max()),
                     float(latitude.min()), float(latitude.max())], crs=projection)
    grid = axis.gridlines(draw_labels=True, linewidth=0.4, alpha=0.5)
    grid.top_labels = False
    grid.right_labels = False
    units = field.attrs.get("units", "")
    axis.set_title(f"{variable}: time index {time_index}, level index {level_index}")
    figure.colorbar(colours, ax=axis, label=f"{variable} ({units})".strip())
    figure.tight_layout()

    target = output / f"custom_{variable.lower()}_map.png"
    figure.savefig(target, dpi=200)
    plt.close(figure)
    return target


def main() -> int:
    arguments = parse_arguments()
    run_directory = arguments.run_directory.expanduser().resolve()
    output_directory = arguments.output.expanduser().resolve()

    if not run_directory.is_dir():
        raise SystemExit(f"WRF run directory does not exist: {run_directory}")
    files = discover_wrfout(run_directory, domain=arguments.domain)
    output_directory.mkdir(parents=True, exist_ok=True)

    print("STEP 2: Inspecting the selected domain")
    print(f"  Domain: {arguments.domain}")
    print(f"  Files:  {len(files)}")
    print(f"  First:  {files[0].name}")
    print(f"  Last:   {files[-1].name}")

    custom_map = None
    with open_wrf_sequence(files) as dataset:
        if arguments.list_variables:
            describe_variables(dataset)
        if arguments.plot_variable:
            print(f"\nSTEP 3: Plotting custom variable {arguments.plot_variable}")
            custom_map = save_custom_map(
                dataset, arguments.plot_variable, output_directory,
                arguments.time_index, arguments.level_index,
            )

    print("\nSTEP 4: Creating the standard multi-domain report")
    products = create_hindcast_report(
        run_directory, output_directory, domain=arguments.domain,
        latitude=arguments.latitude, longitude=arguments.longitude,
    )

    print("\nFinished. Open these files:")
    for product, path in products.items():
        print(f"  {product:10s} {path}")
    if custom_map:
        print(f"  custom map {custom_map}")
    print("\nTip: rerun with --list-variables before choosing another field.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
