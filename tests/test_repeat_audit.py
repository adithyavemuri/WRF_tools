"""Second-pass edge cases: analytical results and explicit input contracts."""
import numpy as np
import pytest

from wrf_tools.diagnostics import (
    brunt_vaisala_frequency, circular_mean, integral_time_scale, inversion_layers,
    precipitation_diagnostics, resolved_tke, reynolds_flux, tke_budget, turbulence_intensity,
)
from wrf_tools.grid import interpolate_to_levels
from wrf_tools.observations import align, from_columns, normalize_time


def test_nonuniform_vertical_derivatives_with_shared_and_column_heights():
    z=np.array([10.,30.,100.,250.])
    theta=290+.0001*z**2
    derivative=np.gradient(theta,z)
    expected=np.sqrt(9.80665/theta*derivative)
    np.testing.assert_allclose(brunt_vaisala_frequency(theta,z),expected)
    # The interior derivative of a quadratic must be exact on uneven levels.
    np.testing.assert_allclose(derivative[1:-1],.0002*z[1:-1])
    columns=np.stack([theta,theta+1])
    np.testing.assert_allclose(brunt_vaisala_frequency(columns,z,axis=1),
        np.sqrt(9.80665/columns*np.stack([derivative,derivative])))
    np.testing.assert_array_equal(inversion_layers(theta,z,minimum_gradient=.01),derivative>.01)
    with pytest.raises(ValueError,match="increasing"):
        brunt_vaisala_frequency(theta,z[::-1])


def test_nonuniform_partial_budget_and_invalid_axes():
    z=np.array([10.,30.,100.,250.]); fluct=np.array([-1.,1.])[:,None]
    u=.0001*z**2+fluct; w=np.broadcast_to(2*fluct,u.shape)
    v=np.zeros_like(u); theta=np.full_like(u,290.)
    actual=tke_budget(u,v,w,theta,z)
    np.testing.assert_allclose(actual["shear_production"],-2*np.gradient(.0001*z**2,z))
    with pytest.raises(ValueError,match="indexes"):
        tke_budget(u,v,w,theta,z,time_axis=2)
    with pytest.raises(ValueError,match="two time"):
        tke_budget(u[:1],v[:1],w[:1],theta[:1],z)


def test_integral_scale_includes_interpolated_first_zero_crossing():
    scale,correlation=integral_time_scale([1.,-1.],spacing=3.)
    np.testing.assert_allclose(correlation,[1,-.5])
    assert scale==pytest.approx(1.)  # triangle to zero at lag 2 seconds


@pytest.mark.parametrize("values",[[np.nan,1,2],[0,np.nan,2],[0,1,np.nan],[0,np.inf,2]])
def test_missing_rainfall_never_becomes_a_partial_period_total(values):
    result=precipitation_diagnostics(values,[0,0,0])
    assert result["missing_detected"] and np.isnan(result["total"])


def test_interpolation_rejects_folded_coordinates_and_preserves_data_gaps():
    with pytest.raises(ValueError,match="monotonic"):
        interpolate_to_levels([1,2,3],[0,100,50],75,axis=0)
    with pytest.raises(ValueError,match="monotonic"):
        interpolate_to_levels([1,2,3],[0,0,100],50,axis=0)
    assert np.isnan(interpolate_to_levels([0,np.nan,100],[0,50,100],25,axis=0))
    assert interpolate_to_levels([2,4,6],[1000,900,800],950,axis=0)==pytest.approx(3)
    fields=np.broadcast_to([2,4,6],(2,3))
    coordinates=np.broadcast_to([1000,900,800],fields.shape)
    assert interpolate_to_levels(fields,coordinates,[950,850],axis=1).shape==(2,2)


def test_turbulence_rejects_silent_broadcasting_and_undefined_intensity():
    from wrf_tools.les import calculate_total_tke
    u=np.array([[1.,2.],[3.,4.]])
    np.testing.assert_allclose(calculate_total_tke(u,u,u,subgrid_tke=np.array([2,3])),[3.5,4.5])
    with pytest.raises(ValueError,match="average"):
        calculate_total_tke(u,u,u,subgrid_tke=np.ones_like(u))
    with pytest.raises(ValueError,match="identical"):
        resolved_tke(u,u[:1],u)
    with pytest.raises(ValueError,match="identical"):
        reynolds_flux(u,u[:1])
    assert np.isnan(turbulence_intensity([-1,1]))


def test_circular_statistics_cannot_invent_a_prevailing_direction():
    from wrf_tools.validation import circular_error
    assert np.isnan(circular_mean([0,180]))
    assert np.isnan(circular_mean([0,90],weights=[0,0]))
    assert circular_mean([0,90],weights=[0,1])==pytest.approx(90)
    with pytest.raises(ValueError,match="nonnegative"):
        circular_mean([0,90],weights=[1,-1])
    with pytest.raises(ValueError,match="identical"):
        circular_error([1,2],[[1,2]])


def test_observation_timezone_normalization_and_invalid_times():
    aware=from_columns(time=[b"2025-01-01T01:00:00+01:00",b"2025-01-01T01:00:00Z"],variables={"speed":[5,6]})
    actual=normalize_time(aware)
    np.testing.assert_array_equal(actual.time.values,np.array(["2025-01-01T00:00:00","2025-01-01T01:00:00"],dtype="datetime64[ns]"))
    with pytest.raises(ValueError,match="cannot also"):
        normalize_time(aware,timezone_offset_hours=1)
    missing=from_columns(time=np.array(["NaT"],dtype="datetime64[ns]"),variables={"speed":[5]})
    with pytest.raises(ValueError,match="NaT"):
        normalize_time(missing)
    with pytest.raises(ValueError,match="numeric"):
        normalize_time(from_columns(time=[0,1],variables={"speed":[5,6]}))
    duplicate=from_columns(time=np.array(["2025-01-01","2025-01-01"],dtype="datetime64[ns]"),variables={"speed":[5,6]})
    with pytest.raises(ValueError,match="unique"):
        align(duplicate,actual,tolerance=np.timedelta64(15,"m"))


def test_uniform_wind_has_all_eight_documented_columns(tmp_path):
    from wrf_tools.coupling.openfast import write_uniform_wind
    path=write_uniform_wind(tmp_path/"uniform.wnd",[0,1],[5,6],direction=30,power_law_shear=.2,gust=[0,2])
    values=np.loadtxt(path,comments="!")
    assert values.shape==(2,8)
    np.testing.assert_allclose(values[:,[0,1,2,5,7]],[[0,5,30,.2,0],[1,6,30,.2,2]])
    np.testing.assert_allclose(values[:,[3,4,6]],0)
    with pytest.raises(ValueError,match="increasing"):
        write_uniform_wind(tmp_path/"bad.wnd",[1,0],[5,6])
    assert not (tmp_path/"bad.wnd").exists()


def test_cluster_validation_and_labels_describe_returned_centers():
    from wrf_tools.validation import cluster_profiles,rank_cases
    points=np.arange(30,dtype=float).reshape(10,3)
    labels,centers=cluster_profiles(points,3,seed=2,max_iterations=1)
    np.testing.assert_array_equal(labels,np.argmin(((points[:,None]-centers[None])**2).sum(axis=2),axis=1))
    with pytest.raises(ValueError,match="positive integer"):
        cluster_profiles(points,3,max_iterations=0)
    with pytest.raises(ValueError,match="finite"):
        cluster_profiles([[1,np.nan],[2,3]],2)
    with pytest.warns(RuntimeWarning):
        with pytest.raises(ValueError,match="unavailable"):
            rank_cases({"missing":[np.nan]},[1])


def test_engineering_spectral_integrals_match_declared_component_variance():
    integrate=pytest.importorskip("scipy.integrate")
    from wrf_tools.wind_models import von_karman_spectrum,iec_kaimal_spectrum
    for component in "uvw":
        variance=integrate.quad(lambda f:von_karman_spectrum(f,mean_speed=10,sigma=2,length_scale=100,component=component),0,np.inf)[0]
        assert variance==pytest.approx(4,rel=.003)  # documented rounded constants
    variance=integrate.quad(lambda f:iec_kaimal_spectrum(f,mean_speed=10,sigma=2,length_scale=100),0,np.inf)[0]
    assert variance==pytest.approx(4)


def test_wind_spectral_models_reject_nonphysical_parameters():
    from wrf_tools.wind_models import exponential_coherence,kaimal_spectrum,von_karman_spectrum,iec_kaimal_spectrum
    with pytest.raises(ValueError,match="finite"):
        kaimal_spectrum([.1],mean_speed=np.nan,height=100,friction_velocity=.4)
    with pytest.raises(ValueError,match="sigma"):
        von_karman_spectrum([.1],mean_speed=10,sigma=-1,length_scale=100)
    with pytest.raises(ValueError,match="Frequencies"):
        iec_kaimal_spectrum([-.1],mean_speed=10,sigma=1,length_scale=100)
    with pytest.raises(ValueError,match="separation"):
        exponential_coherence([.1],-10,mean_speed=10)


def test_report_uses_reset_aware_rainfall_not_just_counter_endpoints(tmp_path):
    from types import SimpleNamespace
    import xarray as xr
    from wrf_tools.hindcast import summarize_hindcast
    counters=np.array([[[0,0],[0,0]],[[10,1],[np.nan,2]],[[2,2],[3,4]]],float)
    ds=xr.Dataset({"Times":("Time",[b"2025-01-01_00:00:00",b"2025-01-01_01:00:00",b"2025-01-01_02:00:00"]),
        "RAINC":(("Time","south_north","west_east"),counters),
        "RAINNC":(("Time","south_north","west_east"),np.zeros_like(counters))})
    record=summarize_hindcast(ds,files=[tmp_path/"rain.nc"],cell=SimpleNamespace(x=0,y=0,latitude=52,longitude=5))["precipitation"]
    assert record["status"]=="PARTIAL" and record["valid_cell_fraction"]==.5
    assert record["reset_cell_count"]==record["missing_cell_count"]==1
    assert record["domain_mean_accumulation_mm"]==3
    assert np.isnan(record["selected_point_accumulation_mm"])


def test_individual_rainfall_reset_cannot_be_hidden_by_another_component():
    result=precipitation_diagnostics([0,10,2],[0,0,20])
    # The combined counter increases at every time, but RAINC resets.
    assert (np.diff(result["accumulated"])>0).all()
    assert result["reset_detected"] and np.isnan(result["total"])


def test_unsigned_precipitation_counters_do_not_wrap_on_reset():
    from wrf_tools.diagnostics import interval_precipitation
    result=interval_precipitation(np.array([0,10,2],dtype="uint16"))
    np.testing.assert_allclose(result,[0,10,-8])
