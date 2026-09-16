"""Focused reporting for time-ordered, mesoscale WRF hindcasts."""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

from .grid import nearest_grid_point
from .io import discover_wrfout, open_wrf_sequence, validate_wrf_dataset
from .quality import quality_control
from .reporting import provenance, write_html_report, write_json_report, write_pdf_report


SURFACE_VARIABLES = ("T2", "PSFC", "Q2", "U10", "V10", "PBLH", "RAINC", "RAINNC")


def _serial(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.datetime64):
        return str(value.astype("datetime64[s]"))
    return value


def _timestamps(dataset: Any) -> list[str]:
    if "Times" in dataset:
        raw = np.asarray(dataset.Times)
        if raw.ndim == 1:
            return [bytes(value).decode().replace("_", "T", 1) for value in raw]
        return [b"".join(row).decode().replace("_", "T", 1) for row in raw]
    return [str(value.astype("datetime64[s]")) for value in np.asarray(dataset.XTIME)]


def summarize_hindcast(dataset: Any, *, files: Iterable[Path], cell: Any) -> dict[str, Any]:
    """Return JSON-safe, deterministic summary statistics for a WRF sequence."""
    times = _timestamps(dataset)
    statistics: dict[str, dict[str, Any]] = {}
    for name in SURFACE_VARIABLES:
        if name not in dataset:
            continue
        values = np.asarray(dataset[name], dtype=float)
        statistics[name] = {
            "units": str(dataset[name].attrs.get("units", "")),
            "minimum": float(np.nanmin(values)),
            "mean": float(np.nanmean(values)),
            "maximum": float(np.nanmax(values)),
        }
    issues = quality_control(dataset[[name for name in SURFACE_VARIABLES if name in dataset]])
    result: dict[str, Any] = {
        "files": [str(Path(item).resolve()) for item in files],
        "file_count": len(times),
        "start_time": times[0],
        "end_time": times[-1],
        "timestamps": times,
        "grid": {
            "model_title": str(dataset.attrs.get("TITLE", "" )).strip(),
            "domain_id": _serial(dataset.attrs.get("GRID_ID")),
            "west_east": int(dataset.sizes["west_east"]),
            "south_north": int(dataset.sizes["south_north"]),
            "dx_metres": _serial(dataset.attrs.get("DX")),
            "dy_metres": _serial(dataset.attrs.get("DY")),
            "map_projection": _serial(dataset.attrs.get("MAP_PROJ")),
            "vertical_levels": int(dataset.sizes.get("bottom_top", 0)),
        },
        "physics": {
            name.lower(): _serial(dataset.attrs.get(name))
            for name in (
                "MP_PHYSICS", "RA_LW_PHYSICS", "RA_SW_PHYSICS",
                "SF_SFCLAY_PHYSICS", "SF_SURFACE_PHYSICS",
                "BL_PBL_PHYSICS", "CU_PHYSICS",
            )
        },
        "selected_point": {
            "requested_or_centre_latitude": cell.latitude,
            "requested_or_centre_longitude": cell.longitude,
            "grid_x": int(cell.x),
            "grid_y": int(cell.y),
        },
        "surface_statistics": statistics,
        "quality_control": {
            "status": "PASS" if not issues else "ISSUES_FOUND",
            "error_count": sum(item.severity == "ERROR" for item in issues),
            "warning_count": sum(item.severity == "WARNING" for item in issues),
            "issues": [item.to_dict() for item in issues],
        },
    }
    if {"RAINC", "RAINNC"} <= set(dataset):
        accumulated = np.asarray(dataset.RAINC + dataset.RAINNC, dtype=float)
        total = accumulated[-1] - accumulated[0]
        result["precipitation"] = {
            "domain_mean_accumulation_mm": float(np.nanmean(total)),
            "domain_maximum_accumulation_mm": float(np.nanmax(total)),
            "selected_point_accumulation_mm": float(total[cell.y, cell.x]),
        }
    return result


def _save_figures(dataset: Any, output: Path, cell: Any, times: list[str]) -> list[Path]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError as exc:
        raise ImportError("Hindcast figures require: pip install wrf-tools[plot]") from exc

    lat = np.asarray(dataset.XLAT.isel(Time=0))
    lon = np.asarray(dataset.XLONG.isel(Time=0))
    datetimes = np.asarray(times, dtype="datetime64[s]")
    figures: list[Path] = []

    def field_figure(values: Any, filename: str, title: str, label: str, cmap: str) -> None:
        fig, ax = plt.subplots(figsize=(7.4, 5.4))
        mesh = ax.pcolormesh(lon, lat, np.asarray(values), shading="auto", cmap=cmap)
        ax.scatter([cell.longitude], [cell.latitude], c="black", s=24, marker="x", label="Analysis point")
        ax.set(xlabel="Longitude", ylabel="Latitude", title=title)
        ax.legend(loc="best")
        fig.colorbar(mesh, ax=ax, label=label)
        target = output / filename
        fig.tight_layout(); fig.savefig(target, dpi=180); plt.close(fig); figures.append(target)

    if "HGT" in dataset:
        field_figure(dataset.HGT.isel(Time=0), "domain_terrain.png", "WRF domain and terrain", "Terrain height (m)", "terrain")
    if "T2" in dataset:
        field_figure(dataset.T2.isel(Time=-1) - 273.15, "final_temperature.png", f"2 m temperature at {times[-1]} UTC", "Temperature (deg C)", "coolwarm")
    if {"U10", "V10"} <= set(dataset):
        speed = np.hypot(dataset.U10.isel(Time=-1), dataset.V10.isel(Time=-1))
        field_figure(speed, "final_wind_speed.png", f"10 m wind speed at {times[-1]} UTC", "Wind speed (m s-1)", "viridis")
    if {"RAINC", "RAINNC"} <= set(dataset):
        rain = (dataset.RAINC + dataset.RAINNC).isel(Time=-1) - (dataset.RAINC + dataset.RAINNC).isel(Time=0)
        field_figure(rain, "accumulated_precipitation.png", "Accumulated precipitation", "Precipitation (mm)", "Blues")

    available = [name for name in ("T2", "U10", "V10", "PBLH") if name in dataset]
    if available:
        rows = 3 if "PBLH" in dataset else 2
        fig, axes = plt.subplots(rows, 1, figsize=(8.2, 2.5 * rows), sharex=True)
        axes = np.atleast_1d(axes)
        position = {"south_north": cell.y, "west_east": cell.x}
        if "T2" in dataset:
            axes[0].plot(datetimes, np.asarray(dataset.T2.isel(position)) - 273.15, marker="o")
            axes[0].set_ylabel("T2 (deg C)")
        if {"U10", "V10"} <= set(dataset):
            wind = np.hypot(dataset.U10.isel(position), dataset.V10.isel(position))
            axes[1].plot(datetimes, wind, marker="o", color="tab:green")
            axes[1].set_ylabel("Wind (m s-1)")
        if rows == 3:
            axes[2].plot(datetimes, dataset.PBLH.isel(position), marker="o", color="tab:purple")
            axes[2].set_ylabel("PBLH (m)")
        for ax in axes:
            ax.grid(alpha=.25)
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        axes[-1].set_xlabel(f"UTC on {times[0][:10]}")
        fig.suptitle(f"Surface evolution near {cell.latitude:.3f}, {cell.longitude:.3f}")
        target = output / "selected_point_timeseries.png"
        fig.tight_layout(); fig.savefig(target, dpi=180); plt.close(fig); figures.append(target)
    return figures


def create_hindcast_report(
    run_directory: str | Path,
    output_directory: str | Path,
    *,
    domain: str = "d01",
    latitude: float | None = None,
    longitude: float | None = None,
    configuration: dict[str, Any] | None = None,
) -> dict[str, Path]:
    """Create JSON, HTML and PDF reports for a time-ordered WRF hindcast."""
    if (latitude is None) != (longitude is None):
        raise ValueError("latitude and longitude must be supplied together")
    files = discover_wrfout(run_directory, domain=domain)
    if not files:
        raise FileNotFoundError(f"no wrfout files for {domain} in {Path(run_directory).resolve()}")
    output = Path(output_directory).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    with open_wrf_sequence(files) as dataset:
        validate_wrf_dataset(dataset)
        lat = dataset.XLAT.isel(Time=0)
        lon = dataset.XLONG.isel(Time=0)
        if latitude is None:
            y, x = np.array(lat.shape) // 2
            latitude, longitude = float(lat[y, x]), float(lon[y, x])
        cell = nearest_grid_point(lat, lon, float(latitude), float(longitude))
        summary = summarize_hindcast(dataset, files=files, cell=cell)
        figures = _save_figures(dataset, output, cell, summary["timestamps"])
    report = {
        "simulation": {key: summary[key] for key in ("file_count", "start_time", "end_time")},
        "grid": summary["grid"],
        "selected_point": summary["selected_point"],
        "physics": summary["physics"],
        "quality_control": summary["quality_control"],
        "surface_statistics": summary["surface_statistics"],
        "precipitation": summary.get("precipitation", {}),
        "provenance": provenance(inputs=files, configuration=configuration, software_version="wrf-tools 0.3.0"),
    }
    paths = {
        "summary": write_json_report(summary, output / "hindcast-summary.json"),
        "html": write_html_report(report, output / "hindcast-report.html", title="WRF hindcast report", figures=figures),
        "pdf": write_pdf_report(report, output / "hindcast-report.pdf", title="WRF hindcast report", figures=figures),
    }
    return paths
