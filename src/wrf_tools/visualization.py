"""Traceable WRF wind figures with explicit grid and height conventions.

Numerical conventions follow the WRF-ARW v4 Technical Note
(doi:10.5065/1dfh-6p97) and WRF-Python's documented ``uvmet``, ``height``
and ``destagger`` conventions. This module verifies/visualizes model output;
it does not validate the simulated atmosphere against observations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .grid import destagger

GRAVITY = 9.81  # WRF module_model_constants.F, m s-2
REFERENCES = {
    "wrf": {"title": "Skamarock et al. (2019), A Description of the Advanced Research WRF Model Version 4",
            "url": "https://doi.org/10.5065/1dfh-6p97"},
    "wind": {"title": "WRF-Python: earth-relative wind components (uvmet)",
             "url": "https://wrf-python.readthedocs.io/en/latest/user_api/generated/wrf.uvmet.html"},
    "grid": {"title": "WRF-Python: diagnostic and height conventions",
             "url": "https://wrf-python.readthedocs.io/en/latest/user_api/generated/wrf.getvar.html"},
    "constants": {"title": "WRF v4.7.1 module_model_constants.F: gravity, reference temperature and dry-air constants",
                  "url": "https://github.com/wrf-model/WRF/blob/v4.7.1/share/module_model_constants.F"},
    "colour": {"title": "Crameri, Shephard and Heron (2020), The misuse of colour in science communication",
               "url": "https://doi.org/10.1038/s41467-020-19160-7"},
}


def history_times(dataset: Any) -> list[str]:
    """Read authoritative WRF Times, rejecting missing or overlapping samples."""
    if "Times" in dataset:
        raw = np.asarray(dataset.Times)
        if raw.ndim == 2:
            values = [(b"".join(row).decode() if raw.dtype.kind == "S" else "".join(row)).strip()
                      for row in raw]
        else:
            values = [v.decode().strip() if isinstance(v, (bytes, np.bytes_)) else str(v).strip() for v in raw]
        result = [value.replace("_", "T", 1) for value in values]
    elif "XTIME" in dataset and np.issubdtype(dataset.XTIME.dtype, np.datetime64):
        result = [str(value.astype("datetime64[s]")) for value in np.asarray(dataset.XTIME)]
    else:
        raise ValueError("A WRF Times variable or decoded datetime XTIME is required")
    stamps = np.asarray(result, dtype="datetime64[s]")
    if not stamps.size or np.isnat(stamps).any() or np.any(np.diff(stamps.astype("int64")) <= 0):
        raise ValueError("WRF history times must be non-empty, valid, unique and increasing")
    return result


def rotate_wind(u: Any, v: Any, cosine: Any, sine: Any) -> tuple[np.ndarray, np.ndarray]:
    """Rotate co-located grid winds to east/north; inputs are in m s-1.

    east = u*cos(alpha) - v*sin(alpha)
    north = v*cos(alpha) + u*sin(alpha)
    """
    u, v, cosine, sine = np.broadcast_arrays(*[np.asarray(value, float) for value in (u, v, cosine, sine)])
    if not np.isfinite(cosine).all() or not np.isfinite(sine).all():
        raise ValueError("Wind-rotation fields contain non-finite values")
    if not np.allclose(cosine**2 + sine**2, 1.0, atol=2e-4):
        raise ValueError("COSALPHA/SINALPHA do not define a unit rotation")
    return u * cosine - v * sine, v * cosine + u * sine


def surface_wind(dataset: Any, time: int | None = None):
    """Return vectors and an explicit coordinate label; never assume zero rotation."""
    fields = [dataset[name] for name in ("U10", "V10")]
    if time is not None:
        fields = [field.isel(Time=time) if "Time" in field.dims else field for field in fields]
    u, v = [np.asarray(field, float) for field in fields]
    if all(name in dataset for name in ("COSALPHA", "SINALPHA")):
        angles = [dataset[name] for name in ("COSALPHA", "SINALPHA")]
        if time is not None:
            angles = [field.isel(Time=time) if "Time" in field.dims else field for field in angles]
        u, v = rotate_wind(u, v, *angles)
        return u, v, "earth-relative"
    return u, v, "grid-relative; COSALPHA/SINALPHA unavailable"


def mass_heights(ph: Any, phb: Any, terrain: Any = 0.0, *, axis: int = 0, agl: bool = False):
    """Average staggered (PH+PHB)/g to mass levels; optionally subtract terrain."""
    height = destagger((np.asarray(ph, float) + np.asarray(phb, float)) / GRAVITY, axis)
    if agl:
        ground = np.asarray(terrain, float)
        if ground.ndim == height.ndim - 1:
            ground = np.expand_dims(ground, axis=axis)
        height = height - ground
    return height


def temperature_celsius(theta_perturbation: Any, pressure: Any):
    """Dry-theta conversion using WRF theta0=300 K and Rd/cp=2/7.

    ``pressure`` is full P+PB in Pa. This assumes T represents perturbation
    dry potential temperature, as in the standard WRF history convention.
    """
    theta, pressure = np.broadcast_arrays(np.asarray(theta_perturbation, float) + 300,
                                          np.asarray(pressure, float))
    if np.any(pressure <= 0):
        raise ValueError("Full pressure must be positive")
    return theta * (pressure / 100000.0) ** (2.0 / 7.0) - 273.15


def interpolate_columns(values: Any, heights: Any, targets: Any) -> np.ndarray:
    """Linear interpolation of (time, level) columns; no extrapolation.

    Heights must increase strictly in each column. Missing values remain
    missing; interpolation never bridges an interior missing value.
    """
    values, heights = np.asarray(values, float), np.asarray(heights, float)
    targets = np.asarray(targets, float)
    if values.shape != heights.shape or values.ndim != 2 or targets.ndim != 1:
        raise ValueError("Expected matching (time, level) arrays and one-dimensional target heights")
    if not np.isfinite(heights).all() or np.any(np.diff(heights, axis=1) <= 0):
        raise ValueError("Physical heights must be finite and strictly increasing")
    return np.stack([np.interp(targets, z, v, left=np.nan, right=np.nan) for z, v in zip(heights, values)])


def wrf_projection(dataset: Any):
    """Construct the plotting CRS from WRF metadata (WRF spherical Earth)."""
    import cartopy.crs as ccrs
    globe = ccrs.Globe(semimajor_axis=6370000, semiminor_axis=6370000)
    attrs = dataset.attrs
    kind = int(attrs.get("MAP_PROJ", 0))
    longitude = float(attrs.get("STAND_LON", attrs.get("CEN_LON", 0)))
    latitude = float(attrs.get("MOAD_CEN_LAT", attrs.get("CEN_LAT", 0)))
    if kind == 1:
        return ccrs.LambertConformal(central_longitude=longitude, central_latitude=latitude,
            standard_parallels=(float(attrs["TRUELAT1"]), float(attrs["TRUELAT2"])), globe=globe)
    if kind == 2:
        return ccrs.Stereographic(central_longitude=longitude,
            central_latitude=90 if float(attrs["TRUELAT1"]) >= 0 else -90,
            true_scale_latitude=float(attrs["TRUELAT1"]), globe=globe)
    if kind == 3:
        return ccrs.Mercator(central_longitude=longitude, latitude_true_scale=float(attrs["TRUELAT1"]), globe=globe)
    # Geographic XLAT/XLONG remain usable for rotated latitude-longitude grids.
    # This is an explicit geographic display rather than a claimed native CRS.
    return ccrs.PlateCarree()


def geographic_axis(figure: Any, slot: Any, dataset: Any):
    """Add a geographic map, cached coastlines, and outside-only grid labels."""
    import cartopy.crs as ccrs
    from .maps import add_cached_features
    lat = np.asarray(dataset.XLAT.isel(Time=0), float)
    lon = np.asarray(dataset.XLONG.isel(Time=0), float)
    if np.ptp(lon) > 180:
        raise ValueError("This map layout does not yet support domains crossing the longitude seam")
    projection = wrf_projection(dataset)
    ax = figure.add_subplot(slot, projection=projection)
    points = projection.transform_points(ccrs.PlateCarree(), lon, lat)
    ax.set_xlim(float(np.nanmin(points[..., 0])), float(np.nanmax(points[..., 0])))
    ax.set_ylim(float(np.nanmin(points[..., 1])), float(np.nanmax(points[..., 1])))
    geography_available = add_cached_features(ax)
    grid = ax.gridlines(draw_labels=True, x_inline=False, y_inline=False, linewidth=0.35, alpha=0.4)
    grid.top_labels = False; grid.right_labels = False; grid.rotate_labels = False
    grid.xlabel_style = {"size": 8}; grid.ylabel_style = {"size": 8}
    return ax, geography_available


def wind_overview_data(dataset: Any, cell: Any, *, time: int = -1, top: float = 2000,
                       section_row: int | None = None) -> dict[str, Any]:
    """Extract only a 2-D map, a row section, and site columns for an overview."""
    required = {"U10", "V10", "U", "V", "PH", "PHB", "HGT", "XLAT", "XLONG"}
    missing = sorted(name for name in required if name not in dataset)
    if missing:
        raise ValueError("Wind overview requires variables: " + ", ".join(missing))
    if not np.isfinite(top) or top <= 0:
        raise ValueError("Overview height limit must be positive and finite")
    times = history_times(dataset)
    selected = range(len(times))[time]  # also validates a negative index
    y = cell.y if section_row is None else section_row
    if not 0 <= y < dataset.sizes["south_north"]:
        raise ValueError("Section row is outside the domain")
    point = {"south_north": cell.y, "west_east": cell.x}
    heights = mass_heights(dataset.PH.isel(point), dataset.PHB.isel(point),
                           dataset.HGT.isel(point), axis=1, agl=True)
    u = np.asarray(dataset.U.isel(south_north=cell.y, west_east_stag=slice(cell.x, cell.x + 2)), float).mean(axis=-1)
    v = np.asarray(dataset.V.isel(south_north_stag=slice(cell.y, cell.y + 2), west_east=cell.x), float).mean(axis=-1)
    speed = np.hypot(u, v)
    targets = np.linspace(0, top, 101)
    regular = interpolate_columns(speed, heights, targets)
    terrain = np.asarray(dataset.HGT.isel(Time=selected, south_north=y), float)
    zrow = mass_heights(dataset.PH.isel(Time=selected, south_north=y),
                        dataset.PHB.isel(Time=selected, south_north=y), axis=0)
    urow = destagger(np.asarray(dataset.U.isel(Time=selected, south_north=y), float), -1)
    vrow = np.asarray(dataset.V.isel(Time=selected, south_north_stag=slice(y, y + 2)), float).mean(axis=1)
    section = np.hypot(urow, vrow)
    surface_u, surface_v, reference = surface_wind(dataset, selected)
    lat = np.asarray(dataset.XLAT.isel(Time=0), float)
    lon = np.asarray(dataset.XLONG.isel(Time=0), float)
    # Great-circle distance on the same spherical Earth used for WRF geometry.
    from pyproj import Geod
    geod = Geod(a=6370000, b=6370000)
    _, _, segments = geod.inv(lon[y, :-1], lat[y, :-1], lon[y, 1:], lat[y, 1:])
    distance = np.r_[0, np.cumsum(segments)] / 1000
    pbl = None
    if "PBLH" in dataset:
        pbl = np.asarray(dataset.PBLH.isel(Time=selected, south_north=y), float) + terrain
    return dict(times=times, selected=selected, latitude=lat, longitude=lon,
        heights=heights, speed=speed, targets=targets, regular=regular,
        terrain=terrain, section_height=zrow, section_speed=section, distance=distance,
        pbl=pbl, u=surface_u, v=surface_v, reference=reference, section_row=y, top=top)


def plot_wind_overview(dataset: Any, cell: Any, *, domain: str = "d01", time: int = -1,
                       top: float = 2000, section_row: int | None = None,
                       limits: tuple[float, float] | None = None):
    """Return ``(figure, metadata)`` for the map/section/evolution/profile layout.

    The section is a native grid row, not a constant-latitude transect. Map
    vectors are shown only when earth-relative rotation is available. The
    caller owns the returned Matplotlib figure and may edit its axes.
    """
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.colors import Normalize
    import cartopy.crs as ccrs
    data = wind_overview_data(dataset, cell, time=time, top=top, section_row=section_row)
    times = np.asarray(data["times"], dtype="datetime64[s]")
    selected = data["selected"]
    fields = [np.hypot(data["u"], data["v"]), data["regular"],
              data["section_speed"][data["section_height"] <= top]]
    finite = np.concatenate([np.asarray(field).ravel() for field in fields])
    finite = finite[np.isfinite(finite)]
    if not finite.size:
        raise ValueError("No finite wind values are available for the overview")
    low, high = limits if limits is not None else (0.0, max(2.0, float(2 * np.ceil(finite.max() / 2))))
    if not np.isfinite([low, high]).all() or high <= low:
        raise ValueError("Colour limits must be finite and increasing")
    norm = Normalize(low, high)
    style = {"font.size": 9, "font.family": "DejaVu Sans", "axes.titlesize": 11,
             "axes.titleweight": "bold", "axes.titlelocation": "left",
             "axes.spines.top": False, "axes.spines.right": False,
             "text.color": "#172d41", "axes.labelcolor": "#243b53"}
    with plt.rc_context(style):
        fig = plt.figure(figsize=(13.5, 9.4), facecolor="white")
        grid = fig.add_gridspec(2, 2, left=.07, right=.94, top=.81, bottom=.20, hspace=.48, wspace=.35, width_ratios=(1.15, 1))
        fig.text(.07, .95, f"{domain.upper()}  |  WIND AND BOUNDARY-LAYER STRUCTURE", size=18, weight="bold")
        spacing = float(dataset.attrs.get("DX", np.nan)) / 1000
        fig.text(.07, .91, f"{spacing:g} km nominal grid · {data['times'][0]} to {data['times'][-1]} UTC", size=10)
        a, geography = geographic_axis(fig, grid[0, 0], dataset)
        image = a.pcolormesh(data["longitude"], data["latitude"], fields[0], shading="auto", cmap="viridis",
                             norm=norm, transform=ccrs.PlateCarree(), rasterized=True)
        if data["reference"] == "earth-relative":
            stride = max(1, int(max(fields[0].shape) / 12))
            selection = (slice(None, None, stride), slice(None, None, stride))
            arrows = a.quiver(data["longitude"][selection], data["latitude"][selection],
                data["u"][selection], data["v"][selection], transform=ccrs.PlateCarree(), color="white",
                scale=max(high, 1) * 12, width=.0035, zorder=6)
            key_speed = max(1, round(high / 2))
            a.quiverkey(arrows, .1, .055, key_speed, f"{key_speed:g} m/s", labelpos="E", color="white", labelcolor="white")
        row = data["section_row"]
        a.plot(data["longitude"][row], data["latitude"][row], color="#ffb454", lw=1.8, transform=ccrs.PlateCarree(), zorder=7)
        a.plot(cell.longitude, cell.latitude, "o", color="white", markeredgecolor="#172d41", ms=5, transform=ccrs.PlateCarree(), zorder=8)
        a.set_title(f"A  |  10 m wind · {data['times'][selected][11:16]} UTC", pad=16)
        fig.colorbar(image, ax=a, label="Wind speed (m/s)", pad=.025, shrink=.9)
        b = fig.add_subplot(grid[0, 1])
        zrow = data["section_height"]
        keep = np.flatnonzero(np.nanmin(zrow, axis=1) <= top * 1.1)
        count = min(zrow.shape[0], max(2, int(keep[-1]) + 1)) if keep.size else min(2, zrow.shape[0])
        if count >= 2:
            image = b.pcolormesh(np.broadcast_to(data["distance"], zrow[:count].shape), zrow[:count],
                data["section_speed"][:count], norm=norm, cmap="viridis", shading="auto", rasterized=True)
            fig.colorbar(image, ax=b, label="Wind speed (m/s)", pad=.025)
        b.fill_between(data["distance"], 0, data["terrain"], color="#485c69", zorder=4)
        if data["pbl"] is not None:
            b.plot(data["distance"], data["pbl"], color="#ffb454", lw=1.7, label="WRF PBLH + terrain")
            b.legend(loc="upper right", fontsize=8)
        if row == cell.y:
            b.axvline(data["distance"][cell.x], color="white", ls=":", lw=1.2)
        b.set(xlabel="Distance along highlighted grid row (km)", ylabel="Height MSL (m)", ylim=(0, top))
        b.set_title("B  |  Wind section and model PBL height", pad=16)
        c = fig.add_subplot(grid[1, 0])
        dates = mdates.date2num(times)
        image = c.pcolormesh(dates, data["targets"], data["regular"].T,
            shading="auto", cmap="viridis", norm=norm, rasterized=True)
        locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
        c.xaxis.set_major_locator(locator)
        c.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        c.set(xlabel="Actual history times (UTC)", ylabel="Height AGL (m)", ylim=(0, top))
        c.set_title(f"C  |  Site evolution · {cell.latitude:.2f}°, {cell.longitude:.2f}°", pad=16)
        fig.colorbar(image, ax=c, label="Wind speed (m/s)", pad=.025)
        d = fig.add_subplot(grid[1, 1])
        indices = sorted({0, selected // 2, selected})
        for index, colour in zip(indices, ("#254d83", "#07827b", "#ce641e")):
            d.plot(data["speed"][index], data["heights"][index], color=colour, lw=2.2,
                   label=data["times"][index].replace("T", " ") + " UTC")
        d.set(xlabel="Horizontal wind speed (m/s)", ylabel="Height AGL (m)", ylim=(0, top), xlim=(0, high * 1.05))
        d.set_title("D  |  Profiles at the same site", pad=16)
        d.grid(alpha=.2); d.legend(loc="upper left", frameon=False, fontsize=7)
        steps = np.diff(times.astype("int64"))
        cadence = "single history time" if not steps.size else (
            f"{steps[0] / 60:g} minute history cadence" if np.all(steps == steps[0]) else "irregular history cadence")
        fig.text(.07, .065,
            f"{cadence}; colour limits shared across panels. Section: native grid row {row}; site: nearest grid cell.\n"
            f"Map vectors: {data['reference']}. Section heights: MSL. Site heights: AGL; linear vertical interpolation without extrapolation.\n"
            "Methods [WRF, wind, grid, constants, colour] and source files are recorded in the sidecar and report. Model output, not observational validation.",
            fontsize=8, color="#52697d", linespacing=1.6)
    metadata = {
        "schema_version": 1, "domain": domain, "diagnostic": "wind_overview",
        "timestamps_utc": data["times"], "selected_time_utc": data["times"][selected],
        "site": {"latitude": cell.latitude, "longitude": cell.longitude, "x": int(cell.x), "y": int(cell.y)},
        "section": {"kind": "native_grid_row", "row": int(row), "height_reference": "MSL"},
        "site_height_reference": "AGL", "height_limit_m": top, "wind_units": "m s-1",
        "wind_reference": data["reference"], "colour_limits_m_s": [low, high],
        "gravity_m_s2": GRAVITY, "earth_radius_m": 6370000,
        "vertical_interpolation": "linear wind-speed interpolation at each time; no extrapolation",
        "history_cadence": cadence, "geography_available": geography,
        "definitions": {"mass_wind": "adjacent arithmetic averages of staggered U and V; speed = hypot(u,v)",
            "height": "mass-level average of (PH+PHB)/g; subtract HGT for AGL",
            "rotation": "east=u*COSALPHA-v*SINALPHA; north=v*COSALPHA+u*SINALPHA",
            "pbl_height": "WRF PBLH as written by the selected physics; no alternative PBL diagnostic inferred"},
        "limitations": ["No observational validation", "Sampling limits resolved temporal variability",
            "Native row section is not a constant-latitude transect", "No antimeridian-crossing map support"],
        "references": REFERENCES,
    }
    return fig, metadata


def save_wind_overview(dataset: Any, cell: Any, prefix: str | Path, *, sources=(), formats=("png","pdf","svg"), **kwargs):
    """Save selected figure formats plus a JSON methods/provenance sidecar.

    Standalone default: PNG/PDF/SVG. The complete report requests PNG/SVG only
    so its sole PDF is the assembled report, not separate per-figure documents.
    """
    import json
    import matplotlib.pyplot as plt
    formats=tuple(formats)
    if not formats or any(name not in {"png","pdf","svg"} for name in formats):
        raise ValueError("formats must select png, pdf and/or svg")
    prefix = Path(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    fig, metadata = plot_wind_overview(dataset, cell, **kwargs)
    metadata["source_files"] = [Path(source).name for source in sources]
    try:
        paths = {}
        for suffix in formats:
            path = prefix.with_suffix("." + suffix)
            fig.savefig(path, dpi=180, facecolor="white")
            paths[suffix] = path
        sidecar = prefix.with_suffix(".json")
        sidecar.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        paths["metadata"] = sidecar
        return paths, metadata
    finally:
        plt.close(fig)
