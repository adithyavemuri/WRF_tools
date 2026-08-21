import numpy as np
import xarray as xr
import pytest
from wrf_tools.io import open_wrf_sequence

def _write(path, grid_id, stamp, nx=2):
    chars=np.array(list(stamp),dtype="S1")[None,:]
    ds=xr.Dataset({"Times":(("Time","DateStrLen"),chars),"T":(("Time","south_north","west_east"),np.ones((1,2,nx)))},attrs={"GRID_ID":grid_id,"DX":1000.0,"DY":1000.0,"MAP_PROJ":1,"CEN_LAT":52.0,"CEN_LON":4.0})
    ds.to_netcdf(path)

def test_same_domain_sequence_and_mixed_domain_rejection(tmp_path):
    first,second,mixed=tmp_path/"one.nc",tmp_path/"two.nc",tmp_path/"mixed.nc"
    _write(first,1,"2020-01-01_00:00:00"); _write(second,1,"2020-01-01_01:00:00"); _write(mixed,2,"2020-01-01_02:00:00")
    with open_wrf_sequence([first,second]) as ds: assert ds.sizes["Time"]==2
    with pytest.raises(ValueError,match="Incompatible"): open_wrf_sequence([first,mixed])
