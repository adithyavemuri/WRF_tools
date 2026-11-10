"""Small map overlays and evidence from model-written wind-farm output."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np


REFERENCES = {
    "fitch2012": {"title": "Fitch et al. (2012), Local and Mesoscale Impacts of Wind Farms as Parameterized in a Mesoscale NWP Model",
                  "url": "https://doi.org/10.1175/MWR-D-11-00352.1"},
    "wrf_fitch": {"title": "WRF v4.7.1 Fitch implementation (POWER is summed turbine power per grid cell)",
                  "url": "https://github.com/wrf-model/WRF/blob/v4.7.1/phys/module_wind_fitch.F"},
}


def _file_hash(path):
    """Stream checksums without loading a history file into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_turbine_layout(path):
    """Read a standalone CSV with latitude/longitude and optional farm names."""
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or not {"latitude", "longitude"} <= set(rows[0]):
        raise ValueError("Turbine CSV needs nonempty latitude and longitude columns")
    latitude = np.array([float(row["latitude"]) for row in rows])
    longitude = np.array([float(row["longitude"]) for row in rows])
    if not (np.isfinite(latitude).all() and np.isfinite(longitude).all()
            and (np.abs(latitude) <= 90).all() and (np.abs(longitude) <= 180).all()):
        raise ValueError("Turbine coordinates must be finite latitude/longitude in degrees")
    return dict(latitude=latitude, longitude=longitude, source=path.name,
                sha256=_file_hash(path), turbine_count=len(rows),
                farms=sorted({row["farm"] for row in rows if row.get("farm")}))


def _overlay_turbines(figure, layout, *, label="Turbine locations (context only)"):
    """Draw 2-point-squared markers only on maps; preserve limits and legends."""
    if layout is None:
        return
    import cartopy.crs as ccrs
    from cartopy.mpl.geoaxes import GeoAxes
    for ax in figure.axes:
        if not isinstance(ax, GeoAxes):
            continue
        limits = ax.get_xlim(), ax.get_ylim()
        ax.scatter(layout["longitude"], layout["latitude"], s=2, color="#151515",
                   edgecolors="white", linewidths=.12, transform=ccrs.PlateCarree(),
                   zorder=15, label=label)
        ax.set_xlim(limits[0]); ax.set_ylim(limits[1])
        old_legend = ax.get_legend()
        location = old_legend._loc if old_legend is not None else "lower left"
        legend = ax.legend(loc=location, fontsize=7, markerscale=1.5, framealpha=.94)
        legend.set_zorder(30)


def _wind_farm_evidence(dataset, *, flag=None):
    """Separate configured activation from output evidence; never infer a wake."""
    native = dataset.attrs.get("WINDFARM_OPT")
    flag = native if native is not None else flag
    flag = int(flag) if flag is not None else None
    status = "Fitch active" if flag == 1 else ("WFP off; locations are context only" if flag == 0 else "Activation not established")
    if flag is not None and flag not in (0, 1):
        status = f"Wind-farm option {flag} (not identified as Fitch)"
    result = dict(windfarm_opt=flag, activation=status,
                  flag_source="WRF attribute" if native is not None else ("effective namelist" if flag is not None else "not supplied"),
                  power_status="POWER unavailable")
    if "POWER" in dataset:
        field = dataset.POWER.transpose("Time", "south_north", "west_east")
        values = np.asarray(field, dtype=float)
        if str(field.attrs.get("units", "")).strip() != "W" or not np.isfinite(values).all() or (values < 0).any():
            raise ValueError("Wind-farm POWER must be finite, nonnegative and in W")
        result.update(power_status="Nonzero generated power" if (values > 0).any() else "Zero at all saved times",
                      fleet_power_mw=(values.sum(axis=(1, 2)) / 1e6).tolist(),
                      powered_cells=(values > 0).sum(axis=(1, 2)).tolist())
    return result


def _load_farm_diagnostics(path, *, files, times, domain, layout, configuration_hash=None):
    """Accept companion farm means only when their saved inputs match this run."""
    path = Path(path)
    result = json.loads(path.read_text())
    if result.get("domain") != domain or result.get("times_utc") != times:
        raise ValueError("Farm diagnostics domain/timestamps do not match the report")
    hashes = {Path(item).name: _file_hash(item) for item in files}
    if result.get("input_sha256") != hashes:
        raise ValueError("Farm diagnostics history-file checksums do not match this run")
    if layout is None or result.get("layout_sha256") != layout["sha256"]:
        raise ValueError("Farm diagnostics turbine layout does not match the report")
    if configuration_hash and result.get("configuration_sha256") != configuration_hash:
        raise ValueError("Farm diagnostics configuration does not match the report")
    return result
