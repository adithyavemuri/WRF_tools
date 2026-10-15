"""Analytical/independent-oracle regressions, not atmospheric validation."""
import json
import numpy as np
import pytest
import xarray as xr

from wrf_tools import validation
from wrf_tools.capabilities import capability_catalog
from wrf_tools.filters import spectral_downsample
from wrf_tools.io import open_wrf_sequence
from wrf_tools.observations import read_csv, read_netcdf
from wrf_tools.spectra import power_spectrum,welch_spectrum,coherence
from wrf_tools.wps.namelist import read_namelist


def test_pairwise_finite_statistics_and_shape_rejection():
    a=np.array([1.,2.,np.nan,4.,np.inf]); b=np.array([1.,np.nan,100.,5.,6.])
    assert validation.rmse(a,b)==pytest.approx(np.sqrt(.5))
    assert validation.correlation(a,b)==pytest.approx(1)
    assert validation.normalized_error(a,b)==pytest.approx(np.sqrt(.5)/3)
    with pytest.raises(ValueError,match="identical shapes"):
        validation.rmse([1,2],[[1,2]])
    assert np.isnan(validation.correlation([1,1],[2,3]))
    assert np.isnan(validation.normalized_error([1,2],[0,0]))


def test_axis_correlation_uses_the_same_pairs():
    a=[[1,2,np.nan,4],[1,np.nan,3,4]]; b=[[1,np.nan,100,5],[2,8,4,5]]
    np.testing.assert_allclose(validation.correlation(a,b,axis=1),[1,1])


def test_empirical_wasserstein_matches_scipy_for_unequal_lengths():
    stats=pytest.importorskip("scipy.stats")
    rng=np.random.default_rng(42)
    for n,m in [(1,4),(4,1),(2,7),(19,31),(5,5)]:
        a,b=rng.normal(size=n),rng.normal(size=m)
        assert validation.kantorovich_distance(a,b)==pytest.approx(stats.wasserstein_distance(a,b))
    with pytest.raises(ValueError): validation.kantorovich_distance([], [1])


@pytest.mark.parametrize("shape,factor",[((8,8),2),((9,11),2),((16,17),3),((8,7),1),((6,8),4)])
def test_fourier_downsampling_matches_independent_scipy(shape,factor):
    signal=pytest.importorskip("scipy.signal")
    field=np.random.default_rng(1).normal(size=shape)+5
    expected=signal.resample(signal.resample(field,shape[0]//factor,axis=0),shape[1]//factor,axis=1)
    actual=spectral_downsample(field,factor_y=factor)
    np.testing.assert_allclose(actual,expected,atol=1e-13)
    assert actual.mean()==pytest.approx(field.mean())


def test_periodogram_parseval_and_welch_independent_oracle():
    signal=pytest.importorskip("scipy.signal")
    values=np.random.default_rng(2).normal(size=65)
    f,p=power_spectrum(values,spacing=.2)
    assert p.sum()*(f[1]-f[0])==pytest.approx(values.var())
    fw,pw=welch_spectrum(values,sample_rate=5,nperseg=15,overlap=7)
    fs,ps=signal.welch(values,fs=5,window=np.hanning(15),nperseg=15,noverlap=7)
    np.testing.assert_allclose(fw,fs); np.testing.assert_allclose(pw,ps,atol=1e-13)
    fc,cc=coherence(values,values[::-1],sample_rate=5,nperseg=15,overlap=7)
    fs,cs=signal.coherence(values,values[::-1],fs=5,window=np.hanning(15),nperseg=15,noverlap=7)
    np.testing.assert_allclose(fc,fs); np.testing.assert_allclose(cc,cs,atol=1e-13)
    with pytest.raises(ValueError): coherence(values,values,sample_rate=5,nperseg=15,overlap=15)
    with pytest.raises(ValueError): welch_spectrum(values,sample_rate=5,nperseg=2)


def test_namelist_quoted_paths_inline_keys_comments_and_d_exponents(tmp_path):
    file=tmp_path/"namelist.wps"
    file.write_text("&geogrid\n geog_data_path='/path/to/a,b!c', ! comment\n dx=1.d3, dy=2.d3,\n flag=.true.,\n/\n")
    result=read_namelist(file)["geogrid"]
    assert result==dict(geog_data_path="/path/to/a,b!c",dx=1000,dy=2000,flag=True)
    file.write_text("&geogrid\na(1)=3,\n/\n")
    with pytest.raises(ValueError,match="f90nml"): read_namelist(file)


def test_single_row_observation_csv_and_selected_netcdf_close(tmp_path):
    file=tmp_path/"single.csv"; file.write_text("time,speed\n2025-01-01T00:00:00,8\n")
    ds=read_csv(file,time_column="time")
    assert ds.sizes["time"]==1
    ds.to_netcdf(tmp_path/"obs.nc")
    with read_netcdf(tmp_path/"obs.nc",variables=["speed"]) as selected:
        assert selected.speed.item()==8


def test_sequence_rejects_one_dimensional_duplicate_times_and_vertical_grid(tmp_path):
    for i in (1,2):
        xr.Dataset({"Times":("Time",[b"2025-01-01_00:00:00"]),"field":(("Time","bottom_top"),[[1.,2.]])}).to_netcdf(tmp_path/f"{i}.nc")
    with pytest.raises(ValueError,match="unique|increasing"): open_wrf_sequence([tmp_path/"1.nc",tmp_path/"2.nc"])
    xr.Dataset({"Times":("Time",[b"2025-01-01_01:00:00"]),"field":(("Time","bottom_top"),[[1.,2.,3.]])}).to_netcdf(tmp_path/"2.nc")
    with pytest.raises(ValueError,match="Incompatible"): open_wrf_sequence([tmp_path/"1.nc",tmp_path/"2.nc"])


def test_method_basis_exists_for_every_cataloged_function():
    for record in capability_catalog().values():
        assert record["basis"]["category"] and record["basis"]["caveat"]
        assert record["basis"]["references"]
        assert all(r["url"].startswith("https://") for r in record["basis"]["references"])
        assert not record["documentation"].startswith("No function docstring")


def test_bts_validation_checks_metadata_not_just_velocities(tmp_path):
    from wrf_tools.coupling.openfast import constant_field,write_bts,validate_bts
    from wrf_tools.exceptions import DataValidationError
    source=constant_field(speed=8,duration=1,dt=1,ny=2,nz=2,dy=5,dz=5,hub_height=20,bottom_height=10)
    path=write_bts(tmp_path/"inflow.bts",source)
    source.dt=2
    with pytest.raises(DataValidationError,match="dt"): validate_bts(path,expected=source)


def test_rainflow_plateaus_and_empty_inputs():
    from wrf_tools.openfast import rainflow_cycles
    assert rainflow_cycles([]).shape==(0,2)
    assert rainflow_cycles([1,1,1]).shape==(0,2)
    np.testing.assert_allclose(rainflow_cycles([0,1,1,0]),[[1,.5],[1,.5]])


def test_regridding_and_transect_do_not_silently_extrapolate():
    from wrf_tools.grid import regrid_regular
    from wrf_tools.extract import transect
    with pytest.raises(ValueError,match="outside"): regrid_regular(np.ones((2,2)),[0,1],[0,1],[2],[.5])
    with pytest.raises(ValueError,match="inside"): transect(np.ones((2,2)),(-1,0),(1,1))


def test_kaimal_component_variant_matches_published_equations():
    from wrf_tools.wind_models import kaimal_spectrum
    f=np.array([0,.01,.1,1]); n=f*100/10
    np.testing.assert_allclose(kaimal_spectrum(f,mean_speed=10,height=100,friction_velocity=.4,component="u"),.4**2*102*10/(1+33*n)**(5/3))
    np.testing.assert_allclose(kaimal_spectrum(f,mean_speed=10,height=100,friction_velocity=.4,component="w"),.4**2*2.1*10/(1+5.3*n**(5/3)))


def test_precipitation_resets_remain_visible_and_total_unknown():
    from wrf_tools.diagnostics import precipitation_diagnostics
    result=precipitation_diagnostics([0,5,1,2],[0,0,0,0])
    assert result["increment"].tolist()==[0,5,-4,1]
    assert result["reset_detected"] and np.isnan(result["total"])


def test_stability_missing_and_neutral_flux_are_not_misclassified():
    from wrf_tools.diagnostics import stability_class,monin_obukhov_length
    assert stability_class(np.nan)=="unavailable"
    assert stability_class(np.inf)=="neutral"
    assert np.isinf(monin_obukhov_length(290,.3,0))
    assert np.isnan(monin_obukhov_length(290,0,0))


def test_inverse_bolton_water_fit_at_saturation():
    from wrf_tools.diagnostics import dew_point
    np.testing.assert_allclose(dew_point([260,280,300],100),[260,280,300])


def test_partial_stull_budget_signs_units_and_negative_axis_indexes():
    from wrf_tools.diagnostics import tke_budget
    a=np.array([-1.,1.,-1.,1.])[:,None]
    z=np.array([10.,50.,100.]); base=290+.003*z
    u=.01*z+a; v=np.zeros_like(u); w=np.broadcast_to(2*a,u.shape); theta=base+3*a
    result=tke_budget(u,v,w,theta,z,time_axis=-2,vertical_axis=-1)
    np.testing.assert_allclose(result["shear_production"],-.02)
    np.testing.assert_allclose(result["buoyancy_production"],9.80665*6/base)
    np.testing.assert_allclose(result["resolved_tke"],2.5)


def test_rotor_mean_refuses_incomplete_vertical_coverage():
    from wrf_tools.diagnostics import rotor_equivalent_wind_speed
    assert np.isnan(rotor_equivalent_wind_speed([5,8],[50,100],40,150))


def test_json_report_keeps_numbers_and_nonfinite_values_standard(tmp_path):
    from wrf_tools.reporting import write_json_report
    report=json.loads(write_json_report({"integer":np.int64(3),"values":np.array([1,np.nan])},tmp_path/"report.json").read_text())
    assert report=={"integer":3,"values":[1.,None]}


def test_capability_metadata_is_not_mutable_resolver_state():
    from wrf_tools.capabilities import get_capability
    first=capability_catalog(); first["validation.rmse"]["module"]="os"
    assert capability_catalog()["validation.rmse"]["module"]=="validation"
    assert callable(get_capability("validation.rmse"))


def test_wps_lambert_corners_use_wrf_spherical_metric():
    pyproj=pytest.importorskip("pyproj")
    from wrf_tools.wps import domain_geometries,geographic_corners
    domains=domain_geometries({"share":{"max_dom":1},"geogrid":{"e_we":3,"e_sn":3,"dx":1000,"dy":1000}})
    corners=geographic_corners(domains,ref_latitude=52,ref_longitude=5,truelat1=52,truelat2=52,stand_lon=5)[0]
    crs=pyproj.CRS.from_proj4("+proj=lcc +lat_1=52 +lat_2=52 +lat_0=52 +lon_0=5 +R=6370000")
    forward=pyproj.Transformer.from_crs(crs.geodetic_crs,crs,always_xy=True)
    projected=np.array([forward.transform(*p) for p in corners])
    np.testing.assert_allclose(projected,[[-1000,-1000],[1000,-1000],[1000,1000],[-1000,1000]],atol=1e-6)


def test_temporal_spacing_is_used_and_constant_series_has_no_ramps():
    from wrf_tools.spatial import temporal_diagnostics,landuse_statistics
    rates=temporal_diagnostics([1,2,4],spacing=2)
    np.testing.assert_allclose(rates["increment_rate"],[.5,1])
    assert not temporal_diagnostics([1,1,1])["ramp_events"].any()
    summary=landuse_statistics([[1,np.nan]],[[1,1]])[1]
    assert summary["count"]==1 and summary["sample_count"]==2
