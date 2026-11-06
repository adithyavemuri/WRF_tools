"""Equal-weight ensemble reporting from explicitly named, co-located WRF runs.

No automatic regridding, dropping of members, time interpolation, or skill claim.
Diagnostics are computed PER MEMBER before averaging nonlinear quantities.
"""
from contextlib import ExitStack
from pathlib import Path
import numpy as np

from .io import discover_wrfout, open_wrf_sequence
from .grid import nearest_grid_point
from .reporting import write_json_report, write_html_report, write_pdf_report
from .visualization import history_times, geographic_axis, surface_wind
from .hindcast import _domain_layout

DEFAULT_VARIABLES = ("wind_speed_10m", "T2", "PSFC", "PBLH", "HFX", "LH", "SWDOWN", "GLW", "UST", "precipitation", "model_tke_100m")


def _mean_members(values):
    """Equal-member mean; missing values propagate (no changing member counts)."""
    return np.mean(np.stack(values), axis=0)


def _validate_alignment(datasets):
    reference = datasets[0]
    for dataset in datasets[1:]:
        if history_times(reference) != history_times(dataset):
            raise ValueError("Ensemble timestamps differ; no implicit time alignment")
        for name in ("XLAT", "XLONG", "HGT"):
            if name not in reference or name not in dataset:
                raise ValueError(f"Ensemble alignment requires {name} in every member")
            if reference[name].shape != dataset[name].shape or not np.allclose(reference[name], dataset[name], rtol=0, atol=1e-6, equal_nan=False):
                raise ValueError(f"Ensemble {name} grids differ; no implicit regridding")
        for key in ("DX", "DY", "MAP_PROJ"):
            if reference.attrs.get(key) != dataset.attrs.get(key):
                raise ValueError(f"Ensemble grid metadata differs: {key}")


def _diagnostic(dataset, name):
    if name == "wind_speed_10m":
        u, v, _ = surface_wind(dataset)
        return np.hypot(u, v), "m s-1", "10 m wind speed"
    if name == "model_tke_100m":
        import xarray as xr
        from .turbulence import model_tke
        from .averaging import to_height
        from .visualization import mass_heights
        tke = model_tke(dataset).transpose("Time", "bottom_top", "south_north", "west_east")
        heights = xr.DataArray(mass_heights(dataset.PH, dataset.PHB, dataset.HGT, axis=1, agl=True), dims=tke.dims, coords=tke.coords)
        field = to_height(tke, heights, [100.], reference="AGL").squeeze("height").transpose("Time", "south_north", "west_east")
        return field.values, "m2 s-2", "Model TKE at 100 m AGL"
    if name == "precipitation":
        values = np.asarray(dataset.RAINC + dataset.RAINNC, dtype=float)
        differences = np.diff(values, axis=0)
        if not np.isfinite(values).all() or (differences < -1e-6).any():
            raise ValueError("Precipitation counter reset/nonfinite data; no automatic reconstruction")
        return values - values[:1], "mm", "Accumulated precipitation since first output"
    field = dataset[name]
    if set(field.dims) != {"Time", "south_north", "west_east"}:
        raise ValueError(f"{name}: select a surface/mass-grid scalar, not an arbitrary vertical index")
    values = np.asarray(field.transpose("Time", "south_north", "west_east"), dtype=float)
    units = field.attrs.get("units")
    if not units:
        raise ValueError(f"{name}: explicit units required")
    return values, units, field.attrs.get("description", name)


def create_ensemble_report(members, output_directory, *, report_domains=None,
                           contour_member="mean", variables=None, latitude=None, longitude=None):
    """Members and mean in every time series; maps use mean or a named member.

    Contours show history-sample means except precipitation, which shows the
    period accumulation. A mean-speed map is NOT speed of mean wind vectors.
    Native surface scalars can be selected explicitly through variables.
    """
    if len(members) < 2 or "mean" in members or any(not str(name).strip() for name in members):
        raise ValueError("Provide at least two named members; 'mean' is reserved")
    if contour_member != "mean" and contour_member not in members:
        raise ValueError("contour_member must be 'mean' or an explicitly named member")
    if (latitude is None) != (longitude is None):
        raise ValueError("Supply both latitude and longitude")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import cartopy.crs as ccrs

    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    names = list(members)
    selected_variables = tuple(variables) if variables is not None else DEFAULT_VARIABLES
    figures, records, member_records = [], {}, {}
    with ExitStack() as stack:
        datasets = {}
        domain_sets = []
        for name, directory in members.items():
            files = discover_wrfout(directory)
            domain_sets.append({path.name.split("_")[1] for path in files})
            member_records[name] = {"source_files": [path.name for path in files]}
        domains = sorted(domain_sets[0]) if report_domains is None else list(report_domains)
        if not domains or len(set(domains)) != len(domains) or any(set(domains) - available for available in domain_sets):
            raise ValueError("Every selected domain must exist in every member")
        if report_domains is None and any(available != domain_sets[0] for available in domain_sets):
            raise ValueError("Member domain sets differ; select report_domains explicitly")
        for domain in sorted(domain_sets[0]):
            reference = stack.enter_context(open_wrf_sequence(discover_wrfout(members[names[0]], domain=domain)))
            datasets[domain] = reference
        figures.append(_domain_layout(datasets, output))
        for domain in domains:
            runs = [datasets[domain]] + [stack.enter_context(open_wrf_sequence(discover_wrfout(members[name], domain=domain))) for name in names[1:]]
            _validate_alignment(runs)
            reference = runs[0]
            lat, lon = reference.XLAT.isel(Time=0), reference.XLONG.isel(Time=0)
            point_lat = float(lat.values[lat.shape[0]//2, lat.shape[1]//2]) if latitude is None else latitude
            point_lon = float(lon.values[lon.shape[0]//2, lon.shape[1]//2]) if longitude is None else longitude
            cell = nearest_grid_point(lat, lon, point_lat, point_lon)
            times = np.asarray(history_times(reference), dtype="datetime64[s]")
            records[domain] = {"site": dict(latitude=cell.latitude, longitude=cell.longitude), "timestamps": history_times(reference), "variables": {}}
            for name, run in zip(names, runs):
                member_records[name].setdefault("physics_by_domain", {})[domain] = {
                    key: run.attrs.get(key) for key in ("MP_PHYSICS", "RA_LW_PHYSICS", "RA_SW_PHYSICS", "BL_PBL_PHYSICS", "SF_SFCLAY_PHYSICS", "CU_PHYSICS")}
            for variable in selected_variables:
                needed = {"U10", "V10"} if variable == "wind_speed_10m" else {"RAINC", "RAINNC"} if variable == "precipitation" else {"PH", "PHB", "HGT"} if variable == "model_tke_100m" else {variable}
                from .turbulence import model_tke_sources, model_tke
                missing = any(not needed <= set(run) or (variable == "model_tke_100m" and not model_tke_sources(run)) for run in runs)
                if missing:
                    if variables is not None:
                        raise ValueError(f"{domain}/{variable} is missing in at least one member")
                    records[domain]["variables"][variable] = {"status": "unavailable in one or more members"}
                    continue
                if variable == "model_tke_100m" and len({model_tke(run).attrs["tke_kind"] for run in runs}) != 1:
                    raise ValueError("Do not average parameterized PBL TKE with dynamics/SGS TKE")
                fields = [_diagnostic(run, variable) for run in runs]
                if len({units for _, units, _ in fields}) != 1:
                    raise ValueError(f"{variable}: member units differ")
                units, description = fields[0][1:]
                values = [field[0] for field in fields]
                average = _mean_members(values)
                series = [value[:, cell.y, cell.x] for value in values]
                mean_series = _mean_members(series)
                selected = average if contour_member == "mean" else values[names.index(contour_member)]
                contour = selected[-1] if variable == "precipitation" else np.mean(selected, axis=0)
                # One compact page-ready figure: named member traces + thick mean,
                # paired with the explicitly selected contour source.
                fig = plt.figure(figsize=(11, 4.3), layout="constrained")
                axis = fig.add_subplot(1, 2, 1)
                for label, samples in zip(names, series):
                    axis.plot(times, samples, label=label, alpha=.8, linewidth=1.1)
                axis.plot(times, mean_series, label="Ensemble mean", color="black", linewidth=2.5, linestyle="--")
                locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
                axis.xaxis.set_major_locator(locator)
                axis.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
                axis.set(xlabel="UTC", ylabel=f"{description} [{units}]", title=f"{domain}: all {len(names)} members + mean")
                axis.grid(alpha=.2)
                axis.legend(fontsize=7, ncol=2)
                map_axis, _ = geographic_axis(fig, 122, reference)
                image = map_axis.pcolormesh(lon, lat, contour, shading="auto", transform=ccrs.PlateCarree(), cmap="viridis")
                fig.colorbar(image, ax=map_axis, shrink=.8, label=f"{description} [{units}]")
                map_axis.set_title(f"{domain}: {contour_member}\n" + ("Period accumulation" if variable == "precipitation" else "History-sample mean"), fontsize=10)
                path = output / f"{domain}_{variable}_ensemble.png"
                fig.savefig(path, dpi=170)
                plt.close(fig)
                figures.append(path)
                records[domain]["variables"][variable] = {"units": units, "status": "COMPLETE",
                    "member_series": dict(zip(names, [value.tolist() for value in series])),
                    "mean_series": mean_series.tolist(), "contour_member": contour_member}
        report = {"ensemble": {"member_count": len(names), "members": member_records,
                    "report_domains": domains, "contour_member": contour_member},
                  "results": records, "methods": {
                    "averaging": "Equal member weights. Diagnostics computed per member before mean; NaNs propagate. No silent member omission.",
                    "maps": "Mean over members at each cell/time, then unweighted mean over history samples; precipitation is final minus initial counter.",
                    "alignment": "Identical timestamps, coordinates, terrain and grid metadata required. No implicit regridding.",
                    "scope": "Model-based ensemble sensitivity, not observational skill, uncertainty calibration or annual yield.",
                    "references": "WRF ARW technical note: https://doi.org/10.5065/1dfh-6p97"}}
        return {"summary": write_json_report(report, output / "ensemble-summary.json"),
                "html": write_html_report(report, output / "ensemble-report.html", title="WRF ensemble report", figures=figures),
                "pdf": write_pdf_report(report, output / "ensemble-report.pdf", title="WRF ensemble report", figures=figures)}
