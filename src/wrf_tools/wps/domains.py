"""WRF/WPS nested-domain geometry independent of plotting libraries."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class DomainGeometry:
    domain: int
    parent: int
    dx: float
    dy: float
    nx: int
    ny: int
    x0: float
    y0: float

    @property
    def extent(self):
        return self.x0, self.x0+(self.nx-1)*self.dx, self.y0, self.y0+(self.ny-1)*self.dy

def _list(value, count):
    values = value if isinstance(value, list) else [value]
    return values + [values[-1]]*(count-len(values))

def domain_geometries(namelist):
    """Calculate nested grid geometry in parent-projection metres."""
    share, geo = namelist.get("share", {}), namelist["geogrid"]
    count = int(share.get("max_dom", geo.get("max_dom", 1)))
    if count<1: raise ValueError("max_dom must be positive")
    parent = _list(geo.get("parent_id", [1]), count)
    ratio = _list(geo.get("parent_grid_ratio", [1]), count)
    istart = _list(geo.get("i_parent_start", [1]), count)
    jstart = _list(geo.get("j_parent_start", [1]), count)
    nx, ny = _list(geo["e_we"], count), _list(geo.get("e_sn", geo.get("e_ns")), count)
    domains = [DomainGeometry(1, 0, float(geo["dx"]), float(geo["dy"]), int(nx[0]), int(ny[0]), 0.0, 0.0)]
    for i in range(1, count):
        if not 1<=int(parent[i])<=i or float(ratio[i])<=1 or int(istart[i])<1 or int(jstart[i])<1:
            raise ValueError(f"Domain d{i+1:02d} needs an earlier parent, ratio >1, and positive start indexes")
        p = domains[int(parent[i])-1]
        dx, dy = p.dx/float(ratio[i]), p.dy/float(ratio[i])
        x0, y0 = p.x0+(int(istart[i])-1)*p.dx, p.y0+(int(jstart[i])-1)*p.dy
        child = DomainGeometry(i+1, int(parent[i]), dx, dy, int(nx[i]), int(ny[i]), x0, y0)
        if child.extent[1] > p.extent[1] or child.extent[3] > p.extent[3]:
            raise ValueError(f"Domain d{i+1:02d} extends beyond its parent")
        domains.append(child)
    return domains

def eta_levels(count, *, exponent=1.5):
    """Generate monotonically decreasing terrain-following eta interfaces."""
    if count < 2 or exponent <= 0:
        raise ValueError("count must be >=2 and exponent positive")
    coordinate = np.linspace(0.0, 1.0, count)
    return 1.0-coordinate**exponent

def geographic_corners(domains, *, ref_latitude, ref_longitude, truelat1, truelat2, stand_lon, earth_radius=6370000.0):
    """Centred Lambert grid corners on the WRF sphere, using optional pyproj.

    Assumes ref_lat/ref_lon is the d01 centre. Non-default ref_x/ref_y,
    rotated/geographic/Mercator/polar projections are not implemented here.
    WRF's default spherical radius is 6,370,000 m, not the WGS84 ellipsoid.
    """
    try:
        from pyproj import CRS,Transformer
    except ImportError as exc:
        raise ImportError("geographic WPS corners require the plotting extra") from exc
    if not np.isfinite(earth_radius) or earth_radius<=0: raise ValueError("Earth radius must be positive and finite")
    projected=CRS.from_proj4(f"+proj=lcc +lat_1={truelat1} +lat_2={truelat2} +lat_0={ref_latitude} +lon_0={stand_lon} +R={earth_radius}")
    geodetic=projected.geodetic_crs; transformer=Transformer.from_crs(projected,geodetic,always_xy=True); forward=Transformer.from_crs(geodetic,projected,always_xy=True)
    # Domain coordinates are relative to the d01 lower-left; anchor them by
    # placing the d01 centre at the WPS reference point.
    outer=domains[0]; cx=(outer.extent[0]+outer.extent[1])/2; cy=(outer.extent[2]+outer.extent[3])/2; anchor_x,anchor_y=forward.transform(ref_longitude,ref_latitude)
    result=[]
    for domain in domains:
        xmin,xmax,ymin,ymax=domain.extent; coordinates=[]
        for x,y in ((xmin,ymin),(xmax,ymin),(xmax,ymax),(xmin,ymax)):
            coordinates.append(transformer.transform(x-cx+anchor_x,y-cy+anchor_y))
        result.append(coordinates)
    return result
