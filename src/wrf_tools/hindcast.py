"""Focused reporting for time-ordered, mesoscale WRF hindcasts."""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

from . import __version__
from .grid import nearest_grid_point
from .diagnostics import precipitation_diagnostics
from .io import discover_wrfout, open_wrf_sequence, validate_wrf_dataset
from .quality import quality_control
from .reporting import provenance, write_html_report, write_json_report, write_pdf_report
from .maps import add_cached_features
from .turbulence import model_tke_sources, model_tke, save_tke_diagnostics
from .visualization import REFERENCES, history_times, surface_wind, mass_heights, temperature_celsius, save_wind_overview


SURFACE_VARIABLES = ("T2", "PSFC", "Q2", "U10", "V10", "PBLH", "RAINC", "RAINNC", "HFX", "LH", "SWDOWN", "GLW", "UST")


def _serial(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.datetime64):
        return str(value.astype("datetime64[s]"))
    return value


def _timestamps(dataset: Any) -> list[str]:
    return history_times(dataset)


def summarize_hindcast(dataset: Any, *, files: Iterable[Path], cell: Any) -> dict[str, Any]:
    """Return JSON-safe, deterministic summary statistics for a WRF sequence."""
    times = _timestamps(dataset)
    files=list(files)
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
        "file_count": len(files),
        "sample_count": len(times),
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
            "integration_timestep_seconds": _serial(dataset.attrs.get("DT")),
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
        rainfall = precipitation_diagnostics(dataset.RAINC,dataset.RAINNC)
        total = rainfall["total"]
        finite = np.isfinite(total)
        result["precipitation"] = {
            "status": "COMPLETE" if finite.all() else ("PARTIAL" if finite.any() else "UNAVAILABLE"),
            "domain_mean_accumulation_mm": float(total[finite].mean()) if finite.any() else np.nan,
            "domain_maximum_accumulation_mm": float(total[finite].max()) if finite.any() else np.nan,
            "selected_point_accumulation_mm": float(total[cell.y, cell.x]),
            "valid_cell_fraction": float(finite.mean()),
            "reset_cell_count": int(np.count_nonzero(rainfall["reset_detected"])),
            "missing_cell_count": int(np.count_nonzero(rainfall["missing_detected"])),
            "note": "Cells with any counter reset or nonfinite sample are excluded; means/maxima describe valid cells only. Bucket/restart reconstruction is not supplied.",
        }
    if {"U10", "V10"} <= set(dataset):
        speed = np.hypot(np.asarray(dataset.U10, dtype=float), np.asarray(dataset.V10, dtype=float))
        rho = np.full_like(speed, 1.225)
        if {"PSFC", "T2"} <= set(dataset):
            rho = np.asarray(dataset.PSFC, dtype=float) / (287.05 * np.asarray(dataset.T2, dtype=float))
        east, north, coordinate_reference = surface_wind(dataset)
        direction = (270.0 - np.degrees(np.arctan2(north, east))) % 360.0
        direction[np.hypot(east, north) < 1e-6] = np.nan
        direction_radians = np.radians(direction[np.isfinite(direction)])
        mean_direction = (
            float(np.degrees(np.arctan2(np.mean(np.sin(direction_radians)), np.mean(np.cos(direction_radians)))) % 360.0)
            if direction_radians.size else None
        )
        if direction_radians.size and np.hypot(np.mean(np.sin(direction_radians)), np.mean(np.cos(direction_radians))) < 1e-12:
            mean_direction = None  # opposing directions have no defined circular mean
        result["wind_resource"] = {
            "height_metres": 10,
            "mean_speed_m_s": float(np.nanmean(speed)),
            "maximum_speed_m_s": float(np.nanmax(speed)),
            "p50_speed_m_s": float(np.nanpercentile(speed, 50)),
            "p90_speed_m_s": float(np.nanpercentile(speed, 90)),
            "p95_speed_m_s": float(np.nanpercentile(speed, 95)),
            "mean_direction_degrees": mean_direction,
            "direction_reference": coordinate_reference,
            "mean_air_density_kg_m3": float(np.nanmean(rho)),
            "mean_power_density_w_m2": float(np.nanmean(0.5 * rho * speed ** 3)),
            "scope_note": "10 m diagnostic only; not a hub-height resource assessment",
        }
    return result


def _vertical_diagnostics(dataset: Any, cell: Any, *, shear_bottom: float = 40, shear_top: float = 200, tke_source=None) -> dict[str, Any] | None:
    required = {"PH", "PHB", "P", "PB", "T", "U", "V", "HGT"}
    if any(name not in dataset for name in required):
        return None
    point = {"south_north": cell.y, "west_east": cell.x}
    height = mass_heights(dataset.PH.isel(point), dataset.PHB.isel(point),
                          dataset.HGT.isel(point), axis=1, agl=True)
    u = 0.5 * (np.asarray(dataset.U.isel(south_north=cell.y, west_east_stag=cell.x), dtype=float) + np.asarray(dataset.U.isel(south_north=cell.y, west_east_stag=cell.x + 1), dtype=float))
    v = 0.5 * (np.asarray(dataset.V.isel(south_north_stag=cell.y, west_east=cell.x), dtype=float) + np.asarray(dataset.V.isel(south_north_stag=cell.y + 1, west_east=cell.x), dtype=float))
    speed = np.hypot(u, v)
    pressure = np.asarray((dataset.P + dataset.PB).isel(point), dtype=float)
    temperature = temperature_celsius(dataset.T.isel(point), pressure)
    tke = None; tke_name = None
    if model_tke_sources(dataset):
        energy = model_tke(dataset, source=tke_source, indexers=point)
        tke = np.asarray(energy, dtype=float)
        tke_name = energy.attrs["source_variable"] + (" / 2" if energy.attrs["conversion_factor"] == .5 else "")
    alpha = []
    for z_values, speed_values in zip(height, speed):
        mask = (z_values >= shear_bottom) & (z_values <= shear_top) & (speed_values > 0)
        alpha.append(float(np.polyfit(np.log(z_values[mask]), np.log(speed_values[mask]), 1)[0]) if mask.sum() >= 2 else np.nan)
    return {"height": height, "speed": speed, "temperature": temperature, "tke": tke, "tke_name": tke_name, "shear_alpha": np.asarray(alpha)}


def _save_figures(dataset: Any, output: Path, cell: Any, times: list[str], *, domain: str, vertical: dict[str, Any] | None = None, profile_top: float = 2000, overview: bool = False) -> list[Path]:
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
        mesh = ax.pcolormesh(lon, lat, np.asarray(values), shading="auto", cmap=cmap, alpha=.82, transform=projection)
        ax.scatter([cell.longitude], [cell.latitude], c="black", s=24, marker="x", label="Analysis point", transform=projection)
        ax.set_extent([float(np.nanmin(lon)),float(np.nanmax(lon)),float(np.nanmin(lat)),float(np.nanmax(lat))],crs=projection)
        add_cached_features(ax)
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
        if not overview:
            field_figure(speed, "final_wind_speed.png", f"10 m wind speed at {times[-1]} UTC", "Wind speed (m s-1)", "viridis")
        u, v, wind_reference = surface_wind(dataset)
        u, v = u.ravel(), v.ravel()
        direction = (270.0 - np.degrees(np.arctan2(v, u))) % 360.0
        direction[np.hypot(u, v) < 1e-6] = np.nan
        bins = np.linspace(0, 360, 17); counts, _ = np.histogram(direction[np.isfinite(direction)], bins=bins)
        theta = np.deg2rad((bins[:-1] + bins[1:]) / 2); width = np.deg2rad(np.diff(bins))
        fig, ax = plt.subplots(figsize=(7.2, 6.2), subplot_kw={"projection": "polar"})
        ax.bar(theta, counts / max(counts.sum(), 1) * 100.0, width=width, color="#1976A3", edgecolor="white")
        ax.set_theta_zero_location("N"); ax.set_theta_direction(-1); ax.set_title(f"10 m wind-direction frequency\n{wind_reference}",pad=24)
        ax.set_rlabel_position(45)
        ax.yaxis.set_major_formatter(lambda value, position: f"{value:g}%")
        target = output / f"{domain}_wind_rose.png"
        fig.tight_layout(); fig.savefig(target, dpi=180); plt.close(fig); figures.append(target)
    if {"RAINC", "RAINNC"} <= set(dataset):
        rain = precipitation_diagnostics(dataset.RAINC,dataset.RAINNC)["total"]
        field_figure(rain, "accumulated_precipitation.png", "Accumulated precipitation (reset/missing cells masked)", "Precipitation (mm)", "Blues")

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
        rainfall = precipitation_diagnostics(dataset.RAINC.isel(position),dataset.RAINNC.isel(position))
        fig, ax = plt.subplots(figsize=(8.2, 4.4)); ax.plot(datetimes, accumulation-accumulation[0], marker="o", color="#1976A3")
        ax.set(title=f"Accumulated precipitation near {cell.latitude:.3f}, {cell.longitude:.3f}",ylabel="Accumulation (mm)",xlabel=f"UTC on {times[0][:10]}")
        if rainfall["missing_detected"] or rainfall["reset_detected"]:
            ax.set_title("Rainfall counter change: reset/missing samples; NOT a valid accumulation")
            ax.set_ylabel("Counter change from first sample (mm)")
        ax.grid(alpha=.3); ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M")); fig.tight_layout()
        target=output/f"{domain}_precipitation_timeseries.png"; fig.savefig(target,dpi=180); plt.close(fig); figures.append(target)
    if vertical is not None:
        panels = 3 if vertical["tke"] is not None else 2
        fig, axes = plt.subplots(1, panels, figsize=(4.4*panels, 6.2), sharey=True); axes=np.atleast_1d(axes)
        z=vertical["height"][-1]
        visible=(z>=0)&(z<=profile_top)
        axes[0].plot(vertical["speed"][-1][visible],z[visible],color="#1976A3"); axes[0].set(xlabel="Wind speed (m s-1)",ylabel="Height AGL (m)")
        axes[1].plot(vertical["temperature"][-1][visible],z[visible],color="#D95F02"); axes[1].set(xlabel="Temperature (deg C)")
        if panels==3: axes[2].plot(vertical["tke"][-1][visible],z[visible],color="#6A3D9A"); axes[2].set(xlabel=f"{vertical['tke_name']} (m2 s-2)")
        for ax in axes: ax.grid(alpha=.3); ax.set_ylim(0,min(profile_top,float(np.nanmax(z))))
        fig.suptitle(f"Final model-level profiles at {times[-1]} UTC"); fig.tight_layout()
        target=output/f"{domain}_vertical_profiles.png"; fig.savefig(target,dpi=180); plt.close(fig); figures.append(target)
        # The overview replaces the old time-height plot. Each time is vertically
        # interpolated independently instead of assigning a time-mean height grid.
    return figures


def _domain_layout(datasets: dict[str, Any], output: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    projection=ccrs.PlateCarree(); fig, ax = plt.subplots(figsize=(8.4, 6.2),subplot_kw={"projection":projection})
    colours = ("#1f77b4", "#d62728", "#2ca02c", "#9467bd")
    from itertools import cycle
    for colour, (domain, dataset) in zip(cycle(colours), datasets.items()):
        lat = np.asarray(dataset.XLAT.isel(Time=0)); lon = np.asarray(dataset.XLONG.isel(Time=0))
        x = np.r_[lon[0, :], lon[1:, -1], lon[-1, -2::-1], lon[-2:0:-1, 0]]
        y = np.r_[lat[0, :], lat[1:, -1], lat[-1, -2::-1], lat[-2:0:-1, 0]]
        ax.plot(x, y, color=colour, linewidth=2.2, label=f"{domain}: {dataset.attrs.get('DX', 0):g} m",transform=projection)
        ax.text(float(lon[0,0]),float(lat[0,0]),domain.upper(),color=colour,weight="bold",fontsize=10,ha="left",va="bottom",transform=projection,bbox={"facecolor":"white","alpha":.8,"edgecolor":colour,"pad":2})
    all_lon=np.concatenate([np.asarray(ds.XLONG.isel(Time=0)).ravel() for ds in datasets.values()]); all_lat=np.concatenate([np.asarray(ds.XLAT.isel(Time=0)).ravel() for ds in datasets.values()])
    ax.set_extent([float(np.nanmin(all_lon))-.3,float(np.nanmax(all_lon))+.3,float(np.nanmin(all_lat))-.2,float(np.nanmax(all_lat))+.2],crs=projection)
    add_cached_features(ax)
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
    tke_variable: str | None = None,
    diagnostic_groups: str | list[str] = "all",
    diagnostic_options: dict[str, Any] | None = None,
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
            sources = model_tke_sources(dataset)
            if sources:
                image, energy_summary = save_tke_diagnostics(dataset, cell, output / f"{domain_name}_tke_diagnostics",
                    source=tke_variable, top=profile_top, sources=files,formats=("png","svg"))
                energy_summary["available_sources"] = sources
                energy_summary["source_files"] = [item.name for item in files]
                figures.append(image)
                summaries[domain_name]["turbulence"] = energy_summary
            elif tke_variable is not None:
                raise ValueError(f"{domain_name}: requested TKE field {tke_variable} is not available")
            else:
                summaries[domain_name]["turbulence"] = dict(status="unavailable", source_variable=None,
                    reason="No supported QKE, TKE_PBL or TKE in this output. No resolved TKE inferred from hourly samples.",
                    bl_pbl_physics=_serial(dataset.attrs.get("BL_PBL_PHYSICS")),
                    km_opt=_serial(dataset.attrs.get("KM_OPT")))
            vertical = _vertical_diagnostics(dataset, cell, shear_bottom=shear_bottom, shear_top=shear_top, tke_source=tke_variable)
            if vertical is not None:
                alpha=vertical["shear_alpha"]
                summaries[domain_name]["vertical_diagnostics"]={"profile_height_limit_metres":profile_top,"shear_fit_layer_metres":[shear_bottom,shear_top],"mean_shear_exponent":float(np.nanmean(alpha)) if np.isfinite(alpha).any() else None,"tke_variable":vertical["tke_name"],"tke_status":"available" if vertical["tke"] is not None else "not present for this physics/output configuration"}
            overview = False
            if {"U10", "V10", "U", "V", "PH", "PHB", "HGT"} <= set(dataset):
                paths, metadata = save_wind_overview(dataset, cell, output / f"{domain_name}_wind_overview",
                    sources=files, domain=domain_name, top=profile_top,formats=("png","svg"))
                figures.append(paths["png"])
                summaries[domain_name]["figure_methods"] = metadata
                overview = True
            else:
                summaries[domain_name]["figure_methods"] = {"status": "overview unavailable",
                    "reason": "Required three-dimensional wind/height or surface wind fields are missing"}
            figures.extend(_save_figures(dataset, output, cell, summaries[domain_name]["timestamps"], domain=domain_name, vertical=vertical, profile_top=profile_top, overview=overview))
            from .diagnostic_groups import run_diagnostic_groups
            connected = run_diagnostic_groups(dataset, cell, output, domain=domain_name,
                groups=diagnostic_groups, options={"profile_top_metres":profile_top, **(diagnostic_options or {})})
            summaries[domain_name]["connected_diagnostics"] = connected
            figures.extend(output / record["figure"] for record in connected.values() if record["status"] == "COMPLETE")
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
    from .diagnostic_groups import DIAGNOSTIC_REFERENCES
    if not temporal_domains:
        temporal_domains={name:record["grid"]["integration_timestep_seconds"] for name,record in summaries.items()}
    history_interval=effective.get("time_control", {}).get("history_interval")
    if history_interval is None and len(selected["timestamps"])>1:
        delta=np.diff(np.array(selected["timestamps"],dtype="datetime64[s]").astype("int64"))
        history_interval=float(delta[0]/60) if np.all(delta==delta[0]) else "irregular (see actual timestamps)"
    report = {
        "overview": {"analysis_domain": domain, "domain_count": len(domains), "file_count_per_domain": selected["file_count"], "start_time": selected["start_time"], "end_time": selected["end_time"], "forcing_interval_seconds": case_data.get("case", {}).get("interval_seconds"), "history_interval_minutes": history_interval, "domain_time_steps_seconds": temporal_domains, "restart_interval_minutes": effective.get("time_control", {}).get("restart_interval"), "resumed_from": wrf_stage.get("resumed_from")},
        "domains": summaries,
        "scientific_methods": {
            "references": {**REFERENCES, **DIAGNOSTIC_REFERENCES},
            "definitions": {
                "wind_direction": "Meteorological direction FROM; circular mean, excluding calm samples (<1e-6 m/s). Earth-relative when rotation fields exist, otherwise explicitly grid-relative.",
                "wind_percentiles": "Sample wind-speed percentiles; not energy-yield P50/P90 exceedance estimates.",
                "summary_averaging": "Unweighted grid-cell and history-sample statistics, not an area-weighted or time-weighted climatology.",
                "temperature": "(T+300)*((P+PB)/100000)**(2/7) - 273.15 deg C; WRF dry Rd=287, cp=7*Rd/2, theta0=300 K. The perturbation dry-theta convention must match the supplied WRF output.",
                "screening_air_density": "PSFC/(287.05*T2), when available; otherwise 1.225 kg/m3. This is an approximate dry-air 10 m screening proxy, not a moist model-level density diagnostic.",
                "tke": "Model-written QKE/2 (MYNN), TKE_PBL directly, or dynamics TKE directly, selected individually, never summed. Interface values are averaged to mass levels when needed. Negative samples are retained. Not resolved/total TKE or proof of spurious energy production. A closed budget requires saved production, dissipation and transport tendencies.",
                "shear": "Least-squares log(speed) versus log(height AGL), using positive speeds within the configured layer; a diagnostic power-law fit.",
                "precipitation": "Counter differences of RAINC+RAINNC. Any reset or nonfinite sample masks that cell's period total; valid-cell fraction and affected counts are reported. Bucket/restart reconstruction is not supplied. Affected site time series retain the raw counter change with a warning.",
            },
            "scope": "Methods describe output processing. Numerical checks do not establish atmospheric accuracy; no observation-based validation is performed.",
        },
        "provenance": provenance(inputs=all_files, configuration=configuration, software_version=f"wrf-tools {__version__}"),
    }
    paths = {
        "summary": write_json_report(report, output / "hindcast-summary.json"),
        "html": write_html_report(report, output / "hindcast-report.html", title="WRF hindcast report", figures=figures),
        "pdf": write_pdf_report(report, output / "hindcast-report.pdf", title="WRF hindcast report", figures=figures),
    }
    return paths
