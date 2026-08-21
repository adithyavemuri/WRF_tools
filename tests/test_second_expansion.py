import numpy as np
import xarray as xr
from wrf_tools.coupling.openfast import concatenate_fields, constant_field, velocity_at
from wrf_tools.les import load_sgs_stress, sgs_tke
from wrf_tools.wps import domain_geometries, eta_levels

def test_sgs_and_wps_domains():
    ds = xr.Dataset({name: ("x", np.ones(2)*i) for i, name in enumerate(("m11","m12","m13","m22","m23","m33"), 1)})
    stress = load_sgs_stress(ds)
    np.testing.assert_allclose(sgs_tke(stress), 0.5*(1+4+6))
    levels = eta_levels(10)
    assert levels[0] == 1 and levels[-1] == 0 and np.all(np.diff(levels) < 0)
    namelist = {"share": {"max_dom": 2}, "geogrid": {"parent_id": [1,1], "parent_grid_ratio": [1,3], "i_parent_start": [1,10], "j_parent_start": [1,10], "e_we": [100,31], "e_sn": [100,31], "dx": 9000, "dy": 9000}}
    domains = domain_geometries(namelist)
    assert domains[1].dx == 3000 and domains[1].parent == 1

def test_wind_field_operations():
    first = constant_field(speed=10, duration=1, dt=0.5, ny=3, nz=2, dy=10, dz=10, hub_height=20, bottom_height=10)
    combined = concatenate_fields([first, first])
    assert combined.velocity.shape[0] == 6
    np.testing.assert_allclose(velocity_at(first, y=0, z=20)[:, 0], 10)
