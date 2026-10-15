"""Model-written TKE, kept separate from resolved velocity-variance statistics."""
from __future__ import annotations

import numpy as np

from .grid import destagger

TKE_METHOD = "https://github.com/wrf-model/WRF/blob/v4.7.1/Registry/Registry.EM_COMMON"


def model_tke_sources(dataset):
    """List supported native fields; do not infer energy from a variable substring."""
    lookup = {name.upper(): name for name in dataset.data_vars}
    return [lookup[name] for name in ("QKE", "TKE_PBL", "TKE") if name in lookup]


def model_tke(dataset, *, source=None, indexers=None):
    """Return mass-grid model TKE with units/conversion/source provenance.

    QKE is twice MYNN TKE and is divided by two. TKE_PBL and dynamics TKE
    are used directly, NEVER added together or labelled resolved/total TKE.
    Auto prefers QKE, then TKE_PBL, then TKE; select explicitly if several
    fields exist. Standard WRF names/conventions only. Native vertical
    interface values are averaged onto adjacent mass levels. Negative values
    are preserved for diagnosis. Selection occurs before loading/destaggering.
    """
    sources = model_tke_sources(dataset)
    if source is None:
        if not sources:
            raise LookupError("No supported model TKE field: expected QKE, TKE_PBL or TKE")
        source = sources[0]
    else:
        source = next((name for name in sources if name.upper() == source.upper()), None)
        if source is None:
            raise ValueError("Requested TKE source is unavailable or unsupported")
    data = dataset[source]
    if indexers:
        data = data.isel({name: index for name, index in indexers.items() if name in data.dims})
    units = str(data.attrs.get("units", "")).lower().replace(" ", "").replace("**", "").replace("^", "")
    if units and units not in {"m2s-2", "m2/s2", "m²s⁻²"}:
        raise ValueError(f"{source}: expected specific energy units m2 s-2, got {data.attrs.get('units')}")
    if "bottom_top_stag" in data.dims:
        data = destagger(data, "bottom_top_stag")
    if "bottom_top" not in data.dims or any(name.endswith("_stag") for name in data.dims):
        raise ValueError(f"{source}: expected a WRF mass-grid or vertically staggered 3-D TKE field")
    factor = .5 if source.upper() == "QKE" else 1.
    result = data * factor
    result.name = "model_tke"
    result.attrs = dict(data.attrs, units="m2 s-2", long_name="Model-provided turbulence kinetic energy",
        source_variable=source, conversion_factor=factor,
        tke_kind="model SGS/dynamics" if source.upper() == "TKE" else "parameterized PBL",
        vertical_processing="adjacent interface averaging" if "bottom_top_stag" in dataset[source].dims else "native mass levels",
        method_reference=TKE_METHOD,
        warning="Not resolved or total TKE; high energy alone does not establish spurious production")
    return result


def tke_diagnostics_data(dataset, cell, *, source=None):
    """Read site columns and framewise domain reductions, not a full 4-D cube."""
    from .visualization import history_times, mass_heights
    times = history_times(dataset)
    point = {"south_north": cell.y, "west_east": cell.x}
    site = model_tke(dataset, source=source, indexers=point)
    z = mass_heights(dataset.PH.isel(point), dataset.PHB.isel(point), dataset.HGT.isel(point), axis=1, agl=True)
    maxima, means, negative, missing, minimum = [], [], 0, 0, np.inf
    final = None
    for index in range(len(times)):
        frame = model_tke(dataset, source=site.attrs["source_variable"], indexers={"Time": index})
        values = np.asarray(frame.transpose("bottom_top", "south_north", "west_east"), float)
        finite = np.isfinite(values)
        if finite.any():
            minimum = min(minimum, float(values[finite].min()))
        count = finite.sum(axis=(1, 2))
        maxima.append(np.where(finite, values, -np.inf).max(axis=(1, 2)))
        maxima[-1][count == 0] = np.nan
        means.append(np.divide(np.where(finite, values, 0).sum(axis=(1, 2)), count,
                               out=np.full(len(count), np.nan), where=count > 0))
        negative += int((values < 0).sum()); missing += int((~finite).sum())
        final = values
    if site.shape != z.shape:
        raise ValueError("TKE and physical mass-level heights do not match")
    return dict(times=times, site=np.asarray(site), heights=z, final_lowest=final[0],
        maxima=np.array(maxima), means=np.array(means), metadata=dict(site.attrs),
        negative_count=negative, nonfinite_count=missing, minimum=minimum)


def save_tke_diagnostics(dataset, cell, prefix, *, source=None, top=2000, sources=(), formats=("png","pdf","svg")):
    """Save a geographic map, site profiles, physical-height evolution and
    time/native-level domain maxima, plus a JSON methods/statistics record.
    PNG is required; select optional PDF/SVG with formats. Complete reports
    request PNG/SVG only to avoid duplicate PDF documents.
    """
    import json
    from pathlib import Path
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.colors import Normalize
    import cartopy.crs as ccrs
    from .visualization import geographic_axis, interpolate_columns
    formats=tuple(formats)
    if "png" not in formats or any(name not in {"png","pdf","svg"} for name in formats):
        raise ValueError("formats must include png and optionally pdf/svg")
    data = tke_diagnostics_data(dataset, cell, source=source)
    finite = np.concatenate([data[key].ravel() for key in ("site", "final_lowest", "maxima")])
    finite = finite[np.isfinite(finite)]
    if not finite.size:
        raise ValueError("No finite TKE values to plot")
    lower, upper = min(0., data["minimum"]), max(.01, float(finite.max()))
    norm = Normalize(lower, upper)
    cmap = "coolwarm" if lower < 0 else "magma"
    times = np.array(data["times"], dtype="datetime64[s]")
    dates = mdates.date2num(times)
    levels = np.linspace(0, top, 101)
    regular = interpolate_columns(data["site"], data["heights"], levels)
    fig = plt.figure(figsize=(13.5, 9.4))
    grid = fig.add_gridspec(2, 2, left=.08, right=.94, top=.85, bottom=.17, wspace=.35, hspace=.45)
    source_name = data["metadata"]["source_variable"]
    fig.text(.08, .95, f"MODEL TKE | {source_name} | {data['metadata']['tke_kind']}", fontsize=17, weight="bold")
    ax, geography = geographic_axis(fig, grid[0, 0], dataset)
    image = ax.pcolormesh(dataset.XLONG.isel(Time=0), dataset.XLAT.isel(Time=0), data["final_lowest"],
        transform=ccrs.PlateCarree(), shading="auto", cmap=cmap, norm=norm, rasterized=True)
    ax.set_title("A | Final lowest mass level (not a fixed AGL height)")
    fig.colorbar(image, ax=ax, label="TKE (m²/s²)", shrink=.85)
    ax = fig.add_subplot(grid[0, 1])
    for index in sorted({0, len(times)//2, len(times)-1}):
        visible = data["heights"][index] <= top
        ax.plot(data["site"][index, visible], data["heights"][index, visible], label=data["times"][index][11:16])
    ax.set(xlabel="TKE (m²/s²)", ylabel="Height AGL (m)", ylim=(0, top), title="B | Site profiles")
    ax.legend(title="UTC", fontsize=8); ax.grid(alpha=.2)
    for slot, values, y, label, title in (
        (grid[1, 0], regular.T, levels, "Height AGL (m)", "C | Site TKE at physical heights"),
        (grid[1, 1], data["maxima"].T, np.arange(data["maxima"].shape[1]), "Native mass-level index", "D | Domain maximum at each native level"),
    ):
        ax = fig.add_subplot(slot)
        image = ax.pcolormesh(dates, y, values, shading="auto", cmap=cmap, norm=norm, rasterized=True)
        locator = mdates.AutoDateLocator(minticks=3, maxticks=6)
        ax.xaxis.set_major_locator(locator); ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        ax.set(xlabel="Saved history time (UTC)", ylabel=label, title=title)
        fig.colorbar(image, ax=ax, label="TKE (m²/s²)")
    fig.text(.08, .045, f"{data['times'][0]} to {data['times'][-1]} UTC. Shared colour scale; negative samples: {data['negative_count']}.\n"
        "Model-written TKE only. No hourly-variance surrogate, energy-budget closure or automatic instability diagnosis.\n"
        "Physical-height interpolation: each time independently, no extrapolation. Domain levels are indexes, not common heights.", fontsize=8)
    prefix = Path(prefix); prefix.parent.mkdir(parents=True, exist_ok=True)
    try:
        for extension in formats:
            fig.savefig(prefix.with_suffix("."+extension), dpi=180)
    finally:
        plt.close(fig)
    summary = dict(status="available", source_variable=source_name, kind=data["metadata"]["tke_kind"],
        conversion_factor=data["metadata"]["conversion_factor"], units="m2 s-2", method_reference=TKE_METHOD,
        vertical_processing=data["metadata"]["vertical_processing"], negative_count=data["negative_count"],
        nonfinite_count=data["nonfinite_count"], minimum=data["minimum"], maximum=float(finite.max()),
        timestamps_utc=data["times"], source_files=[Path(item).name for item in sources],
        domain_mean_by_native_level=np.where(np.isfinite(data["means"]), data["means"], None).tolist(),
        domain_maximum_by_native_level=np.where(np.isfinite(data["maxima"]), data["maxima"], None).tolist(), geography_available=geography,
        warning="Elevated TKE is not proof of numerical energy injection; production/dissipation/transport tendencies are needed")
    prefix.with_suffix(".json").write_text(json.dumps(summary, indent=2)+"\n")
    return prefix.with_suffix(".png"), summary
