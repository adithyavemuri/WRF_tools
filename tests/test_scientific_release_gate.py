"""Independent equations, conservation identities and trusted-library oracles.

These verify declared numerical conventions, not atmospheric realism.
No expected answer is computed by calling a second wrapper around the function
under test.
"""
from math import gamma
from types import SimpleNamespace

import numpy as np
import pytest

from wrf_tools import diagnostics as met
from wrf_tools.filters import butterworth_spatial, spectral_downsample, top_hat_coarsen
from wrf_tools.spectra import power_spectrum, cross_spectrum, welch_spectrum
from wrf_tools.wind_models import von_karman_spectrum, iec_kaimal_spectrum


@pytest.mark.parametrize("component",list("uvw"))
@pytest.mark.parametrize("speed,length,sigma",[(10.,100.,1.),(7.5,31.,2.3),(25.,500.,.4)])
def test_von_karman_literal_published_equation_and_exact_integral(component,speed,length,sigma):
    integrate=pytest.importorskip("scipy.integrate")
    # TurbSim v2 guide printed p.41, Eqs.27-28, inspected in the source PDF.
    frequency=np.array([0.,.001,.03,1.])
    n=frequency*length/speed
    if component=="u":
        expected=4*sigma**2*length/speed/(1+71*n*n)**(5/6)
    else:
        expected=2*sigma**2*length/speed*(1+189*n*n)/(1+71*n*n)**(11/6)
    np.testing.assert_allclose(von_karman_spectrum(frequency,mean_speed=speed,sigma=sigma,length_scale=length,component=component),expected,rtol=1e-14)
    # Closed beta-function integral is a separate mathematical oracle. Published
    # rounded constants are NOT silently renormalized to exactly sigma squared.
    beta=lambda a,b: gamma(a)*gamma(b)/gamma(a+b)
    exact=(2*beta(.5,1/3)/np.sqrt(71) if component=="u" else
           (beta(.5,4/3)+189/71*beta(1.5,1/3))/np.sqrt(71))*sigma**2
    numerical=integrate.quad(lambda f:von_karman_spectrum(f,mean_speed=speed,sigma=sigma,length_scale=length,component=component),0,np.inf,epsabs=1e-10)[0]
    assert numerical==pytest.approx(exact,rel=1e-8)
    assert numerical/sigma**2==pytest.approx(1,rel=.003)


@pytest.mark.parametrize("component",list("uvw"))
def test_spectral_units_and_high_frequency_slope(component):
    f=np.array([.01,.1,1.])
    first=von_karman_spectrum(f,mean_speed=10,sigma=2,length_scale=100,component=component)
    scaled=von_karman_spectrum(3*f,mean_speed=30,sigma=2,length_scale=100,component=component)
    np.testing.assert_allclose(scaled,first/3)
    np.testing.assert_allclose(von_karman_spectrum(f,mean_speed=10,sigma=4,length_scale=100,component=component),4*first)
    high=von_karman_spectrum(np.array([1e4,1e5]),mean_speed=10,sigma=2,length_scale=100,component=component)
    assert np.log10(high[1]/high[0])==pytest.approx(-5/3,abs=1e-9)


@pytest.mark.parametrize("n",[1,2,3,8,9,64,65])
@pytest.mark.parametrize("detrend",[False,True])
def test_periodogram_against_scipy_including_dc_nyquist_and_short_records(n,detrend):
    signal=pytest.importorskip("scipy.signal")
    values=np.random.default_rng(n).normal(size=n)+3
    f,p=power_spectrum(values,spacing=.2,detrend=detrend)
    expected_f,expected=signal.periodogram(values,fs=5,window="boxcar",detrend="constant" if detrend else False)
    np.testing.assert_allclose(f,expected_f)
    np.testing.assert_allclose(p,expected,atol=1e-13)
    assert p.sum()*5/n==pytest.approx(np.mean((values-values.mean())**2) if detrend else np.mean(values**2),abs=1e-12)


@pytest.mark.parametrize("axis",[0,1,-1])
def test_multidimensional_psd_and_welch_against_scipy(axis):
    signal=pytest.importorskip("scipy.signal")
    values=np.random.default_rng(10).normal(size=(17,19))
    f,p=power_spectrum(values,axis=axis,spacing=.5)
    sf,sp=signal.periodogram(values,fs=2,axis=axis)
    np.testing.assert_allclose(f,sf); np.testing.assert_allclose(p,sp,atol=1e-13)
    f,p=welch_spectrum(values,axis=axis,sample_rate=2,nperseg=7,overlap=3)
    sf,sp=signal.welch(values,fs=2,axis=axis,window=np.hanning(7),nperseg=7,noverlap=3)
    np.testing.assert_allclose(f,sf); np.testing.assert_allclose(p,sp,atol=1e-13)


@pytest.mark.parametrize("n",[2,3,16,17])
def test_cross_spectrum_phase_convention_against_scipy(n):
    signal=pytest.importorskip("scipy.signal")
    rng=np.random.default_rng(n); x,y=rng.normal(size=n),rng.normal(size=n)
    f,p=cross_spectrum(x,y,spacing=.2)
    sf,sp=signal.csd(x,y,fs=5,window="boxcar",nperseg=n,noverlap=0)
    # Our documented X*conj(Y) is the conjugate of SciPy's conj(X)*Y.
    np.testing.assert_allclose(f,sf); np.testing.assert_allclose(p,np.conj(sp),atol=1e-13)


def test_butterworth_known_mode_has_declared_half_power_and_complement():
    x=np.arange(32); field=np.broadcast_to(np.cos(2*np.pi*x/8),(16,32))
    low=butterworth_spatial(field,dx=1,cutoff_wavelength=8,order=3)
    high=butterworth_spatial(field,dx=1,cutoff_wavelength=8,order=3,kind="highpass")
    np.testing.assert_allclose(low,field/np.sqrt(2),atol=1e-14)
    np.testing.assert_allclose(high,field/np.sqrt(2),atol=1e-14)
    assert np.sum(low**2+high**2)==pytest.approx(np.sum(field**2))


def test_spatial_reductions_preserve_constant_mean_and_retained_mode_amplitude():
    field=np.random.default_rng(42).normal(size=(12,18))+4
    assert top_hat_coarsen(field,factor_y=3,factor_x=2).mean()==pytest.approx(field.mean())
    x=np.arange(32); mode=np.broadcast_to(7+2*np.cos(2*np.pi*x/16),(16,32))
    coarse=spectral_downsample(mode,factor_y=2)
    np.testing.assert_allclose(coarse,np.broadcast_to(7+2*np.cos(2*np.pi*np.arange(16)/8),(8,16)),atol=1e-13)


def test_thermodynamic_relations_with_independent_numbers_and_units():
    np.testing.assert_allclose(met.potential_temperature([-2,3]),[298,303])
    theta,p=300.,80000.
    assert met.temperature_from_potential(theta,p)==pytest.approx(theta*(p/100000)**(287.05/1004))
    assert met.virtual_temperature(290,.01)==pytest.approx(291.769)
    assert met.air_density(100000,290,.01)==pytest.approx(100000/(287.05*291.769))
    assert met.geopotential_height(981,981)==pytest.approx(200)
    assert met.mixing_ratio_to_specific_humidity(.01)==pytest.approx(.01/1.01)
    assert met.reflectivity_to_rain_rate(10*np.log10(200))==pytest.approx(1)
    assert met.friction_velocity(.3,1.2)==pytest.approx(.5)
    assert met.monin_obukhov_length(300,.5,.1)==pytest.approx(-300*.5**3/(.4*9.80665*.1))
    assert met.convective_velocity_scale(.1,1000,300)==pytest.approx((9.80665*.1*1000/300)**(1/3))
    assert met.convective_velocity_scale(-.1,1000,300)==0
    assert met.bulk_richardson_number(300,302,10,110,5,8,1,5)==pytest.approx(9.80665/301*2*100/25)


def test_log_law_roughness_and_power_law_recover_known_parameters():
    height=np.array([10.,40.,100.,200.]); kappa=.4; ustar=.3; z0=.12
    expected=ustar/kappa*np.log(height/z0)
    np.testing.assert_allclose(met.log_wind_profile(height,friction_velocity_value=ustar,roughness=z0),expected)
    np.testing.assert_allclose(met.roughness_length(expected,height,ustar),z0)
    speed=8*(height/100)**.17
    assert met.power_law_exponent(speed[0],speed[-1],height[0],height[-1])==pytest.approx(.17)
    assert met.wind_power_density([2,4],density=1.2)==pytest.approx(.5*1.2*(8+64)/2)


def test_reynolds_energy_fluxes_and_partial_budget_are_rotation_consistent():
    rng=np.random.default_rng(2)
    u,v,w=rng.normal(size=(3,64,5))
    angle=.73; east=u*np.cos(angle)-v*np.sin(angle); north=u*np.sin(angle)+v*np.cos(angle)
    expected=.5*(u.var(axis=0)+v.var(axis=0)+w.var(axis=0))
    np.testing.assert_allclose(met.resolved_tke(east,north,w),expected)
    np.testing.assert_allclose(met.reynolds_flux(u,w),np.mean((u-u.mean(axis=0))*(w-w.mean(axis=0)),axis=0))
    z=np.array([10.,30.,80.,200.,500.]); fluct=np.array([-1.,1.])[:,None]
    u=.02*z+fluct; v=-.01*z+3*fluct; w=np.broadcast_to(-2*fluct,u.shape)
    theta=np.broadcast_to(290+.003*z,u.shape)
    budget=met.tke_budget(u,v,w,theta,z)
    rotated=met.tke_budget(u*np.cos(angle)-v*np.sin(angle),u*np.sin(angle)+v*np.cos(angle),w,theta,z)
    np.testing.assert_allclose(budget["shear_production"],-.02)
    np.testing.assert_allclose(rotated["shear_production"],budget["shear_production"])
    np.testing.assert_allclose(rotated["resolved_tke"],budget["resolved_tke"])


def test_arbitrary_cartesian_gradient_tensor_and_horizontal_kinematics():
    z,y,x=np.meshgrid(np.arange(4)*3.,np.arange(5)*2.,np.arange(6)*4.,indexing="ij")
    matrix=np.array([[2.,-3.,.5],[4.,-1.,2.],[-.5,1.,-1.]])
    fields=[row[0]*x+row[1]*y+row[2]*z for row in matrix]
    strain=.5*(matrix+matrix.T); rotation=.5*(matrix-matrix.T)
    np.testing.assert_allclose(met.q_criterion(*fields,4,2,3),.5*(np.sum(rotation**2)-np.sum(strain**2)))
    horizontal=met.horizontal_kinematics(fields[0],fields[1],4,2)
    np.testing.assert_allclose(horizontal["divergence"],1.)
    np.testing.assert_allclose(horizontal["vertical_vorticity"],7.)
    np.testing.assert_allclose(horizontal["strain_normal"],3.)
    np.testing.assert_allclose(horizontal["strain_shear"],1.)


@pytest.mark.parametrize("pressure",[70000.,90000.,100000.])
def test_surface_hfx_potential_flux_conversion_is_pressure_consistent(pressure):
    from test_connected_workflows import _synthetic
    from wrf_tools.diagnostic_groups import _thermodynamics
    import matplotlib.pyplot as plt
    ds=_synthetic(); ds.PSFC.values[:]=pressure; ds.T2.values[:]=290
    ds.Q2.values[:]=0; ds.HFX.values[:]=50; ds.UST.values[:]=.3
    fig,arrays,*_=_thermodynamics(ds,SimpleNamespace(x=1,y=1),{})
    plt.close(fig)
    rho=pressure/(287.05*290)
    # theta and theta/T in the mean/flux cancel. This dimensional energy-flux
    # expression is independent of the implementation's potential conversion.
    expected=-rho*1004*290*.3**3/(.4*9.80665*50)
    np.testing.assert_allclose(arrays["monin_obukhov_length"],expected)


def test_report_writers_can_avoid_companion_pdfs(tmp_path,monkeypatch):
    from test_visualization import wrf_dataset
    from wrf_tools.visualization import save_wind_overview
    from wrf_tools.turbulence import save_tke_diagnostics
    # Reuse a declared synthetic WRF-shaped fixture, not observations.
    ds=wrf_dataset.__wrapped__()
    monkeypatch.setattr("wrf_tools.maps.add_cached_features",lambda ax:False)
    cell=SimpleNamespace(x=1,y=1,latitude=52.,longitude=5.)
    paths,_=save_wind_overview(ds,cell,tmp_path/"wind",formats=("png","svg"))
    assert set(paths)=={"png","svg","metadata"}
    import xarray as xr
    dims=("Time","bottom_top","south_north","west_east")
    ds["QKE"]=xr.DataArray(np.full(tuple(ds.sizes[dim] for dim in dims),4.),dims=dims,attrs={"units":"m2 s-2"})
    image,_=save_tke_diagnostics(ds,cell,tmp_path/"tke",formats=("png","svg"))
    assert image.is_file() and not list(tmp_path.glob("*.pdf"))
