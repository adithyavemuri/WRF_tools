"""Terrain-aware isosurface geometry; rendering does not alter model physics.

Lewiner marching cubes runs in native (k,j,i) index space. Vertices are mapped
to nominal projected x/y and trilinearly interpolated WRF mass heights (MSL).
This is not Cartesian differentiation, a storm detector, or volume integration.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def _clip_top(vertices, faces, top_km):
    """Clip triangles geometrically; do not cap or close the resulting surface."""
    result, triangles = [], []
    for triangle in vertices[faces]:
        polygon = []
        for start, end in zip(triangle, np.roll(triangle, -1, axis=0)):
            a, b = start[2] <= top_km, end[2] <= top_km
            if a:
                polygon.append(start)
            if a != b:
                weight = (top_km - start[2]) / (end[2] - start[2])
                polygon.append(start + weight * (end - start))
        if len(polygon) >= 3:
            offset = len(result)
            result.extend(polygon)
            triangles.extend([offset, offset+i, offset+i+1] for i in range(1, len(polygon)-1))
    vertices = np.asarray(result, dtype=float).reshape(-1, 3)
    faces = np.asarray(triangles, dtype=int).reshape(-1, 3)
    if len(faces):
        edges = vertices[faces]
        area = np.linalg.norm(np.cross(edges[:,1]-edges[:,0], edges[:,2]-edges[:,0]), axis=1)
        faces = faces[area > 0]
    return vertices, faces


def isosurface_mesh(values, heights_m, x_km, y_km, level, *, top_metres=None):
    """Extract one scalar isosurface as vertices_km/faces in (x,y,z MSL) order.

    Arrays must be finite with shape (k,y,x), increasing height in every column,
    and increasing one-dimensional horizontal coordinates. Missing cells are
    rejected rather than filled. Out-of-range/constant thresholds yield an
    empty mesh. Optional MSL top clips triangles without inventing a closed cap.
    No smoothing, extrapolation or temporal interpolation is performed.

    References: scikit-image marching_cubes (Lewiner et al., 2003), and the
    WRF technical note for terrain-following coordinates. Geometry follows
    linear grid-cell interpolation, not unresolved atmospheric structures.
    """
    from scipy.ndimage import map_coordinates
    try:
        from skimage.measure import marching_cubes
    except ImportError as exc:
        raise ImportError('Install the optional mesh dependency: pip install "wrf-tools[isosurface]"') from exc
    values, heights = np.asarray(values, float), np.asarray(heights_m, float)
    x, y = np.asarray(x_km, float), np.asarray(y_km, float)
    if values.ndim != 3 or min(values.shape) < 2 or heights.shape != values.shape:
        raise ValueError("values and heights_m must share a (k,y,x) shape with at least two points per axis")
    if x.ndim != 1 or y.ndim != 1 or values.shape[1:] != (len(y), len(x)):
        raise ValueError("x_km/y_km must match the horizontal volume shape")
    if not all(np.isfinite(a).all() for a in (values, heights, x, y)):
        raise ValueError("Missing/nonfinite volume values or coordinates are not filled or bridged")
    if np.any(np.diff(x) <= 0) or np.any(np.diff(y) <= 0) or np.any(np.diff(heights, axis=0) <= 0):
        raise ValueError("Horizontal coordinates and each height column must be strictly increasing")
    if not np.isscalar(level) or not np.isfinite(level):
        raise ValueError("level must be one finite scalar")
    if top_metres is not None and (not np.isscalar(top_metres) or not np.isfinite(top_metres)):
        raise ValueError("top_metres must be finite")
    # The extraction backend uses float32; do not manufacture a surface from a
    # range that collapses to a constant at that precision.
    volume = values.astype(np.float32)
    if not np.isfinite(volume).all():
        raise ValueError("Volume exceeds the float32 range supported by marching cubes")
    if not float(volume.min()) < float(level) < float(volume.max()):
        return dict(level=float(level), vertices_km=[], faces=[])
    indices, faces, _, _ = marching_cubes(volume, level=float(level), allow_degenerate=False)
    k, j, i = indices.T
    z = map_coordinates(heights, [k, j, i], order=1, mode="nearest", prefilter=False)
    vertices = np.column_stack((np.interp(i, np.arange(len(x)), x),
                                np.interp(j, np.arange(len(y)), y), z/1000))
    if top_metres is not None:
        vertices, faces = _clip_top(vertices, faces, float(top_metres)/1000)
    return dict(level=float(level), vertices_km=vertices.tolist(), faces=faces.tolist())


def _indices(size, stride):
    return np.unique(np.r_[np.arange(0, size, stride), size-1])


def _terrain(frame, x, y, rows, columns):
    """Use WRF terrain and binary land/water classification; never bathymetry."""
    from matplotlib import colormaps, colors
    from .contours3d import horizontal_contours
    ground = np.asarray(frame.HGT.transpose("south_north", "west_east"), float)
    mask = np.asarray(frame.LANDMASK.transpose("south_north", "west_east"), float)
    if not np.isfinite(ground).all() or not np.isin(mask, [0, 1]).all():
        raise ValueError("HGT must be finite and LANDMASK must contain only 0/1")
    # WRF land below MSL is retained; the water surface is drawn at sea level.
    display = np.where(mask == 1, ground, 0.)
    sampled = display[np.ix_(rows, columns)]
    xx, yy = np.meshgrid(x, y)
    vertices = np.column_stack((xx.ravel(), yy.ravel(), sampled.ravel()/1000))
    faces, shades = [], []
    cmap = colormaps["gist_earth"]
    ny, nx = sampled.shape
    for j in range(ny-1):
        for i in range(nx-1):
            a = j*nx+i
            face = [a, a+1, a+nx+1, a+nx]
            # A display-only majority classification for each sampled quad.
            land = mask[rows[j]:rows[j+1]+1, columns[i]:columns[i+1]+1].mean() >= .5
            height = float(vertices[face, 2].mean()*1000)
            colour = colors.to_hex(cmap(.39 + .36*np.clip(height/1200, 0, 1))) if land else "#175373"
            faces.append(face)
            shades.append(colour)
    # Coastline from FULL model resolution, independent of mesh display stride.
    coast = horizontal_contours(mask[None],
        np.arange(ground.shape[1])*float(frame.attrs["DX"])/1000,
        np.arange(ground.shape[0])*float(frame.attrs["DY"])/1000, [0.], [.5])
    return dict(vertices_km=vertices.tolist(), faces=faces, colours=shades,
        coastlines_km=[item["points_km"] for item in coast],
        elevation_range_m=[float(ground.min()), float(ground.max())],
        geographic_bounds=dict(south=float(frame.XLAT.min()), north=float(frame.XLAT.max()),
                               west=float(frame.XLONG.min()), east=float(frame.XLONG.max())),
        method="HGT land; LANDMASK water drawn at 0 m MSL; no bathymetry; model-resolution coastline",
        face_colour_method="Display-only sampled-quad majority LANDMASK; height-coloured land, uniform blue water")


def export_isosurface_sequence(run_directory, output, *, domain="d02", variable="wind_speed",
        thresholds=(12., 16.), top_metres=4000., horizontal_stride=3,
        vertical_exaggeration=25., maximum_frames=7, maximum_faces=30000, tke_source=None,
        diagnostics=None, earth_radius_metres=6370000.):
    """Export actual WRF isosurfaces and terrain/ocean for the Manim mesh scene.

    Reads one actual timestamp at a time. Wind is horizontal mass-grid speed;
    model_tke requires an existing supported energy field. Heights are MSL from
    mass-averaged (PH+PHB)/9.81. Horizontal stride is explicit point subsampling,
    not filtering; selected endpoints are kept and geometry can lose features.
    Moving grids, missing data and unsupported fields raise clear errors.
    A numeric top clips geometry; top_metres=None retains all saved mass levels.
    Sides and the lowest mass level remain open. The actual model top is
    recorded separately from the selected display height.

    Optional diagnostics={name: thresholds} exports schema v2 for the offline
    diagnostic selector and movable native-grid sections. Supported names:
    wind_speed, vertical_velocity, vertical_vorticity, q_criterion, model_tke.
    This mapping replaces variable/thresholds; their nondefault values cannot
    be combined with it. Derivatives use spherical physical-coordinate
    Jacobians and Earth-relative wind, not the uniform-Cartesian Q helper.
    These are finite-difference post-processing diagnostics, not WRF operators.
    Missing source fields disable that selection, never fabricate its values.
    """
    if diagnostics is not None:
        from ._diagnostic_geometry import _export_diagnostics
        if variable != "wind_speed" or list(thresholds) != [12., 16.]:
            raise ValueError("Use diagnostics OR variable/thresholds, not both")
        return _export_diagnostics(run_directory, output, domain=domain, diagnostics=diagnostics,
            top_metres=top_metres, horizontal_stride=horizontal_stride,
            vertical_exaggeration=vertical_exaggeration, maximum_frames=maximum_frames,
            maximum_faces=maximum_faces, tke_source=tke_source, earth_radius_metres=earth_radius_metres)
    from .grid import destagger
    from .io import discover_wrfout, open_wrf_sequence
    from .turbulence import model_tke
    from .visualization import history_times, mass_heights
    for name, value in (("horizontal_stride", horizontal_stride), ("maximum_faces", maximum_faces)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if maximum_frames is not None and (isinstance(maximum_frames, bool) or not isinstance(maximum_frames, int) or maximum_frames < 1):
        raise ValueError("maximum_frames must be positive or None")
    if (top_metres is not None and (not np.isfinite(top_metres) or top_metres <= 0)) or not np.isfinite(vertical_exaggeration) or vertical_exaggeration <= 0:
        raise ValueError("top_metres and vertical_exaggeration must be positive and finite")
    thresholds = np.asarray(thresholds, float)
    if thresholds.ndim != 1 or not thresholds.size or not np.isfinite(thresholds).all() or np.any(np.diff(thresholds) <= 0):
        raise ValueError("thresholds must be finite, nonempty and strictly increasing")
    if variable not in {"wind_speed", "model_tke"}:
        raise ValueError("variable must be wind_speed or model_tke")
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"Choose a new geometry output or remove it explicitly: {output}")
    files = discover_wrfout(run_directory, domain=domain)
    frames = []
    with open_wrf_sequence(files) as ds:
        required = {"HGT", "LANDMASK", "PH", "PHB", "XLAT", "XLONG"}
        if variable == "wind_speed":
            required |= {"U", "V"}
        if missing := required-set(ds.variables):
            raise ValueError(f"Missing WRF variables: {', '.join(sorted(missing))}")
        base = ds.isel(Time=0)
        coordinates = {name: np.asarray(base[name]) for name in ("XLAT", "XLONG", "HGT", "LANDMASK")}
        dx, dy = float(ds.attrs["DX"]), float(ds.attrs["DY"])
        if not np.isfinite([dx, dy]).all() or min(dx, dy) <= 0:
            raise ValueError("DX/DY must be positive and finite")
        rows = _indices(ds.sizes["south_north"], horizontal_stride)
        columns = _indices(ds.sizes["west_east"], horizontal_stride)
        x, y = columns*dx/1000, rows*dy/1000
        terrain = _terrain(base, x, y, rows, columns)
        for index, stamp in enumerate(history_times(ds)[:maximum_frames]):
            frame = ds.isel(Time=index, drop=True)
            for name, original in coordinates.items():
                if not np.allclose(frame[name], original):
                    raise ValueError("Moving grids or time-varying terrain/land masks are not supported")
            if variable == "wind_speed":
                field = np.hypot(destagger(frame.U, "west_east_stag"), destagger(frame.V, "south_north_stag"))
                source = dict(units="m s-1", definition="hypot(mass-grid U, mass-grid V)", source_variables=["U", "V"])
            else:
                field = model_tke(frame, source=tke_source)
                source = {key: field.attrs[key] for key in ("units", "source_variable", "conversion_factor",
                    "tke_kind", "vertical_processing", "method_reference", "warning")}
            values = field.transpose("bottom_top", "south_north", "west_east").values
            heights = mass_heights(frame.PH, frame.PHB, frame.HGT, axis=0, agl=False)
            # Keep the first level wholly above the chosen top for clipping.
            above = np.flatnonzero(np.min(heights, axis=(1, 2)) > top_metres) if top_metres is not None else np.array([], dtype=int)
            stop = int(above[0]+1) if above.size else len(heights)
            interface_top = np.asarray((frame.PH+frame.PHB).isel(bottom_top_stag=-1), float)/9.81
            top_ranges = dict(interface_msl_m=[float(interface_top.min()), float(interface_top.max())],
                highest_mass_msl_m=[float(heights[-1].min()), float(heights[-1].max())])
            values = values[:stop][:, rows][:, :, columns]
            heights = heights[:stop][:, rows][:, :, columns]
            meshes = [isosurface_mesh(values, heights, x, y, level, top_metres=top_metres) for level in thresholds]
            count = sum(len(mesh["faces"]) for mesh in meshes)
            if count > maximum_faces:
                raise ValueError(f"{stamp}: {count} faces exceed maximum_faces={maximum_faces}; explicitly increase the limit or horizontal_stride")
            frames.append(dict(time_utc=stamp, meshes=meshes, face_count=count, model_top=top_ranges))
        model_top = dict(
            interface_msl_m=[min(f["model_top"]["interface_msl_m"][0] for f in frames),
                             max(f["model_top"]["interface_msl_m"][1] for f in frames)],
            highest_mass_msl_m=[min(f["model_top"]["highest_mass_msl_m"][0] for f in frames),
                                max(f["model_top"]["highest_mass_msl_m"][1] for f in frames)],
            pressure_pa=float(np.asarray(base.P_TOP).item()) if "P_TOP" in base else None)
    if not any(frame["face_count"] for frame in frames):
        raise ValueError("No isosurfaces intersect the selected thresholds and vertical extent")
    bundle = dict(schema="wrf-tools-isosurfaces", schema_version=1, domain=domain,
        variable=variable, source=source, source_files=[path.name for path in files],
        thresholds=thresholds.tolist(), top_metres=float(top_metres) if top_metres is not None else model_top["highest_mass_msl_m"][1],
        requested_top_metres=None if top_metres is None else float(top_metres), model_top=model_top,
        height_reference="MSL",
        horizontal_stride=horizontal_stride, nominal_spacing_km=[dx/1000, dy/1000],
        vertical_exaggeration=float(vertical_exaggeration), terrain=terrain, frames=frames,
        x_extent_km=float(x[-1]), y_extent_km=float(y[-1]), temporal_interpolation="none",
        coordinate_method="Native index-space marching cubes; x/y interpolation on nominal grid; trilinear physical mass height",
        references=["https://scikit-image.org/docs/stable/api/skimage.measure.html#skimage.measure.marching_cubes",
                    "https://doi.org/10.5065/1dfh-6p97"],
        limitations=["Regional projected cutout, not a spherical globe", "Nominal DX/DY, not geodesic distances",
            "Explicit point subsampling, not antialias filtering; small features can disappear",
            "Open surfaces at top, side boundaries and lowest mass level; not enclosed-volume estimates",
            "No smoothing, extrapolation, storm identification or temporal shape morphing",
            "Water at sea level, no bathymetry; terrain and ocean colours are illustrative, not satellite imagery",
            "Clipped triangles approximate the mapped surface linearly; fixed thresholds are user choices"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    return output
