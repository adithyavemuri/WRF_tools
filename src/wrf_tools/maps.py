"""Explicit, cacheable Cartopy feature setup for offline report generation."""
from __future__ import annotations

from pathlib import Path


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


def add_cached_features(ax, *, resolution: str = "50m") -> bool:
    """Add Natural Earth features, downloading them once into Cartopy's cache."""
    import cartopy
    import cartopy.crs as ccrs
    from cartopy.io import shapereader
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
        try:
            setup_map_data(resolution=resolution)
        except Exception:
            ax.stock_img()
            return False
    for spec, path in zip(FEATURES, paths):
        ax.add_geometries(shapereader.Reader(path).geometries(), ccrs.PlateCarree(), **styles[spec])
    return True
