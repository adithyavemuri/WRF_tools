"""Run independent wrf-tools integration checks against a real WRF output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import traceback

import numpy as np

from wrf_tools.coupling.openfast import validate_bts, wind_field_from_components, write_bts
from wrf_tools.diagnostics import resolved_tke, wind_direction, wind_speed
from wrf_tools.grid import destagger, interpolate_to_levels, nearest_grid_point, subset_by_bounds
from wrf_tools.io import (
    discover_wrfout,
    get_variable,
    open_wrf,
    open_wrf_sequence,
    validate_wrf_dataset,
)
from wrf_tools.les import calculate_fluxes, calculate_total_tke, load_velocity
from wrf_tools.types import GeoBounds


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    path = args.path.resolve()
    results: list[dict[str, object]] = []

    def check(name, operation):
        try:
            detail = operation()
            results.append({"name": name, "status": "PASS", "detail": detail})
        except Exception as error:  # continue so every independent capability is audited
            results.append(
                {
                    "name": name,
                    "status": "FAIL",
                    "error": f"{type(error).__name__}: {error}",
                    "traceback": traceback.format_exc(limit=3),
                }
            )

    check(
        "discover_wrfout",
        lambda: {"matched": path in discover_wrfout(path.parent), "count": len(discover_wrfout(path.parent))},
    )

    dataset_box = {}

    def open_dataset():
        dataset = open_wrf(path)
        dataset_box["dataset"] = dataset
        return {"dimensions": dict(dataset.sizes), "variables": len(dataset.data_vars)}

    check("open_wrf", open_dataset)
    dataset = dataset_box.get("dataset")
    if dataset is None:
        print(json.dumps(results, indent=2, default=str))
        return 1

    check("validate_wrf_dataset", lambda: validate_wrf_dataset(dataset) or "valid WRF grid")
    check("get_variable", lambda: {"U": list(get_variable(dataset, "U", time=0).shape)})

    lat_name = "XLAT" if "XLAT" in dataset else "XLAT_M"
    lon_name = "XLONG" if "XLONG" in dataset else "XLONG_M"
    latitude = np.asarray(dataset[lat_name].isel(Time=0) if "Time" in dataset[lat_name].dims else dataset[lat_name])
    longitude = np.asarray(dataset[lon_name].isel(Time=0) if "Time" in dataset[lon_name].dims else dataset[lon_name])
    center_y, center_x = latitude.shape[-2] // 2, latitude.shape[-1] // 2

    check(
        "nearest_grid_point",
        lambda: nearest_grid_point(
            latitude,
            longitude,
            float(latitude[center_y, center_x]),
            float(longitude[center_y, center_x]),
        ).__dict__,
    )

    def geographic_subset():
        delta = 0.05
        bounds = GeoBounds(
            west=float(longitude[center_y, center_x]) - delta,
            south=float(latitude[center_y, center_x]) - delta,
            east=float(longitude[center_y, center_x]) + delta,
            north=float(latitude[center_y, center_x]) + delta,
        )
        subset, slices = subset_by_bounds(latitude, latitude, longitude, bounds)
        return {"shape": list(subset.shape), "slices": [str(item) for item in slices]}

    check("subset_by_bounds", geographic_subset)

    velocity_box = {}

    def velocity_components():
        u, v, w = load_velocity(dataset)
        velocity_box.update(u=u, v=v, w=w)
        return {"u": list(u.shape), "v": list(v.shape), "w": list(w.shape)}

    check("load_velocity_and_destagger", velocity_components)

    def wind_diagnostics():
        u = np.asarray(velocity_box["u"].isel(Time=0, bottom_top=0))[center_y - 1:center_y + 2, center_x - 1:center_x + 2]
        v = np.asarray(velocity_box["v"].isel(Time=0, bottom_top=0))[center_y - 1:center_y + 2, center_x - 1:center_x + 2]
        return {
            "speed_mean": float(np.mean(wind_speed(u, v))),
            "direction_mean": float(np.mean(wind_direction(u, v))),
        }

    check("wind_diagnostics", wind_diagnostics)

    def vertical_interpolation():
        ph = np.asarray(dataset["PH"].isel(Time=0, south_north=center_y, west_east=center_x))
        phb = np.asarray(dataset["PHB"].isel(Time=0, south_north=center_y, west_east=center_x))
        height_stag = (ph + phb) / 9.81
        height = destagger(height_stag, 0)
        temperature = np.asarray(dataset["T"].isel(Time=0, south_north=center_y, west_east=center_x)) + 300.0
        target = float((height[0] + height[-1]) / 2.0)
        value = interpolate_to_levels(temperature, height, target, axis=0)
        return {"height": target, "potential_temperature": float(value)}

    check("vertical_interpolation", vertical_interpolation)

    def les_diagnostics():
        u = np.asarray(velocity_box["u"].isel(bottom_top=0, south_north=center_y, west_east=center_x))
        v = np.asarray(velocity_box["v"].isel(bottom_top=0, south_north=center_y, west_east=center_x))
        w = np.asarray(velocity_box["w"].isel(bottom_top=0, south_north=center_y, west_east=center_x))
        return {
            "resolved_tke": float(resolved_tke(u, v, w)),
            "total_tke": float(calculate_total_tke(u, v, w)),
            "fluxes": {name: float(value) for name, value in calculate_fluxes(u, v, w).items()},
        }

    check("les_diagnostics", les_diagnostics)

    results.append(
        {
            "name": "open_wrf_sequence",
            "status": "SKIP",
            "detail": "Multi-file opening is outside this single-file audit",
        }
    )

    def bts_round_trip():
        time_count = min(8, dataset.sizes.get("Time", 1))
        z_count = min(5, dataset.sizes.get("bottom_top", 1))
        y_slice = slice(max(center_y - 2, 0), min(center_y + 3, dataset.sizes["south_north"]))
        u = np.asarray(velocity_box["u"].isel(Time=slice(0, time_count), bottom_top=slice(0, z_count), south_north=y_slice, west_east=center_x))
        v = np.asarray(velocity_box["v"].isel(Time=slice(0, time_count), bottom_top=slice(0, z_count), south_north=y_slice, west_east=center_x))
        w = np.asarray(velocity_box["w"].isel(Time=slice(0, time_count), bottom_top=slice(0, z_count), south_north=y_slice, west_east=center_x))
        field = wind_field_from_components(
            u,
            v,
            w,
            time_axis=0,
            vertical_axis=1,
            lateral_axis=2,
            dy=float(dataset.attrs.get("DY", 1.0)),
            dz=1.0,
            dt=float(dataset.attrs.get("DT", 1.0)),
            hub_height=2.0,
            bottom_height=0.0,
        )
        with tempfile.TemporaryDirectory() as directory:
            target = write_bts(Path(directory) / "sample.bts", field)
            actual = validate_bts(target, field)
        return {"shape": list(actual.velocity.shape), "max_speed": float(np.max(actual.velocity))}

    check("openfast_bts_round_trip", bts_round_trip)
    dataset.close()
    print(json.dumps(results, indent=2, default=str))
    return int(any(item["status"] == "FAIL" for item in results))


if __name__ == "__main__":
    raise SystemExit(main())
