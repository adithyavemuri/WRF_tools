#!/usr/bin/env python3
"""Editable examples of all four averaging choices; plots and reduced NetCDF.

    .venv/bin/python examples/average_wrf_fields.py --demo
    .venv/bin/python examples/average_wrf_fields.py /path/to/wrf/run --domain d02

Edit STEP 1, then run. No simulation or PDF is generated. This teaching example
loads the selected period in memory; select a short period for large simulations.
The separate compare_simulations.py remains a simple site-comparison example.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import xarray as xr

from wrf_tools.averaging import layer_thickness, mean, to_height, wrf_cell_area
from wrf_tools.grid import destagger
from wrf_tools.io import discover_wrfout, open_wrf_sequence
from wrf_tools.visualization import GRAVITY, geographic_axis, history_times, temperature_celsius
from wrf_tools.turbulence import model_tke


# =============================================================================
# STEP 1: SETTINGS YOU CAN EDIT
# =============================================================================
VARIABLE = "wind_speed"       # Or "temperature", "model_tke", "TKE_PBL", etc.
# Raw variables must already be on (Time, bottom_top, south_north, west_east).
# Here QKE means QKE as written, NOT automatically QKE/2 or resolved TKE.
START_UTC = None              # Example: "2025-01-10T01:00:00" (inclusive)
END_UTC = None                # Example: "2025-01-10T06:00:00" (inclusive)
HORIZONTAL_WEIGHTING = "area" # "uniform" (equal cells) or "area"
PROFILE_COORDINATE = "height" # "model" (native levels) or "height"
HEIGHT_REFERENCE = "AGL"      # "AGL" or "MSL"; also applies to LAYER_METRES
HEIGHTS_METRES = np.array([50., 100., 200., 300., 500., 750., 1000., 1500., 2000.])
REGION = dict(south=51.5, north=52.5, west=4.5, east=5.5)
LAYER_METRES = (50., 200.)     # Physical layer for vertical-mean maps/time series
VERTICAL_WEIGHTING = "layer"  # "layer" (clipped thickness) or "uniform"
MAP_TIME_INDEX = -1           # -1 = final selected timestamp
SAVE_REDUCED_DATA = True      # Replot these means later without rereading WRF
# Time mean below is an equal-sample mean: appropriate to regular hourly states,
# not a duration-weighted mean of an irregular sequence. No time interpolation.


def select_field(dataset):
    """STEP 2: Select the variable. Add your own diagnostic here if needed."""
    if VARIABLE == "wind_speed":
        u = destagger(dataset.U, "west_east_stag")
        v = destagger(dataset.V, "south_north_stag")
        field = np.hypot(u, v)
        field.attrs = {"units": "m s-1", "long_name": "horizontal wind speed"}
    elif VARIABLE == "temperature":
        field = dataset.T.copy(data=temperature_celsius(dataset.T, dataset.P + dataset.PB))
        field.attrs = {"units": "degC", "long_name": "dry-theta temperature diagnostic"}
    elif VARIABLE == "model_tke":
        field = model_tke(dataset)  # QKE/2, TKE_PBL or dynamics TKE; see docs/TURBULENCE.md.
    else:
        field = dataset[VARIABLE]
    expected = ("Time", "bottom_top", "south_north", "west_east")
    if set(field.dims) != set(expected) or not field.attrs.get("units"):
        raise ValueError("Choose a mass-grid 3-D field with recorded units (destagger first if needed)")
    # Keep dimension coordinates; remove auxiliary XTIME/XLAT_U/etc. before
    # combining reductions with different retained dimensions.
    return field.transpose(*expected).reset_coords(drop=True).rename("selected_field")


def calculate_means(dataset):
    """STEP 3: Four independent, named reductions. No hidden averaging."""
    times = np.array(history_times(dataset), dtype="datetime64[s]")
    selected = np.ones(len(times), dtype=bool)
    if START_UTC is not None:
        selected &= times >= np.datetime64(START_UTC)
    if END_UTC is not None:
        selected &= times <= np.datetime64(END_UTC)
    if not selected.any():
        raise ValueError("No timestamps remain in the selected period")
    dataset = dataset.isel(Time=np.flatnonzero(selected)).assign_coords(Time=times[selected])
    lat = dataset.XLAT.isel(Time=0, drop=True).reset_coords(drop=True)
    lon = dataset.XLONG.isel(Time=0, drop=True).reset_coords(drop=True)
    if not np.allclose(dataset.XLAT, lat) or not np.allclose(dataset.XLONG, lon):
        raise ValueError("This example requires stationary domains")
    field = select_field(dataset)
    interfaces = (dataset.PH + dataset.PHB) / GRAVITY
    if HEIGHT_REFERENCE == "AGL":
        interfaces = interfaces - dataset.HGT
    elif HEIGHT_REFERENCE != "MSL":
        raise ValueError("HEIGHT_REFERENCE must be AGL or MSL")
    interfaces = interfaces.reset_coords(drop=True)
    height = destagger(interfaces, "bottom_top_stag").transpose(*field.dims)
    region = ((lat >= REGION["south"]) & (lat <= REGION["north"]) &
              (lon >= REGION["west"]) & (lon <= REGION["east"]))
    if not bool(region.any()):
        raise ValueError("REGION contains no grid-cell centres; edit the bounding box")
    area = wrf_cell_area(dataset).reset_coords(drop=True) if HORIZONTAL_WEIGHTING == "area" else None
    if HORIZONTAL_WEIGHTING not in {"uniform", "area"}:
        raise ValueError("HORIZONTAL_WEIGHTING must be uniform or area")
    horizontal = ["south_north", "west_east"]

    # A. HORIZONTAL MEAN -> profile at every time.
    # Native index remains an index; common-height interpolation happens FIRST.
    if PROFILE_COORDINATE == "height":
        profile_field = to_height(field, height, HEIGHTS_METRES, reference=HEIGHT_REFERENCE)
    elif PROFILE_COORDINATE == "model":
        profile_field = field
    else:
        raise ValueError("PROFILE_COORDINATE must be model or height")
    domain_profiles = mean(profile_field, horizontal, weighting=HORIZONTAL_WEIGHTING, weights=area)

    # B. SELECTED-AREA MEAN -> profiles at every time, and a region time series.
    region_profiles = mean(profile_field, horizontal, weighting=HORIZONTAL_WEIGHTING, weights=area, mask=region)

    # C. VERTICAL MEAN -> horizontal map at every time, within LAYER_METRES.
    thickness = layer_thickness(interfaces, *LAYER_METRES)
    # Match any explicit mass-level indexes before xarray arithmetic.
    if "bottom_top" in field.coords:
        thickness = thickness.assign_coords(bottom_top=field.bottom_top)
    if VERTICAL_WEIGHTING not in {"uniform", "layer"}:
        raise ValueError("VERTICAL_WEIGHTING must be uniform or layer")
    layer_maps = mean(field, "bottom_top", weighting=VERTICAL_WEIGHTING,
                      weights=thickness if VERTICAL_WEIGHTING == "layer" else None,
                      mask=thickness > 0)
    region_series = mean(layer_maps, horizontal, weighting=HORIZONTAL_WEIGHTING, weights=area, mask=region)

    # D. TIME MEAN -> one layer-mean map and one horizontal-mean profile.
    time_map = mean(layer_maps, "Time", weighting="uniform")
    time_profile = mean(domain_profiles, "Time", weighting="uniform")
    steps = np.diff(dataset.Time.values.astype("datetime64[s]").astype("int64"))
    if steps.size and not np.all(steps == steps[0]):
        print("NOTE: irregular timestamps; time means are equal-sample, NOT duration-weighted")
    result = xr.Dataset(dict(horizontal_mean=domain_profiles, selected_area_mean=region_profiles,
        selected_area_timeseries=region_series, vertical_mean=layer_maps,
        time_mean_map=time_map, time_mean_profile=time_profile,
        selected_area_mask=region, latitude=lat, longitude=lon))
    result.attrs = dict(variable=VARIABLE, horizontal_weighting=HORIZONTAL_WEIGHTING,
        profile_coordinate=PROFILE_COORDINATE, height_reference=HEIGHT_REFERENCE,
        vertical_weighting=VERTICAL_WEIGHTING, layer_metres=str(LAYER_METRES),
        region=str(REGION), time_weighting="equal saved samples; no temporal interpolation",
        vertical_mean_method="layer-representative values; partial boundary layers clipped")
    return result, dataset


def save_plots(result, dataset, output, *, synthetic=False):
    """STEP 4: Edit titles/axes/colours here. Maps include geographic context."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    output.mkdir(parents=True, exist_ok=True)
    prefix = "SYNTHETIC | " if synthetic else ""
    units = result.horizontal_mean.attrs["units"]
    field_label = result.horizontal_mean.attrs.get("long_name", VARIABLE.replace("_", " "))
    vertical = "height" if PROFILE_COORDINATE == "height" else "bottom_top"
    ylabel = f"Height {HEIGHT_REFERENCE} (m)" if vertical == "height" else "Native model-level index (not metres)"

    def save(figure, name):
        for suffix in ("png", "svg"):
            path = output / f"{name}.{suffix}"
            figure.savefig(path, dpi=170, bbox_inches="tight")
            print(f"Saved {path}")
        plt.close(figure)

    for name in ("horizontal_mean", "selected_area_mean"):
        fig, ax = plt.subplots(figsize=(7, 5), layout="constrained")
        profiles = result[name]
        for index in np.unique(np.linspace(0, profiles.sizes["Time"]-1, min(5, profiles.sizes["Time"]), dtype=int)):
            line = profiles.isel(Time=index)
            ax.plot(line, line[vertical], label=np.datetime_as_string(profiles.Time.values[index], unit="m"))
        title = "Full-domain horizontal mean" if name == "horizontal_mean" else "Selected-region horizontal mean"
        ax.set(xlabel=f"{field_label} ({units})", ylabel=ylabel,
               title=prefix+title+f"\n{HORIZONTAL_WEIGHTING} weighting")
        ax.grid(alpha=.25); ax.legend(title="UTC", frameon=False, fontsize=8)
        save(fig, name)

    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    ax.plot(result.Time, result.selected_area_timeseries, marker="o")
    ax.set(xlabel="Saved times (UTC)", ylabel=f"{field_label} ({units})",
           title=prefix+f"Region mean of {LAYER_METRES} m {HEIGHT_REFERENCE} layer")
    fig.autofmt_xdate(); ax.grid(alpha=.25); save(fig, "selected_area_timeseries")

    fig, ax = plt.subplots(figsize=(7, 5), layout="constrained")
    ax.plot(result.time_mean_profile, result.time_mean_profile[vertical])
    ax.set(xlabel=f"{field_label} ({units})", ylabel=ylabel, title=prefix+"Time-mean horizontal profile")
    ax.grid(alpha=.25); save(fig, "time_mean_profile")

    # Maps stay on each run's own grid and share one colour scale.
    maps = (("vertical_mean_map", result.vertical_mean.isel(Time=MAP_TIME_INDEX)),
            ("time_mean_map", result.time_mean_map))
    finite = np.concatenate([np.asarray(values).ravel() for _, values in maps])
    finite = finite[np.isfinite(finite)]
    if not finite.size:
        raise ValueError("No supported data in the chosen physical layer")
    low, high = float(finite.min()), float(finite.max())
    if high == low:
        high = low + 1
    for name, values in maps:
        fig = plt.figure(figsize=(8, 6))
        ax, geography = geographic_axis(fig, 111, dataset)
        artist = ax.pcolormesh(result.longitude, result.latitude, values,
                              transform=ccrs.PlateCarree(), cmap="viridis", shading="auto", vmin=low, vmax=high)
        title = "Vertical-layer mean" if name == "vertical_mean_map" else "Time mean of vertical-layer means"
        ax.set_title(prefix+title+f"\n{LAYER_METRES[0]:g}–{LAYER_METRES[1]:g} m {HEIGHT_REFERENCE}; {VERTICAL_WEIGHTING} weighting")
        fig.colorbar(artist, ax=ax, label=f"{field_label} ({units})", shrink=.8)
        ax.plot([REGION["west"], REGION["east"], REGION["east"], REGION["west"], REGION["west"]],
                [REGION["south"], REGION["south"], REGION["north"], REGION["north"], REGION["south"]],
                transform=ccrs.PlateCarree(), color="white", linewidth=1.3, label="Selected region", zorder=8)
        ax.legend(loc="upper left", fontsize=8)
        if name == "vertical_mean_map":
            stamp = np.datetime_as_string(values.Time.values, unit="m")+" UTC"
        else:
            stamp = (f"{np.datetime_as_string(result.Time.values[0], unit='m')} to "
                     f"{np.datetime_as_string(result.Time.values[-1], unit='m')} UTC; equal samples")
        fig.text(.5, .035, stamp, ha="center", fontsize=8)
        if not geography:
            print("NOTE: detailed geography unavailable; map uses the fallback background")
        save(fig, name)


def synthetic_dataset():
    """Small, clearly synthetic WRF-like fields, never a physics experiment."""
    nt, nz, ny, nx = 4, 4, 4, 5
    times = np.array([f"2025-01-01_0{i}:00:00".encode() for i in range(nt)])
    lat, lon = np.meshgrid(np.linspace(51, 53, ny), np.linspace(4, 6, nx), indexing="ij")
    faces = np.array([0., 50., 150., 300., 600.])
    ground = 20 + np.arange(nx)[None, None, :] + np.zeros((nt, ny, nx))
    phb = GRAVITY * (ground[:, None] + faces[None, :, None, None])
    speed = 3 + np.arange(nt)[:, None, None, None] + .005*(faces[:-1]+faces[1:])[None, :, None, None]/2
    return xr.Dataset(dict(Times=("Time", times),
        XLAT=(("Time", "south_north", "west_east"), np.broadcast_to(lat, (nt, ny, nx))),
        XLONG=(("Time", "south_north", "west_east"), np.broadcast_to(lon, (nt, ny, nx))),
        HGT=(("Time", "south_north", "west_east"), ground),
        PH=(("Time", "bottom_top_stag", "south_north", "west_east"), np.zeros_like(phb)),
        PHB=(("Time", "bottom_top_stag", "south_north", "west_east"), phb),
        U=(("Time", "bottom_top", "south_north", "west_east_stag"), np.broadcast_to(speed, (nt,nz,ny,nx+1))),
        V=(("Time", "bottom_top", "south_north_stag", "west_east"), np.zeros((nt,nz,ny+1,nx))),
        MAPFAC_M=(("Time", "south_north", "west_east"), np.ones((nt,ny,nx)))),
        attrs=dict(MAP_PROJ=1, DX=9000., DY=9000., STAND_LON=5., CEN_LAT=52., TRUELAT1=52., TRUELAT2=52.))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_directory", nargs="?", type=Path)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--domain", default="d02")
    parser.add_argument("--output", type=Path, default=Path("example_results/averaging"))
    args = parser.parse_args()
    if args.demo == (args.run_directory is not None):
        parser.error("choose --demo OR a WRF run directory")
    dataset = synthetic_dataset() if args.demo else open_wrf_sequence(discover_wrfout(args.run_directory, domain=args.domain))
    try:
        result, selected = calculate_means(dataset)
        save_plots(result, selected, args.output, synthetic=args.demo)
        if SAVE_REDUCED_DATA:
            result.attrs["data_origin"] = "SYNTHETIC DEMONSTRATION" if args.demo else "WRF history output"
            path = args.output / "averaged_fields.nc"
            result.to_netcdf(path)
            print(f"Saved {path} (all selected timestamps, not just displayed profiles)")
    finally:
        dataset.close()


if __name__ == "__main__":
    main()
