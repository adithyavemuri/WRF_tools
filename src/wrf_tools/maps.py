"""Explicit, cacheable Cartopy feature setup for offline report generation."""
from __future__ import annotations

from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=16)
def _geometries(path,modified):
    from cartopy.io import shapereader
    reader=shapereader.Reader(path)
    try: return tuple(reader.geometries())
    finally: reader.close()


FEATURES = (
    ("physical", "land"),
    ("physical", "ocean"),
    ("physical", "lakes"),
    ("physical", "coastline"),
    ("cultural", "admin_0_boundary_lines_land"),
)


def setup_map_data(*, resolution: str = "50m") -> list[Path]:
    """Download Natural Earth features only when explicitly requested."""
    from cartopy.io import shapereader
    return [Path(shapereader.natural_earth(resolution, category, name)) for category, name in FEATURES]


def add_cached_features(ax, *, resolution: str = "50m", allow_download: bool = True) -> bool:
    """Add Natural Earth features; allow_download=False is strictly cache-only.

    Returns False with a visible bundled-image fallback when data are absent.
    The default retains the automatic local cache download used by reports.
    """
    import os
    import cartopy
    if os.environ.get("WRF_TOOLS_OFFLINE_MAPS","").lower() in {"1","true","yes"}:
        allow_download=False
    import cartopy.crs as ccrs
    from shapely.geometry import box
    data = Path(cartopy.config["data_dir"]) / "shapefiles" / "natural_earth"
    styles = {
        ("physical", "land"): {"facecolor": "#EEE9D6", "edgecolor": "none", "zorder": 0},
        ("physical", "ocean"): {"facecolor": "#DDEBF4", "edgecolor": "none", "zorder": 0},
        ("physical", "lakes"): {"facecolor": "#DDEBF4", "edgecolor": "#729BB7", "linewidth": .35, "zorder": 1},
        ("physical", "coastline"): {"facecolor": "none", "edgecolor": "#253746", "linewidth": .55, "zorder": 2},
        ("cultural", "admin_0_boundary_lines_land"): {"facecolor": "none", "edgecolor": "#596A73", "linewidth": .4, "linestyle": "--", "zorder": 2},
    }
    paths = [data / category / f"ne_{resolution}_{name}.shp" for category, name in FEATURES]
    if not all(path.is_file() for path in paths):
        if not allow_download:
            ax.stock_img(); return False
        try:
            setup_map_data(resolution=resolution)
        except Exception:
            ax.stock_img()
            return False
    for spec, path in zip(FEATURES, paths):
        west,east,south,north=ax.get_extent(ccrs.PlateCarree())
        bounds=box(west-1e-3,south-1e-3,east+1e-3,north+1e-3)
        # Clip context to the actual view, not every polygon in the world.
        # This keeps vector exports small without changing atmospheric data.
        geometries=[geometry.intersection(bounds) for geometry in _geometries(str(path),path.stat().st_mtime_ns) if geometry.intersects(bounds)]
        ax.add_geometries(geometries, ccrs.PlateCarree(), **styles[spec])
    return True
