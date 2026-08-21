import numpy as np
import xarray as xr
from wrf_tools import validation
from wrf_tools.extract import transect, variables
from wrf_tools.grid import regrid_regular
from wrf_tools.openfast import channel_statistics, compare_outputs, rainflow_cycles, stress_from_moment, zero_crossing_frequency
from wrf_tools.observations import from_columns
from wrf_tools.wind_models import exponential_coherence, von_karman_spectrum

def test_validation_and_observations():
    assert validation.rmse([1, 3], [1, 1]) == np.sqrt(2)
    assert validation.circular_error(1, 359) == 2
    assert validation.kantorovich_distance([0, 1], [1, 2]) == 1
    obs = from_columns(time=["2020-01-01", "2020-01-02"], variables={"wind": [5, 6]})
    assert obs.sizes["time"] == 2

def test_extract_models_and_openfast_analysis():
    ds = xr.Dataset({"U": ("x", [1, 2])})
    assert "u" in variables(ds, {"u": "U"})
    assert np.all(exponential_coherence([0, 1], 10, mean_speed=10) <= 1)
    assert np.all(von_karman_spectrum([0.1, 1], mean_speed=10, sigma=1, length_scale=20) > 0)
    assert zero_crossing_frequency(np.sin(np.linspace(0, 20*np.pi, 1001)), 100) > 0
    assert stress_from_moment(10, 2, 5) == 4
    assert rainflow_cycles([0, 1, 0, -1, 0]).shape[1] == 2
    output=xr.Dataset({"load":("time",[1.,2.])},coords={"time":[0,1]})
    assert channel_statistics(output)["load"]["mean"]==1.5
    assert compare_outputs(output,output)["load"]["rmse"]==0
    grid=np.array([[0.,1.],[1.,2.]])
    np.testing.assert_allclose(regrid_regular(grid,[0,1],[0,1],[.5],[.5]),[[1.]])
    section,_,_=transect(grid,(0,0),(1,1),points=3)
    np.testing.assert_allclose(section,[0,1,2])
    assert validation.rank_cases({"bad":[3,3],"good":[1,1]},[1,1])[0][0]=="good"
