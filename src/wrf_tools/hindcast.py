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
from .maps import add_cached_features


SURFACE_VARIABLES = ("T2", "PSFC", "Q2", "U10", "V10", "PBLH", "RAINC", "RAINNC", "HFX", "LH", "SWDOWN", "GLW", "UST")


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
    qc_names = [name for name in SURFACE_VARIABLES if name in dataset]
    if "Times" in dataset:
        qc_names.append("Times")
    issues = quality_control(dataset[qc_names])
    result: dict[str, Any] = {
        "files": [Path(item).name for item in files],
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
    if {"U10", "V10"} <= set(dataset):
        speed = np.hypot(np.asarray(dataset.U10, dtype=float), np.asarray(dataset.V10, dtype=float))
        rho = np.full_like(speed, 1.225)
        if {"PSFC", "T2"} <= set(dataset):
            rho = np.asarray(dataset.PSFC, dtype=float) / (287.05 * np.asarray(dataset.T2, dtype=float))
        direction = (270.0 - np.degrees(np.arctan2(np.asarray(dataset.V10), np.asarray(dataset.U10)))) % 360.0
        direction_radians = np.radians(direction[np.isfinite(direction)])
        mean_direction = (
            float(np.degrees(np.arctan2(np.mean(np.sin(direction_radians)), np.mean(np.cos(direction_radians)))) % 360.0)
            if direction_radians.size else None
        )
        result["wind_resource"] = {
            "height_metres": 10,
            "mean_speed_m_s": float(np.nanmean(speed)),
            "maximum_speed_m_s": float(np.nanmax(speed)),
            "p50_speed_m_s": float(np.nanpercentile(speed, 50)),
            "p90_speed_m_s": float(np.nanpercentile(speed, 90)),
            "p95_speed_m_s": float(np.nanpercentile(speed, 95)),
            "mean_direction_degrees": mean_direction,
            "mean_air_density_kg_m3": float(np.nanmean(rho)),
            "mean_power_density_w_m2": float(np.nanmean(0.5 * rho * speed ** 3)),
            "scope_note": "10 m diagnostic only; not a hub-height resource assessment",
        }
    return result


def _vertical_diagnostics(dataset: Any, cell: Any, *, shear_bottom: float = 40, shear_top: float = 200) -> dict[str, Any] | None:
    required = {"PH", "PHB", "P", "PB", "T", "U", "V", "HGT"}
    if not required <= set(dataset):
        return None
    point = {"south_north": cell.y, "west_east": cell.x}
    z_stag = np.asarray((dataset.PH + dataset.PHB).isel(point), dtype=float) / 9.80665
    terrain = np.asarray(dataset.HGT.isel(Time=0, **point), dtype=float)
    height = 0.5 * (z_stag[:, :-1] + z_stag[:, 1:]) - terrain
    u = 0.5 * (np.asarray(dataset.U.isel(south_north=cell.y, west_east_stag=cell.x), dtype=float) + np.asarray(dataset.U.isel(south_north=cell.y, west_east_stag=cell.x + 1), dtype=float))
    v = 0.5 * (np.asarray(dataset.V.isel(south_north_stag=cell.y, west_east=cell.x), dtype=float) + np.asarray(dataset.V.isel(south_north_stag=cell.y + 1, west_east=cell.x), dtype=float))
    speed = np.hypot(u, v)
    pressure = np.asarray((dataset.P + dataset.PB).isel(point), dtype=float)
    theta = np.asarray(dataset.T.isel(point), dtype=float) + 300.0
    temperature = theta * (pressure / 100000.0) ** 0.2854 - 273.15
    tke = None; tke_name = None
    if "TKE_PBL" in dataset:
        tke = np.asarray(dataset.TKE_PBL.isel(point), dtype=float); tke_name = "TKE_PBL"
    elif "QKE" in dataset:
        tke = 0.5 * np.asarray(dataset.QKE.isel(point), dtype=float); tke_name = "QKE / 2"
    alpha = []
    for z_values, speed_values in zip(height, speed):
        mask = (z_values >= shear_bottom) & (z_values <= shear_top) & (speed_values > 0)
        alpha.append(float(np.polyfit(np.log(z_values[mask]), np.log(speed_values[mask]), 1)[0]) if mask.sum() >= 2 else np.nan)
    return {"height": height, "speed": speed, "temperature": temperature, "tke": tke, "tke_name": tke_name, "shear_alpha": np.asarray(alpha)}


def _save_figures(dataset: Any, output: Path, cell: Any, times: list[str], *, domain: str, vertical: dict[str, Any] | None = None, profile_top: float = 2000) -> list[Path]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import cartopy.crs as ccrs
    except ImportError as exc:
        raise ImportError("Hindcast figures require: pip install wrf-tools[plot]") from exc

    lat = np.asarray(dataset.XLAT.isel(Time=0))
    lon = np.asarray(dataset.XLONG.isel(Time=0))
    datetimes = np.asarray(times, dtype="datetime64[s]")
    figures: list[Path] = []

    def field_figure(values: Any, filename: str, title: str, label: str, cmap: str) -> None:
        projection = ccrs.PlateCarree()
        fig, ax = plt.subplots(figsize=(7.4, 5.4), subplot_kw={"projection": projection})
        add_cached_features(ax)
        mesh = ax.pcolormesh(lon, lat, np.asarray(values), shading="auto", cmap=cmap, alpha=.82, transform=projection)
        ax.scatter([cell.longitude], [cell.latitude], c="black", s=24, marker="x", label="Analysis point", transform=projection)
        ax.set_extent([float(np.nanmin(lon)),float(np.nanmax(lon)),float(np.nanmin(lat)),float(np.nanmax(lat))],crs=projection)
        grid=ax.gridlines(draw_labels=True,linewidth=.4,color="0.25",alpha=.5,linestyle="--"); grid.top_labels=False; grid.right_labels=False
        ax.set_title(title)
        ax.legend(loc="best")
        fig.colorbar(mesh, ax=ax, label=label)
        target = output / f"{domain}_{filename}"
        fig.tight_layout(); fig.savefig(target, dpi=180); plt.close(fig); figures.append(target)

    if "HGT" in dataset:
        field_figure(dataset.HGT.isel(Time=0), "domain_terrain.png", "WRF domain and terrain", "Terrain height (m)", "terrain")
    if "T2" in dataset:
        field_figure(dataset.T2.isel(Time=-1) - 273.15, "final_temperature.png", f"2 m temperature at {times[-1]} UTC", "Temperature (deg C)", "coolwarm")
    if {"U10", "V10"} <= set(dataset):
        speed = np.hypot(dataset.U10.isel(Time=-1), dataset.V10.isel(Time=-1))
        field_figure(speed, "final_wind_speed.png", f"10 m wind speed at {times[-1]} UTC", "Wind speed (m s-1)", "viridis")
        u = np.asarray(dataset.U10, dtype=float).ravel(); v = np.asarray(dataset.V10, dtype=float).ravel()
        direction = (270.0 - np.degrees(np.arctan2(v, u))) % 360.0
        bins = np.linspace(0, 360, 17); counts, _ = np.histogram(direction[np.isfinite(direction)], bins=bins)
        theta = np.deg2rad((bins[:-1] + bins[1:]) / 2); width = np.deg2rad(np.diff(bins))
        fig, ax = plt.subplots(figsize=(7.2, 6.2), subplot_kw={"projection": "polar"})
        ax.bar(theta, counts / max(counts.sum(), 1) * 100.0, width=width, color="#1976A3", edgecolor="white")
        ax.set_theta_zero_location("N"); ax.set_theta_direction(-1); ax.set_title("10 m wind-direction frequency",pad=24)
        ax.set_rlabel_position(45)
        ax.yaxis.set_major_formatter(lambda value, position: f"{value:g}%")
        target = output / f"{domain}_wind_rose.png"
        fig.tight_layout(); fig.savefig(target, dpi=180); plt.close(fig); figures.append(target)
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
        target = output / f"{domain}_selected_point_timeseries.png"
        fig.tight_layout(); fig.savefig(target, dpi=180); plt.close(fig); figures.append(target)
    if {"RAINC", "RAINNC"} <= set(dataset):
        position = {"south_north": cell.y, "west_east": cell.x}
        accumulation = np.asarray((dataset.RAINC + dataset.RAINNC).isel(position), dtype=float)
        fig, ax = plt.subplots(figsize=(8.2, 4.4)); ax.plot(datetimes, accumulation-accumulation[0], marker="o", color="#1976A3")
        ax.set(title=f"Accumulated precipitation near {cell.latitude:.3f}, {cell.longitude:.3f}",ylabel="Accumulation (mm)",xlabel=f"UTC on {times[0][:10]}")
        ax.grid(alpha=.3); ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M")); fig.tight_layout()
        target=output/f"{domain}_precipitation_timeseries.png"; fig.savefig(target,dpi=180); plt.close(fig); figures.append(target)
    if vertical is not None:
        panels = 3 if vertical["tke"] is not None else 2
        fig, axes = plt.subplots(1, panels, figsize=(4.4*panels, 6.2), sharey=True); axes=np.atleast_1d(axes)
        z=vertical["height"][-1]; axes[0].plot(vertical["speed"][-1],z,color="#1976A3"); axes[0].set(xlabel="Wind speed (m s-1)",ylabel="Height AGL (m)")
        axes[1].plot(vertical["temperature"][-1],z,color="#D95F02"); axes[1].set(xlabel="Temperature (deg C)")
        if panels==3: axes[2].plot(vertical["tke"][-1],z,color="#6A3D9A"); axes[2].set(xlabel=f"{vertical['tke_name']} (m2 s-2)")
        for ax in axes: ax.grid(alpha=.3); ax.set_ylim(0,min(profile_top,float(np.nanmax(z))))
        fig.suptitle(f"Final model-level profiles at {times[-1]} UTC"); fig.tight_layout()
        target=output/f"{domain}_vertical_profiles.png"; fig.savefig(target,dpi=180); plt.close(fig); figures.append(target)
        zmean=np.nanmean(vertical["height"],axis=0); fig,ax=plt.subplots(figsize=(8.2,5.4)); mesh=ax.pcolormesh(datetimes,zmean,vertical["speed"].T,shading="auto",cmap="viridis")
        ax.set(title="Model-level wind-speed evolution",ylabel="Height AGL (m)",xlabel=f"UTC on {times[0][:10]}",ylim=(0,min(profile_top,float(np.nanmax(zmean))))); ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M")); fig.colorbar(mesh,ax=ax,label="Wind speed (m s-1)"); fig.tight_layout()
        target=output/f"{domain}_wind_time_height.png"; fig.savefig(target,dpi=180); plt.close(fig); figures.append(target)
    return figures


def _domain_layout(datasets: dict[str, Any], output: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    projection=ccrs.PlateCarree(); fig, ax = plt.subplots(figsize=(8.4, 6.2),subplot_kw={"projection":projection})
    add_cached_features(ax)
    colours = ("#1f77b4", "#d62728", "#2ca02c", "#9467bd")
    for colour, (domain, dataset) in zip(colours, datasets.items()):
        lat = np.asarray(dataset.XLAT.isel(Time=0)); lon = np.asarray(dataset.XLONG.isel(Time=0))
        x = np.r_[lon[0, :], lon[1:, -1], lon[-1, -2::-1], lon[-2:0:-1, 0]]
        y = np.r_[lat[0, :], lat[1:, -1], lat[-1, -2::-1], lat[-2:0:-1, 0]]
        ax.plot(x, y, color=colour, linewidth=2.2, label=f"{domain}: {dataset.attrs.get('DX', 0):g} m",transform=projection)
        ax.text(float(lon[0,0]),float(lat[0,0]),domain.upper(),color=colour,weight="bold",fontsize=10,ha="left",va="bottom",transform=projection,bbox={"facecolor":"white","alpha":.8,"edgecolor":colour,"pad":2})
    all_lon=np.concatenate([np.asarray(ds.XLONG.isel(Time=0)).ravel() for ds in datasets.values()]); all_lat=np.concatenate([np.asarray(ds.XLAT.isel(Time=0)).ravel() for ds in datasets.values()])
    ax.set_extent([float(np.nanmin(all_lon))-.3,float(np.nanmax(all_lon))+.3,float(np.nanmin(all_lat))-.2,float(np.nanmax(all_lat))+.2],crs=projection)
    grid=ax.gridlines(draw_labels=True,linewidth=.4,color="0.25",alpha=.5,linestyle="--"); grid.top_labels=False; grid.right_labels=False
    ax.set_title("WRF computational domains"); ax.legend(loc="lower right"); fig.tight_layout()
    target = output / "domain_layout.png"; fig.savefig(target, dpi=200); plt.close(fig)
    return target


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
    all_files = discover_wrfout(run_directory)
    domains = sorted({item.name.split("_")[1] for item in all_files})
    if domain not in domains:
        raise FileNotFoundError(f"no wrfout files for {domain} in {Path(run_directory).resolve()}")
    output = Path(output_directory).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    case_data = (configuration or {}).get("case_configuration", {}).get("data", {})
    manifest_data = (configuration or {}).get("case_manifest", {}).get("data", {})
    effective = manifest_data.get("effective_namelist", {})
    analysis_options = case_data.get("analysis", {})
    profile_top = float(analysis_options.get("profile_top_metres", 2000))
    shear_bottom = float(analysis_options.get("shear_bottom_metres", 40))
    shear_top = float(analysis_options.get("shear_top_metres", 200))
    if profile_top <= 0:
        raise ValueError("analysis.profile_top_metres must be positive")
    if shear_bottom <= 0 or shear_top <= shear_bottom:
        raise ValueError("analysis shear heights must be positive and shear_top_metres must exceed shear_bottom_metres")
    summaries: dict[str, Any] = {}; figures: list[Path] = []; opened: dict[str, Any] = {}
    try:
        for domain_name in domains:
            files = discover_wrfout(run_directory, domain=domain_name)
            dataset = open_wrf_sequence(files); opened[domain_name] = dataset
            validate_wrf_dataset(dataset)
            lat = dataset.XLAT.isel(Time=0); lon = dataset.XLONG.isel(Time=0)
            point_lat, point_lon = latitude, longitude
            if point_lat is None:
                y, x = np.array(lat.shape) // 2
                point_lat, point_lon = float(lat[y, x]), float(lon[y, x])
            cell = nearest_grid_point(lat, lon, float(point_lat), float(point_lon))
            summaries[domain_name] = summarize_hindcast(dataset, files=files, cell=cell)
            vertical = _vertical_diagnostics(dataset, cell, shear_bottom=shear_bottom, shear_top=shear_top)
            if vertical is not None:
                alpha=vertical["shear_alpha"]
                summaries[domain_name]["vertical_diagnostics"]={"profile_height_limit_metres":profile_top,"shear_fit_layer_metres":[shear_bottom,shear_top],"mean_shear_exponent":float(np.nanmean(alpha)) if np.isfinite(alpha).any() else None,"tke_variable":vertical["tke_name"],"tke_status":"available" if vertical["tke"] is not None else "not present for this physics/output configuration"}
            figures.extend(_save_figures(dataset, output, cell, summaries[domain_name]["timestamps"], domain=domain_name, vertical=vertical, profile_top=profile_top))
        figures.insert(0, _domain_layout(opened, output))
    finally:
        for dataset in opened.values(): dataset.close()
    selected = summaries[domain]
    domain_records = manifest_data.get("domain", {}).get("domains", [])
    workflow_state = (configuration or {}).get("workflow_state", {}).get("data", {})
    wrf_stage = workflow_state.get("stages", {}).get("wrf", {})
    outer_dt = effective.get("domains", {}).get("time_step")
    temporal_domains = {}
    for item in domain_records:
        ratio = 1
        current = item
        while int(current.get("domain_id", 1)) > 1:
            ratio *= int(current.get("parent_time_step_ratio", 1))
            current = domain_records[int(current.get("parent_id", 1)) - 1]
        temporal_domains[f"d{int(item.get('domain_id', 1)):02d}"] = outer_dt / ratio if outer_dt else None
    report = {
        "overview": {"analysis_domain": domain, "domain_count": len(domains), "file_count_per_domain": selected["file_count"], "start_time": selected["start_time"], "end_time": selected["end_time"], "forcing_interval_seconds": case_data.get("case", {}).get("interval_seconds", 3600), "history_interval_minutes": effective.get("time_control", {}).get("history_interval"), "domain_time_steps_seconds": temporal_domains, "restart_interval_minutes": effective.get("time_control", {}).get("restart_interval"), "resumed_from": wrf_stage.get("resumed_from")},
        "domains": summaries,
        "provenance": provenance(inputs=all_files, configuration=configuration, software_version="wrf-tools 0.4.0"),
    }
    paths = {
        "summary": write_json_report(report, output / "hindcast-summary.json"),
        "html": write_html_report(report, output / "hindcast-report.html", title="WRF hindcast report", figures=figures),
        "pdf": write_pdf_report(report, output / "hindcast-report.pdf", title="WRF hindcast report", figures=figures),
    }
    return paths
