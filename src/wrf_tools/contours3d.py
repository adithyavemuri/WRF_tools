"""Actual model isolines on physical-height planes; optional renderer agnostic.

This is a stack of 2-D contours in 3-D coordinates, NOT volumetric isosurfaces
or an energy-budget diagnostic. No temporal interpolation is performed.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np


def horizontal_contours(values, x_km, y_km, heights_m, thresholds):
    """Extract full-grid contour polylines without bridging unsupported cells."""
    import contourpy
    values, x_km, y_km = np.asarray(values), np.asarray(x_km), np.asarray(y_km)
    if values.shape != (len(heights_m), len(y_km), len(x_km)):
        raise ValueError("Expected one (y,x) field per physical height")
    result = []
    for height, field in zip(heights_m, values):
        generator = contourpy.contour_generator(x=x_km, y=y_km,
            z=np.ma.masked_invalid(field), corner_mask=False, line_type="Separate")
        for threshold in thresholds:
            for line in generator.lines(float(threshold)):
                if len(line) > 1:
                    points = np.column_stack([line, np.full(len(line), height / 1000.)])
                    result.append(dict(value=float(threshold), height_m=float(height), points_km=points.tolist()))
    return result


def export_contour_sequence(run_directory, output, *, domain="d02", variable="wind_speed",
        heights=(100., 500., 1000., 1500.), reference="MSL", thresholds=(4., 8., 12., 16., 20.),
        vertical_exaggeration=150., maximum_frames=7, tke_source=None):
    """Export one JSON geometry contract for the optional Manim 3-D example.

    Native nominal DX/DY coordinates, fixed physical levels/thresholds, selected
    actual timestamps and recorded vertical exaggeration. Reads one 3-D frame
    at a time. Supported diagnostics: mass-grid horizontal speed and model TKE.
    """
    import xarray as xr
    from matplotlib import colormaps, colors
    from .averaging import to_height
    from .grid import destagger
    from .io import discover_wrfout, open_wrf_sequence
    from .turbulence import model_tke
    from .visualization import history_times, mass_heights
    heights, thresholds = np.asarray(heights, float), np.asarray(thresholds, float)
    for name, values in (("heights", heights), ("thresholds", thresholds)):
        if values.ndim != 1 or not values.size or not np.isfinite(values).all() or np.any(np.diff(values) <= 0):
            raise ValueError(f"{name} must be finite, nonempty and strictly increasing")
    if reference not in {"AGL", "MSL"} or heights[0] < 0:
        raise ValueError("Choose nonnegative AGL or MSL heights")
    if not np.isfinite(vertical_exaggeration) or vertical_exaggeration <= 0:
        raise ValueError("Vertical exaggeration must be positive and finite")
    if maximum_frames is not None and (not isinstance(maximum_frames, int) or maximum_frames < 1):
        raise ValueError("maximum_frames must be a positive integer or None")
    files = discover_wrfout(run_directory, domain=domain)
    frames = []
    with open_wrf_sequence(files) as ds:
        times = history_times(ds)
        if not np.allclose(ds.XLAT, ds.XLAT.isel(Time=0)) or not np.allclose(ds.XLONG, ds.XLONG.isel(Time=0)):
            raise ValueError("Moving-domain contour stacks are not supported")
        dx, dy = float(ds.attrs["DX"]), float(ds.attrs["DY"])
        if not np.isfinite([dx, dy]).all() or min(dx, dy) <= 0:
            raise ValueError("DX/DY must be positive and finite")
        x = np.arange(ds.sizes["west_east"]) * dx / 1000
        y = np.arange(ds.sizes["south_north"]) * dy / 1000
        if min(len(x), len(y)) < 2:
            raise ValueError("A contour map requires at least two cells along each horizontal axis")
        source_metadata = None
        for index, stamp in enumerate(times[:maximum_frames]):
            frame = ds.isel(Time=index, drop=True)
            if variable == "wind_speed":
                field = np.hypot(destagger(frame.U, "west_east_stag"), destagger(frame.V, "south_north_stag"))
                source_metadata = dict(units="m s-1", definition="hypot(mass-grid U, mass-grid V)",
                                       source_variables=["U", "V"])
            elif variable == "model_tke":
                field = model_tke(frame, source=tke_source)
                source_metadata = {key: field.attrs[key] for key in (
                    "units", "source_variable", "conversion_factor", "tke_kind", "vertical_processing")}
            else:
                raise ValueError("variable must be wind_speed or model_tke")
            field = field.transpose("bottom_top", "south_north", "west_east").reset_coords(drop=True)
            z = mass_heights(frame.PH, frame.PHB, frame.HGT, axis=0, agl=reference=="AGL")
            height = xr.DataArray(z, dims=field.dims, coords=field.coords)
            samples = to_height(field, height, heights, reference=reference).transpose("height", "south_north", "west_east")
            paths = horizontal_contours(samples.values, x, y, heights, thresholds)
            frames.append(dict(time_utc=stamp, contours=paths,
                finite_fraction_by_height=np.isfinite(samples.values).mean(axis=(1, 2)).tolist()))
        land_water = []
        if "LANDMASK" in ds:
            coast = horizontal_contours(np.asarray(ds.LANDMASK.isel(Time=0))[None], x, y, [0.], [.5])
            land_water = [path["points_km"] for path in coast]
    if not any(frame["contours"] for frame in frames):
        raise ValueError("No contours intersect the requested thresholds at supported physical heights")
    low, high = float(thresholds[0]), float(thresholds[-1])
    norm = colors.Normalize(low, high if high > low else low+1)
    bundle = dict(schema_version=1, domain=domain, variable=variable,
        source=source_metadata, source_files=[path.name for path in files],
        x_extent_km=float(x[-1]), y_extent_km=float(y[-1]), heights_m=heights.tolist(),
        height_reference=reference, thresholds=thresholds.tolist(),
        threshold_colours={str(float(value)): colors.to_hex(.7*np.array(colormaps["viridis"](norm(value))[:3])+.3) for value in thresholds},
        colour_method="viridis lightened 30 percent for a dark background; same colours at every time/height",
        vertical_exaggeration=float(vertical_exaggeration), frames=frames,
        model_land_water_boundaries=land_water, temporal_interpolation="none",
        limitations=["Stacked horizontal isolines, not volumetric isosurfaces",
            "Nominal native grid-km axes, not exact geodesic distances", "Stationary domains only",
            "AGL coordinate stacks are not a geometric MSL terrain scene",
            "No extrapolation or temporal morphing", "High values alone do not identify spurious energy production"])
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, separators=(",", ":"), allow_nan=False))
    return output
