"""Chapter 1: equations, filters, spectra, means and comparisons.

All inputs here are small synthetic arrays with declared units/coordinates.
The showcase tests connectivity. Analytical assertions live in tests/.
"""
import numpy as np
import xarray as xr


def run(c):
    call=c.call
    time=np.arange(64.)
    signal=8+np.sin(2*np.pi*time/8)
    height=np.array([10.,50.,100.,200.])
    u=signal[:,None]+.01*height
    v=np.cos(time[:,None]/4)+np.zeros_like(u)
    w=.2*np.sin(time[:,None]/3)+np.zeros_like(u)
    theta=290+.01*height+np.sin(time[:,None]/5)
    z=np.broadcast_to(height,u.shape)

    # Atmospheric state and surface-layer relations. K, Pa, kg/kg, m, m/s.
    prefix="diagnostics.meteorology."
    cases={
        "potential_temperature":([0,1],),"temperature_from_potential":([300,301],[100000,90000]),
        "virtual_temperature":([290,291],[.005,.006]),"air_density":([100000,90000],[290,285],[.005,.006]),
        "geopotential_height":([0,981],[0,0]),
        "bulk_richardson_number":(290,291,10,100,5,8,0,1),
        "power_law_exponent":(5,8,10,100),"interval_precipitation":([0,1,3],),
        "reflectivity_to_rain_rate":([10,20],),"friction_velocity":([.1,.2],1.225),
        "monin_obukhov_length":(290,.3,.05),"circular_mean":([350,10],),
        "roughness_length":(8,100,.3),"log_wind_profile":(height,),
        "mixing_ratio_to_specific_humidity":([.005,.006],),
    }
    for name,args in cases.items():
        kwargs=dict(friction_velocity_value=.3,roughness=.1) if name=="log_wind_profile" else {}
        call(prefix+name,*args,**kwargs)
    for name,args in {"wind_speed":(u,v),"wind_direction":(u,v),
        "wind_speed_direction_to_uv":([5,8],[270,180]),"angle_between":([1,0],[0,1])}.items():
        call("diagnostics.wind."+name,*args)
    for name,args in {"fluctuations":(u,),"resolved_tke":(u,v,w),
        "reynolds_flux":(u,w),"turbulence_intensity":(u,)}.items():
        call("diagnostics.turbulence."+name,*args)

    prefix="diagnostics.advanced."
    # Profile diagnostics need the vertical axis explicitly: this array is (time,z).
    call(prefix+"height_agl",height+10,10)
    call(prefix+"interpolate_height",u,z,[40,80],axis=1)
    call(prefix+"stability_class",[-300,-100,-10,10,100,300,np.inf,np.nan])
    call(prefix+"diagnose_pbl_height",theta,z,axis=1)
    call(prefix+"convective_velocity_scale",.05,500,290)
    call(prefix+"rotor_equivalent_wind_speed",u,z,40,150,axis=1)
    call(prefix+"rotor_shear_veer",u,np.full_like(u,270),z,40,150,axis=1)
    call(prefix+"weibull_fit",signal)
    call(prefix+"wind_power_density",signal)
    f,p=call(prefix+"component_spectra",signal,signal*.2,signal*.1,spacing=1)
    call(prefix+"premultiplied_spectrum",f,p["u"])
    call(prefix+"fit_spectral_slope",[1,2,4,8],np.array([1,2,4,8])**(-5/3))
    call(prefix+"integral_time_scale",signal)
    call(prefix+"dew_point",290,70)
    call(prefix+"relative_humidity",290,100000,.005)
    call(prefix+"equivalent_potential_temperature",290,100000,.005)
    # These levels are intentionally uneven: derivatives use their physical
    # spacing, not a difference in index space divided by a height difference.
    call(prefix+"brunt_vaisala_frequency",theta,z,axis=1)
    call(prefix+"inversion_layers",theta,z,axis=1)
    call(prefix+"tke_budget",u,v,w,theta,z)
    zz,yy,xx=np.mgrid[:3,:8,:8].astype(float)
    call(prefix+"horizontal_kinematics",-yy[0],xx[0],1,1)
    call(prefix+"q_criterion",-yy,xx,np.zeros_like(xx),1,1,1)
    call(prefix+"low_level_jet",[4,10,6],[10,100,300])
    call(prefix+"precipitation_diagnostics",[0,1,2],[0,0,1])
    missing_rain=call(prefix+"precipitation_diagnostics",[0,np.nan,2],[0,0,0])
    assert np.isnan(missing_rain["total"])  # do not publish a partial total

    # Explicit sampling. The time spacing here is 1 s, NOT the real hourly case.
    f,p=call("spectra.power_spectrum",signal,spacing=1)
    call("spectra.welch_spectrum",signal,sample_rate=1,nperseg=16,overlap=8)
    call("spectra.cross_spectrum",signal,np.roll(signal,1),spacing=1)
    call("spectra.coherence",signal,np.roll(signal,1),sample_rate=1,nperseg=16,overlap=8)
    call("spectra.log_bin",f,p,bins=5)
    field=np.sin(xx[0])+np.cos(yy[0])
    call("spectra.radial_wavenumber_spectrum",field,dx=10)
    smooth=call("filters.butterworth_spatial",field,dx=10,cutoff_wavelength=40)
    call("filters.resolved_subfilter",field,smooth)
    call("filters.butterworth_band",field,dx=10,low_wavelength=20,high_wavelength=60)
    call("filters.top_hat_coarsen",field,factor_y=2)
    call("filters.spectral_downsample",field,factor_y=2)

    # Generic skill scores: pairs are finite and co-located before comparison.
    for name in ("bias","mae","rmse","normalized_error","correlation","comparison_summary","spatial_scores"):
        call("validation."+name,[1.,2.,3.],[1.,2.5,4.])
    call("validation.circular_error",[1,359],[359,1])
    call("validation.circular_mae",[1,359],[359,1])
    call("validation.kantorovich_distance",[0,1],[0,2,4])
    call("validation.standard_error",signal)
    call("validation.cluster_profiles",[[1,2],[1,2.1],[8,9],[8,9.1]],2,seed=1)
    call("validation.rank_cases",{"baseline":[1,2],"test":[2,3]},[1,2])
    for name,args in {"terrain_metrics":(field,10,10),"speed_up_ratio":(signal,8),
        "landuse_statistics":(field,(xx[0]%3).astype(int)),"resolution_metrics":(field,smooth),
        "boundary_discontinuity":(field,),"integral_conservation":(field,field,100,100),
        "rotate_vectors":(1,0,30),"temporal_diagnostics":(signal,),"diurnal_cycle":(signal,time%24)}.items():
        call("spatial."+name,*args)
    for name,kwargs in {
        "kaimal_spectrum":dict(mean_speed=10,height=100,friction_velocity=.4),
        "von_karman_spectrum":dict(mean_speed=10,sigma=1,length_scale=100),
        "iec_kaimal_spectrum":dict(mean_speed=10,sigma=1,length_scale=100),
        "cheynet_spectrum":dict(mean_speed=10,height=81.5,friction_velocity=.4),
    }.items(): call("wind_models."+name,[.01,.1,1],**kwargs)
    call("wind_models.exponential_coherence",[.01,.1,1],10,mean_speed=10)
    call("wind_models.synthetic_wind_field",10,nt=8,ny=4,nz=3,dt=1,dy=10,dz=10,seed=2)

    # Labelled weighted reductions, not implicit averaging on mixed coordinates.
    a=xr.DataArray(u,dims=("Time","bottom_top"),attrs={"units":"m s-1"})
    physical=xr.DataArray(z,dims=a.dims)
    call("averaging.mean",a,"Time",weighting="uniform")
    call("averaging.to_height",a,physical,[40,80,150],reference="AGL")
    call("averaging.layer_thickness",xr.DataArray([0,50,150,400],dims="bottom_top_stag"),40,200)
