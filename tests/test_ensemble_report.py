import numpy as np
import pytest
import xarray as xr
from wrf_tools.ensemble import _diagnostic as diagnostic, _mean_members as mean_members, _validate_alignment as validate_alignment


def dataset(u=3.):
    shape = (2, 2, 2)
    return xr.Dataset({"Times": ("Time", np.array([b"2025-01-10_00:00:00", b"2025-01-10_01:00:00"])),
        "XLAT": (("Time", "south_north", "west_east"), np.full(shape,52.)),
        "XLONG": (("Time", "south_north", "west_east"), np.full(shape,5.)),
        "HGT": (("Time", "south_north", "west_east"), np.zeros(shape)),
        "U10": (("Time", "south_north", "west_east"), np.full(shape,u)),
        "V10": (("Time", "south_north", "west_east"), np.zeros(shape))}, attrs={"DX":3000.,"DY":3000.,"MAP_PROJ":1})


def test_mean_wind_speed_is_not_speed_of_mean_vectors():
    a, b = dataset(3.), dataset(-3.)
    actual = mean_members([diagnostic(a,"wind_speed_10m")[0], diagnostic(b,"wind_speed_10m")[0]])
    np.testing.assert_allclose(actual,3.)


def test_missing_member_values_propagate():
    assert np.isnan(mean_members([np.array([1.,2.]),np.array([np.nan,4.])])[0])


def test_rejects_different_grid_and_time():
    a,b=dataset(),dataset()
    b.XLAT.values[:]=53
    with pytest.raises(ValueError,match="grids differ"):
        validate_alignment([a,b])
    b=dataset()
    b.Times.values[1]=b"2025-01-10_02:00:00"
    with pytest.raises(ValueError,match="timestamps"):
        validate_alignment([a,b])
    with pytest.raises(ValueError,match="requires HGT"):
        validate_alignment([a,dataset().drop_vars("HGT")])


def test_precipitation_differences_before_mean_and_rejects_reset():
    a=dataset()
    a["RAINC"]=(a.U10.dims,np.array([np.ones((2,2)),np.full((2,2),3.)]))
    a["RAINNC"]=xr.zeros_like(a.RAINC)
    np.testing.assert_allclose(diagnostic(a,"precipitation")[0][-1],2.)
    a.RAINC.values[-1]=0
    with pytest.raises(ValueError,match="reset"):
        diagnostic(a,"precipitation")
