"""Simple WRF data animations with reusable PNG frames and methods metadata.

Frames are read one history slice at a time. All selected frames share the same
colour limits. Playback never invents intermediate atmospheric states.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .visualization import REFERENCES, geographic_axis, history_times


def read_animation_manifest(path):
    """Validate the actual-time movie/PNG manifest contract."""
    path = Path(path).expanduser().resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    times, frames = data.get("timestamps_utc", []), data.get("frames", [])
    if not times or len(times) != len(frames) or data.get("temporal_interpolation") != "none":
        raise ValueError("Expected one saved PNG per actual history time and no temporal interpolation")
    stamps = np.asarray(times, dtype="datetime64[s]")
    if np.isnat(stamps).any() or np.any(np.diff(stamps.astype("int64")) <= 0):
        raise ValueError("Animation times must be valid, unique and increasing")
    fps = data.get("playback_fps", 0)
    if not isinstance(fps, (int, float)) or not np.isfinite(fps) or not 0 < fps <= 60:
        raise ValueError("Invalid animation playback rate")
    limits = np.asarray(data.get("colour_limits_m_s", []), float)
    if limits.shape != (2,) or not np.isfinite(limits).all() or limits[1] <= limits[0]:
        raise ValueError("Invalid fixed colour limits")
    paths = [(path.parent / name).resolve() for name in frames]
    if any(not item.is_relative_to(path.parent) or item.suffix.lower() != ".png" or not item.is_file() for item in paths):
        raise ValueError("Frame paths must identify PNG files inside the animation output directory")
    return data, paths


def create_wind_animation(run_directory, output_directory, *, domain="d01", fps=1.0,
                          stride=1, maximum_frames=None, limits=None, movie_format="gif"):
    """Export a fixed-scale 10 m wind movie, PNG frames and methods manifest.

    ``stride`` selects existing history records, not new times. Output formats
    are GIF (Pillow) and MP4 (an installed FFmpeg). GIF encoding itself retains
    images in memory; choose MP4 for long movies. Input histories must describe
    a stationary grid. No simulation, model download or dependency install runs.
    """
    from .io import discover_wrfout, open_wrf
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter, FFMpegWriter
    from matplotlib.colors import Normalize
    import cartopy.crs as ccrs
    if not np.isfinite(fps) or not 0 < fps <= 60:
        raise ValueError("Playback fps must be positive and at most 60")
    if not isinstance(stride, int) or stride < 1:
        raise ValueError("History stride must be a positive integer")
    if maximum_frames is not None and (not isinstance(maximum_frames, int) or maximum_frames < 1):
        raise ValueError("maximum_frames must be a positive integer")
    if movie_format not in {"gif", "mp4"}:
        raise ValueError("Movie format must be gif or mp4")
    if movie_format == "mp4" and not FFMpegWriter.isAvailable():
        raise RuntimeError("MP4 requires FFmpeg on PATH. Use --format gif or configure FFmpeg locally.")
    files = discover_wrfout(run_directory, domain=domain)
    records = []
    grid_signature = None
    for file in files:
        with open_wrf(file) as ds:
            if any(name not in ds for name in ("U10", "V10", "XLAT", "XLONG")):
                raise ValueError("Wind animation requires U10, V10, XLAT and XLONG")
            signature = tuple(ds.attrs.get(name) for name in ("GRID_ID", "DX", "DY", "MAP_PROJ")) + (ds.sizes["south_north"], ds.sizes["west_east"])
            if grid_signature is not None and signature != grid_signature:
                raise ValueError("Animation inputs have incompatible WRF domain/grid metadata")
            grid_signature = signature
            records.extend((file, index, stamp) for index, stamp in enumerate(history_times(ds)))
    stamps = np.asarray([record[2] for record in records], dtype="datetime64[s]")
    if not stamps.size or np.any(np.diff(stamps.astype("int64")) <= 0):
        raise ValueError("Animation history times must be unique and strictly increasing")
    selected = records[::stride]
    if maximum_frames is not None:
        selected = selected[:maximum_frames]

    def read_frame(record):
        with open_wrf(record[0]) as ds:
            lat = np.asarray(ds.XLAT.isel(Time=record[1]), float)
            lon = np.asarray(ds.XLONG.isel(Time=record[1]), float)
            speed = np.hypot(np.asarray(ds.U10.isel(Time=record[1]), float),
                             np.asarray(ds.V10.isel(Time=record[1]), float))
            return speed, lat, lon

    first, latitude, longitude = read_frame(selected[0])
    maximum = 0.0
    for record in selected:
        speed, lat, lon = read_frame(record)
        if not np.allclose(lat, latitude, atol=1e-6) or not np.allclose(lon, longitude, atol=1e-6):
            raise ValueError("Moving-grid animations are not supported by this layout")
        finite = speed[np.isfinite(speed)]
        if not finite.size:
            raise ValueError(f"No finite wind values at {record[2]}")
        maximum = max(maximum, float(finite.max()))
    lower, upper = limits if limits is not None else (0.0, max(2.0, float(2 * np.ceil(maximum / 2))))
    if not np.isfinite([lower, upper]).all() or upper <= lower:
        raise ValueError("Colour limits must be finite and increasing")
    output = Path(output_directory).expanduser().resolve()
    frame_directory = output / "frames"
    frame_directory.mkdir(parents=True, exist_ok=True)
    norm = Normalize(lower, upper)
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 10}):
        fig = plt.figure(figsize=(8.5, 6.5), facecolor="white")
        with open_wrf(selected[0][0]) as ds:
            ax, geography = geographic_axis(fig, 111, ds)
        fig.subplots_adjust(left=.10, right=.9, bottom=.16, top=.81)
        mesh = ax.pcolormesh(longitude, latitude, first, transform=ccrs.PlateCarree(),
                             cmap="viridis", norm=norm, shading="auto")
        fig.colorbar(mesh, ax=ax, label="10 m wind speed (m/s)", pad=.035, shrink=.85)
        title = fig.text(.10, .92, "", size=14, weight="bold", color="#172d41")
        fig.text(.10, .86, f"{domain.upper()} · fixed colour limits · model output", size=10)
        selected_times = np.asarray([record[2] for record in selected], dtype="datetime64[s]")
        steps = np.diff(selected_times.astype("int64"))
        cadence = "one output time" if not steps.size else (
            f"{steps[0] / 60:g} simulated minutes between frames" if np.all(steps == steps[0]) else "irregular simulated intervals; see timestamps")
        fig.text(.10, .045, f"{cadence} · playback {fps:g} frames/s\n"
                 "Actual history states only; no temporal interpolation. Not a resolved-turbulence movie.",
                 size=8.5, color="#52697d")
        frame_paths = []

        def update(index):
            record = selected[index]
            speed, _, _ = read_frame(record)
            mesh.set_array(speed.ravel())
            title.set_text(f"WRF WIND  |  {record[2].replace('T', ' ')} UTC")
            return mesh, title

        try:
            # Keep numbered images for reproducible inspection and reuse.
            for index, record in enumerate(selected):
                update(index)
                path = frame_directory / f"{domain}_wind_{index:05d}.png"
                fig.savefig(path, dpi=120, facecolor="white")
                frame_paths.append(path)
            movie = output / f"{domain}_wind.{movie_format}"
            animation = FuncAnimation(fig, update, frames=len(selected), interval=1000 / fps,
                                       repeat=False, cache_frame_data=False)
            writer = PillowWriter(fps=fps) if movie_format == "gif" else FFMpegWriter(fps=fps)
            animation.save(movie, writer=writer, dpi=120)
        finally:
            plt.close(fig)
    metadata = {
        "schema_version": 1, "domain": domain, "variable": "10 m horizontal wind speed",
        "definition": "hypot(U10,V10); wind magnitude is invariant to orthonormal earth rotation",
        "units": "m s-1", "colour_limits_m_s": [lower, upper], "playback_fps": fps,
        "timestamps_utc": [record[2] for record in selected],
        "frames": [str(path.relative_to(output)) for path in frame_paths],
        "source_files": [record[0].name for record in selected],
        "history_stride": stride, "temporal_interpolation": "none",
        "geography_available": geography, "references": REFERENCES,
        "limitations": ["Stationary WRF grids only", "Does not resolve variability absent from history output",
                        "GIF encoding retains rendered frames in memory; MP4 is preferred for long sequences"],
    }
    manifest = output / f"{domain}_animation.json"
    manifest.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return {"movie": movie, "manifest": manifest, "frames": frame_directory}
