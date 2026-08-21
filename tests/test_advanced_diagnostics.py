import numpy as np
import xarray as xr

from wrf_tools.diagnostics import (
    component_spectra, diagnose_pbl_height, fit_spectral_slope, height_agl,
    horizontal_kinematics, integral_time_scale, interpolate_height,
    low_level_jet, precipitation_diagnostics, rotor_equivalent_wind_speed,
    rotor_shear_veer, weibull_fit, wind_power_density,
)
from wrf_tools.quality import quality_control
from wrf_tools.spatial import integral_conservation, landuse_statistics, rotate_vectors, temporal_diagnostics, terrain_metrics


def test_height_rotor_and_resource_diagnostics():
    z=np.array([0.,50.,100.,150.]); speed=np.array([5.,7.,9.,10.]); direction=np.array([350.,355.,2.,5.])
    assert np.allclose(height_agl(z,10),z-10)
    assert np.allclose(interpolate_height(speed,z,[25,125]),[6,9.5])
    assert 7 < rotor_equivalent_wind_speed(speed,z,25,125) < 10
    shear,veer=rotor_shear_veer(speed,direction,z,25,125)
    assert np.isfinite(shear) and abs(veer)<30
    shape,scale=weibull_fit([5,6,7,8,9]); assert shape>0 and scale>0
    assert wind_power_density([5,10])>0


def test_spectra_events_and_flow_diagnostics():
    time=np.arange(256.); u=np.sin(2*np.pi*time/16); zeros=np.zeros_like(u)
    frequency,spectra=component_spectra(u,zeros,zeros,spacing=1); assert spectra["u"].shape==frequency.shape
    slope,_=fit_spectral_slope(np.array([1,2,4,8.]),np.array([1,2,4,8.])**(-5/3)); assert np.isclose(slope,-5/3)
    scale,_=integral_time_scale(u); assert scale>0
    y,x=np.mgrid[:5,:5]; flow=horizontal_kinematics(x,-y,1,1); assert np.allclose(flow["divergence"],0)
    jet=low_level_jet([3,10,6],[10,100,300]); assert bool(jet["detected"])
    rain=precipitation_diagnostics([0,1,3],[0,0,1]); assert rain["increment"].tolist()==[0,1,3]


def test_qc_spatial_and_temporal(capsys):
    ds=xr.Dataset({"T2":(("Time","y","x"),np.array([[[290.]],[[500.]],[[291.]]]))},coords={"XTIME":("Time",np.array([0.,60.,120.]))})
    issues=quality_control(ds); assert any(item.variable=="T2" and item.check=="physical-range" for item in issues)
    terrain=terrain_metrics(np.array([[0.,1.],[0.,1.]]),1,1); assert np.all(terrain["slope"]>0)
    assert landuse_statistics([[1.,2.]],[[1,2]])[1]["mean"]==1
    assert np.isclose(integral_conservation([1,1],[1,1],2,2)["relative_error"],0)
    ru,rv=rotate_vectors(1,0,90); assert np.allclose([ru,rv],[0,1],atol=1e-12)
    assert "ramp_events" in temporal_diagnostics([1,2,8])
