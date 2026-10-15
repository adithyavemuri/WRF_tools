"""Connected WRF diagnostics: scientific choices and missing inputs stay visible."""
from __future__ import annotations

from pathlib import Path
import numpy as np

from . import diagnostics as met
from .diagnostics.advanced import _vertical_gradient
from .grid import destagger
from .visualization import history_times, mass_heights, temperature_celsius, rotate_wind

DIAGNOSTIC_REFERENCES={
    "stull":{"title":"Stull (1988), An Introduction to Boundary Layer Meteorology: Richardson number and partial TKE budget",
             "url":"https://doi.org/10.1007/978-94-009-3027-8"},
    "q_criterion":{"title":"Hunt, Wray and Moin (1988), Eddies, streams, and convergence zones in turbulent flows",
                   "url":"https://ntrs.nasa.gov/citations/19890015184"},
    "welch":{"title":"Welch (1967), Power spectra from modified periodograms",
             "url":"https://doi.org/10.1109/TAU.1967.1161901"},
    "pope":{"title":"Pope (2000), Turbulent Flows: resolved Reynolds covariances",
            "url":"https://doi.org/10.1017/CBO9780511840531"},
    "rotor":{"title":"Wagner et al. (2014), Rotor-equivalent wind speed; this package uses a uniform-height approximation",
             "url":"https://doi.org/10.1088/1742-6596/524/1/012108"},
    "weibull":{"title":"Justus et al. (1978), Methods for estimating wind speed frequency distributions",
               "url":"https://doi.org/10.1175/1520-0450(1978)017<0350:MFEWSF>2.0.CO;2"},
}

class _Unavailable(Exception):
    pass


def _columns(ds, cell):
    point = dict(south_north=cell.y, west_east=cell.x)
    height = mass_heights(ds.PH.isel(point), ds.PHB.isel(point), ds.HGT.isel(point), axis=1, agl=True)
    u = np.asarray(ds.U.isel(south_north=cell.y, west_east_stag=slice(cell.x, cell.x+2))).mean(axis=-1)
    v = np.asarray(ds.V.isel(south_north_stag=slice(cell.y, cell.y+2), west_east=cell.x)).mean(axis=-1)
    return point, height, u, v


def _thermodynamics(ds, cell, options):
    import matplotlib.pyplot as plt
    point, z, u, v = _columns(ds, cell)
    theta = met.potential_temperature(ds.T.isel(point))
    pressure = np.asarray(ds.P.isel(point)+ds.PB.isel(point))
    temperature = temperature_celsius(ds.T.isel(point), pressure)+273.15
    mixing = np.asarray(ds.QVAPOR.isel(point))
    theta_v = met.virtual_temperature(theta, mixing)
    ri = met.bulk_richardson_number(theta_v[:,:-1],theta_v[:,1:],z[:,:-1],z[:,1:],u[:,:-1],u[:,1:],v[:,:-1],v[:,1:])
    n2 = 9.80665/theta_v*_vertical_gradient(theta_v,z,axis=1)
    n = met.brunt_vaisala_frequency(theta_v,z,axis=1)
    rh = met.relative_humidity(temperature,pressure,mixing)
    density = met.air_density(pressure,temperature,mixing)
    dewpoint = met.dew_point(temperature,rh)
    theta_e = met.equivalent_potential_temperature(temperature,pressure,mixing)
    inversion = met.inversion_layers(temperature,z,axis=1)
    pbl = met.diagnose_pbl_height(theta_v,z,axis=1)
    surface_p=np.asarray(ds.PSFC.isel(point)); surface_t=np.asarray(ds.T2.isel(point))
    surface_q=np.asarray(ds.Q2.isel(point))
    surface_rho=met.air_density(surface_p,surface_t,surface_q)
    theta2=surface_t*(100000/surface_p)**(287.05/1004.)
    theta2v=met.virtual_temperature(theta2,surface_q)
    # HFX/(rho*cp) is w'T', not w'theta'. At fixed surface pressure,
    # dtheta/dT=theta/T. The same potential-temperature convention must be
    # used in the mean and flux in L and w* (Stull's surface-buoyancy relation).
    kinematic=np.asarray(ds.HFX.isel(point))/(surface_rho*1004.)*theta2/surface_t
    virtual_flux=(1+.61*surface_q)*kinematic
    if "QFX" in ds:
        virtual_flux += .61*theta2*np.asarray(ds.QFX.isel(point))/surface_rho
    length=met.monin_obukhov_length(theta2v,ds.UST.isel(point),virtual_flux)
    convective=met.convective_velocity_scale(virtual_flux,ds.PBLH.isel(point),theta2v)
    time=np.array(history_times(ds),dtype="datetime64[s]")
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout="constrained")
    visible=z[-1]<=float(options.get("profile_top_metres",2000))
    mid=.5*(z[-1,:-1]+z[-1,1:]); keep=mid<=float(options.get("profile_top_metres",2000))
    axes[0,0].plot(ri[-1,keep],mid[keep]); axes[0,0].axvline(0,color="0.5",lw=.7)
    axes[0,0].set(xlabel="Bulk Richardson number",ylabel="Height AGL (m)",title="Stull: adjacent-layer bulk Richardson number")
    axes[0,1].plot(n2[-1,visible],z[-1,visible]); axes[0,1].axvline(0,color="0.5",lw=.7)
    axes[0,1].set(xlabel="N² (s⁻²); negative retained",ylabel="Height AGL (m)",title="Virtual-potential-temperature stability")
    axes[1,0].plot(time,length,marker="o"); axes[1,0].axhline(0,color="0.5",lw=.7)
    axes[1,0].set(xlabel="Saved time (UTC)",ylabel="L (m)",title="Monin–Obukhov length (surface-flux approximation)")
    axes[1,1].plot(time,convective,marker="o")
    axes[1,1].set(xlabel="Saved time (UTC)",ylabel="w* (m/s)",title="Convective velocity scale")
    for ax in axes.flat: ax.grid(alpha=.2)
    return fig,dict(height_agl=z,bulk_richardson=ri,n2=n2,n_clipped=n,relative_humidity=rh,
        density=density,dewpoint_K=dewpoint,theta_e_screening=theta_e,inversion=inversion,
        diagnosed_pbl=pbl,monin_obukhov_length=length,convective_velocity=convective,
        stability_class=met.stability_class(length)),"Stull bulk Ri and surface-flux similarity diagnostics. HFX/(rho cp) is converted to potential-temperature flux using theta/T before virtual-flux correction. Approximate virtual temperature neglects condensate. theta-e is a simplified screening formula; N² retains instability. Not a closed TKE budget.",[
        "diagnostics.meteorology.bulk_richardson_number","diagnostics.meteorology.monin_obukhov_length",
        "diagnostics.meteorology.virtual_temperature","diagnostics.advanced.brunt_vaisala_frequency",
        "diagnostics.advanced.dew_point","diagnostics.advanced.relative_humidity","diagnostics.advanced.equivalent_potential_temperature",
        "diagnostics.advanced.inversion_layers","diagnostics.advanced.diagnose_pbl_height","diagnostics.advanced.convective_velocity_scale"]


def _wind_resource(ds,cell,options):
    import matplotlib.pyplot as plt
    point,z,u,v=_columns(ds,cell)
    if "COSALPHA" not in ds or "SINALPHA" not in ds:
        raise _Unavailable("Earth-relative rotation fields are needed for rotor veer")
    u,v=rotate_wind(u,v,np.asarray(ds.COSALPHA.isel(point))[:,None],np.asarray(ds.SINALPHA.isel(point))[:,None])
    speed=met.wind_speed(u,v); direction=met.wind_direction(u,v)
    lower,upper=float(options.get("rotor_bottom_metres",40)),float(options.get("rotor_top_metres",200))
    if not 0<lower<upper: raise ValueError("Choose positive increasing rotor bounds")
    covered=(z[:,0]<=lower)&(z[:,-1]>=upper)
    equivalent=met.rotor_equivalent_wind_speed(speed,z,lower,upper,axis=1)
    shear,veer=met.rotor_shear_veer(speed,direction,z,lower,upper,axis=1)
    equivalent,shear,veer=[np.where(covered,item,np.nan) for item in (equivalent,shear,veer)]
    jet=met.low_level_jet(speed[-1],z[-1])
    surface=np.hypot(ds.U10.isel(point),ds.V10.isel(point)).values
    shape,scale=met.weibull_fit(surface)
    time=np.array(history_times(ds),dtype="datetime64[s]")
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout="constrained")
    for ax,values,title,ylabel in zip(axes.flat,(equivalent,shear,veer,surface),
        ("Rotor-equivalent wind (uniform-height approximation)","Rotor-layer power-law shear","Earth-relative rotor veer","10 m wind: sampled period, not a climatology"),
        ("Speed (m/s)","Shear exponent","Veer (degrees)","Speed (m/s)")):
        ax.plot(time,values,marker="o"); ax.set(title=title,ylabel=ylabel,xlabel="UTC"); ax.grid(alpha=.2)
    return fig,dict(rotor_equivalent_speed=equivalent,rotor_shear=shear,rotor_veer=veer,
        complete_rotor_coverage=covered,jet_detected=jet["detected"],jet_height=jet["core_height"],
        weibull_shape=shape,weibull_scale=scale),f"Research screening over {lower:g}–{upper:g} m AGL; incomplete columns excluded. Rotor speed uses uniform-height, not disk-area weights. Short-period Weibull estimates are not long-term resource estimates.",[
        "diagnostics.advanced.rotor_equivalent_wind_speed","diagnostics.advanced.rotor_shear_veer",
        "diagnostics.advanced.low_level_jet","diagnostics.advanced.weibull_fit"]


def _map_panels(ds,items,title):
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    from .visualization import geographic_axis
    fig=plt.figure(figsize=(12,8),layout="constrained")
    slots=fig.add_gridspec(2,2)
    for index,(name,values,label,cmap) in enumerate(items):
        ax,_=geographic_axis(fig,slots[index//2,index%2],ds)
        values=np.asarray(values)
        color_options={}
        if cmap in {"RdBu_r","PuOr"} and np.isfinite(values).any():
            limit=max(float(np.nanmax(np.abs(values))),np.finfo(float).eps)
            color_options=dict(vmin=-limit,vmax=limit)
        artist=ax.pcolormesh(ds.XLONG.isel(Time=0),ds.XLAT.isel(Time=0),values,
            transform=ccrs.PlateCarree(),shading="auto",cmap=cmap,rasterized=True,**color_options)
        ax.set_title(name,fontsize=10); fig.colorbar(artist,ax=ax,label=label,shrink=.8)
    fig.suptitle(title,fontsize=14)
    return fig


def _flow_structure(ds,cell,options):
    import xarray as xr
    from .averaging import to_height
    heights=np.asarray(options.get("flow_heights_metres",[200,400,600,800,1000]),float)
    if heights.size<3 or np.any(np.diff(heights)<=0) or not np.allclose(np.diff(heights),np.diff(heights)[0]):
        raise ValueError("flow_heights_metres needs at least three increasing, equally spaced MSL heights")
    frame=ds.isel(Time=-1,drop=True)
    z=mass_heights(frame.PH,frame.PHB,axis=0)
    sampled=[]
    for name,dimension in (("U","west_east_stag"),("V","south_north_stag"),("W","bottom_top_stag")):
        field=destagger(frame[name],dimension).reset_coords(drop=True).transpose("bottom_top","south_north","west_east")
        physical=xr.DataArray(z,dims=field.dims,coords=field.coords)
        sampled.append(to_height(field,physical,heights,reference="MSL").transpose("height","south_north","west_east").values)
    dx,dy=float(ds.attrs["DX"]),float(ds.attrs["DY"])
    u,v,w=sampled
    q=met.q_criterion(u,v,w,dx,dy,float(np.diff(heights)[0]))
    flow=met.horizontal_kinematics(u[0],v[0],dx,dy)
    if not np.isfinite(q).any(): raise _Unavailable("No supported Cartesian Q samples at the selected MSL heights")
    fig=_map_panels(ds,[("Vertical vorticity",flow["vertical_vorticity"],"s⁻¹","RdBu_r"),
        ("Horizontal divergence",flow["divergence"],"s⁻¹","RdBu_r"),
        ("Q criterion",q[0],"s⁻²","PuOr"),("Horizontal speed",np.hypot(u[0],v[0]),"m/s","viridis")],
        f"Final flow structure at {heights[0]:g} m MSL | Cartesian approximation")
    return fig,dict(q_criterion=q,heights_msl=heights,**flow),"Wind interpolated to uniformly spaced MSL planes without extrapolation. Q/vorticity/divergence use nominal DX/DY Cartesian derivatives; projection metrics and varying grid basis are neglected. This approximation is explicit, not an exact WRF metric-aware operator.",[
        "diagnostics.advanced.q_criterion","diagnostics.advanced.horizontal_kinematics"]


def _spatial(ds,cell,options):
    from .spatial import terrain_metrics,landuse_statistics,boundary_discontinuity,speed_up_ratio
    terrain=np.asarray(ds.HGT.isel(Time=0)); dx,dy=float(ds.attrs["DX"]),float(ds.attrs["DY"])
    metrics=terrain_metrics(terrain,dx,dy)
    speed=np.hypot(ds.U10.isel(Time=-1),ds.V10.isel(Time=-1)).values
    ratio=speed_up_ratio(speed,np.nanmean(speed))
    temperature=np.asarray(ds.T2.isel(Time=-1))
    land=landuse_statistics(temperature,ds.LU_INDEX.isel(Time=0)) if "LU_INDEX" in ds else {}
    edge=boundary_discontinuity(temperature)
    fig=_map_panels(ds,[("Terrain slope",metrics["slope_degrees"],"degrees","viridis"),
        ("Terrain aspect",metrics["aspect"],"degrees","twilight"),
        ("Wind speed-up relative to domain mean",ratio,"ratio","viridis"),
        ("Land-use index" if "LU_INDEX" in ds else "Terrain (land use unavailable)",ds.LU_INDEX.isel(Time=0) if "LU_INDEX" in ds else terrain,"index" if "LU_INDEX" in ds else "m","tab20")],"Terrain, land-use and wind exposure")
    arrays=dict(**metrics,speed_up=ratio,**{f"edge_{k}":v for k,v in edge.items()})
    arrays.update({f"landuse_{category}_{name}":value for category,stats in land.items() for name,value in stats.items()})
    return fig,arrays,"Nominal-grid terrain derivatives. Speed-up uses the instantaneous unweighted domain-mean speed as a reference, not a paired control simulation. Land-use numbers are categorical codes.",[
        "spatial.terrain_metrics","spatial.landuse_statistics","spatial.boundary_discontinuity","spatial.speed_up_ratio"]


def _spectral(ds,cell,options):
    import matplotlib.pyplot as plt
    from .filters import butterworth_spatial,butterworth_band,top_hat_coarsen,spectral_downsample,resolved_subfilter
    from .spectra import power_spectrum,welch_spectrum,cross_spectrum,coherence,log_bin,radial_wavenumber_spectrum
    from .spatial import integral_conservation,resolution_metrics
    from .grid import regrid_regular
    time=np.array(history_times(ds),dtype="datetime64[s]")
    if len(time)<6: raise _Unavailable("Connected Welch/coherence panels need at least six saved samples; basic spectra remain callable separately")
    step=np.diff(time.astype("int64"))
    if not np.all(step==step[0]): raise _Unavailable("Selected temporal spectra require regular timestamps")
    series=np.asarray(ds.U10.isel(south_north=cell.y,west_east=cell.x))
    other=np.asarray(ds.V10.isel(south_north=cell.y,west_east=cell.x))
    spacing=step[0]/3600; frequency,power=power_spectrum(series,spacing=spacing)
    count=min(16,max(3,len(series)//2)); fw,pw=welch_spectrum(series,sample_rate=1/spacing,nperseg=count,overlap=count//2)
    fc,cross=cross_spectrum(series,other,spacing=spacing)
    fcoh,coh=coherence(series,other,sample_rate=1/spacing,nperseg=count,overlap=count//2)
    fb,pb=log_bin(frequency,power,bins=max(2,min(10,len(frequency))))
    field=np.asarray(ds.T2.isel(Time=-1)); dx,dy=float(ds.attrs["DX"]),float(ds.attrs["DY"])
    cutoff=float(options.get("filter_cutoff_metres",6*max(dx,dy)))
    filtered=butterworth_spatial(field,dx=dx,dy=dy,cutoff_wavelength=cutoff)
    _,residual=resolved_subfilter(field,filtered)
    band=butterworth_band(field,dx=dx,dy=dy,low_wavelength=4*max(dx,dy),high_wavelength=16*max(dx,dy))
    coarse=top_hat_coarsen(field,factor_y=2,trim=True)
    spectral=spectral_downsample(field,factor_y=2)
    ky,kp=radial_wavenumber_spectrum(field,dx=dx,dy=dy)
    # The coarse coordinates are block centres; compare only within that extent.
    cy,cx=coarse.shape; tx=np.arange(cx)*2+.5; ty=np.arange(cy)*2+.5
    target_x=np.arange(1,2*cx-1); target_y=np.arange(1,2*cy-1)
    restored=regrid_regular(coarse,tx,ty,target_x,target_y)
    conservation=integral_conservation(field[:cy*2,:cx*2],coarse,dx*dy,4*dx*dy)
    resolution=resolution_metrics(field[1:2*cy-1,1:2*cx-1],restored)
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout="constrained")
    for freq,values,label in ((frequency,power,"Periodogram"),(fw,pw,"Welch")):
        valid=(freq>0)&(values>0); axes[0,0].loglog(freq[valid],values[valid],label=label)
    axes[0,0].set(xlabel="Frequency (h⁻¹)",ylabel="PSD ((m/s)² h)",title="Sampled weather variability—not LES turbulence")
    axes[0,0].legend(); valid=(ky>0)&(kp>0)
    axes[0,1].loglog(ky[valid]*1000,kp[valid]); axes[0,1].set(xlabel="Wavenumber (km⁻¹)",ylabel="Binned temperature spectral power",title="Spatial temperature spectrum")
    axes[1,0].plot(fcoh,coh); axes[1,0].set(xlabel="Frequency (h⁻¹)",ylabel="Coherence",title="U10/V10 coherence (short-record screening)")
    axes[1,1].plot(frequency,met.premultiplied_spectrum(frequency,power)); axes[1,1].set(xlabel="Frequency (h⁻¹)",ylabel="f × PSD ((m/s)²)",title="Premultiplied sampled spectrum")
    for ax in axes.flat: ax.grid(alpha=.2)
    return (fig,dict(frequency=frequency,power=power,welch_frequency=fw,welch_power=pw,cross_spectrum=cross,
        coherence=coh,log_frequency=fb,log_power=pb,spatial_wavenumber=ky,spatial_power=kp,
        filtered=filtered,residual=residual,band=band,coarse=coarse,spectral_coarse=spectral,
        **{f"conservation_{k}":v for k,v in conservation.items()},**{f"resolution_{k}":v for k,v in resolution.items()}),
        "Temporal spectra describe the selected sampling/period only. No -5/3 turbulent-range claim is made. FFT spatial filters assume periodic boundaries. Coherence from few samples is poorly constrained. Coarsened arrays and conservation diagnostics are saved with the spectra.",[
        "spectra.power_spectrum","spectra.welch_spectrum","spectra.cross_spectrum","spectra.coherence","spectra.log_bin",
        "filters.butterworth_spatial","filters.butterworth_band","filters.top_hat_coarsen","filters.spectral_downsample",
        "spatial.integral_conservation","spatial.resolution_metrics"])


def _turbulence(ds,cell,options):
    import matplotlib.pyplot as plt
    from .les import calculate_fluxes,calculate_total_tke
    average=options.get("turbulence_average","none")
    if average not in {"time","none"}: raise ValueError("turbulence_average must be none or time")
    if average != "time":
        raise _Unavailable("Choose turbulence_average='time' and appropriate sampling/window explicitly; hourly weather variance is not silently labelled TKE")
    times=np.array(history_times(ds),dtype="datetime64[s]")
    minimum=int(options.get("minimum_turbulence_samples",32))
    max_interval=float(options.get("max_turbulence_interval_seconds",60))
    if minimum<2 or not np.isfinite(max_interval) or max_interval<=0:
        raise ValueError("Turbulence sampling needs >=2 samples and a positive finite maximum interval")
    if len(times)<max(2,minimum) or np.max(np.diff(times.astype("int64")))>max_interval:
        raise _Unavailable(f"Researcher-selected turbulence policy requires >= {minimum} samples and intervals <= {max_interval:g} s")
    point,z,u,v=_columns(ds,cell)
    w=np.asarray(destagger(ds.W.isel(point),"bottom_top_stag"))
    theta=met.potential_temperature(ds.T.isel(point))
    flux=calculate_fluxes(u,v,w,axis=0)
    budget=met.tke_budget(u,v,w,theta,z)
    resolved=calculate_total_tke(u,v,w,axis=0)
    fig,axes=plt.subplots(1,3,figsize=(12,6),layout="constrained")
    height=z.mean(axis=0)
    axes[0].plot(resolved,height); axes[0].set(xlabel="Resolved variance energy (m²/s²)",ylabel="Mean mass height AGL (m)")
    axes[1].plot(flux["uw"],height,label="u'w'"); axes[1].plot(flux["vw"],height,label="v'w'"); axes[1].legend(); axes[1].set(xlabel="Resolved momentum covariance (m²/s²)")
    for key in ("shear_production","buoyancy_production"): axes[2].plot(budget[key],height,label=key.replace("_"," "))
    axes[2].legend(fontsize=8); axes[2].set(xlabel="Partial budget terms (m²/s³)")
    for ax in axes: ax.grid(alpha=.2)
    fig.suptitle("User-selected time averaging | Stull partial budget, not closure")
    return fig,dict(resolved_tke=resolved,**flux,**{f"budget_{k}":v for k,v in budget.items()}),"Time average over selected records at native levels. Buoyancy term uses dry potential temperature; moisture/condensate buoyancy is omitted. Researcher must justify stationarity and sampling. No transport, pressure-correlation, dissipation or SGS closure; no claim that resolved variance equals total model TKE.",[
        "les.diagnostics.calculate_fluxes","les.diagnostics.calculate_total_tke","diagnostics.advanced.tke_budget"]


_GROUPS={"thermodynamics":_thermodynamics,"wind_resource":_wind_resource,"flow_structure":_flow_structure,
         "spatial":_spatial,"spectral":_spectral,"turbulence":_turbulence}
_REQUIRED={
    "thermodynamics":"U V PH PHB HGT T P PB QVAPOR PSFC T2 Q2 HFX UST PBLH",
    "wind_resource":"U V PH PHB HGT U10 V10 COSALPHA SINALPHA",
    "flow_structure":"U V W PH PHB XLAT XLONG",
    "spatial":"HGT U10 V10 T2 XLAT XLONG",
    "spectral":"U10 V10 T2",
    "turbulence":"U V W PH PHB HGT T",
}


def run_diagnostic_groups(dataset,cell,output_directory,*,domain="d01",groups="all",options=None):
    """Run selected connected groups and visibly report unmet prerequisites.

    Every group is listed even when not selected. Missing input is UNAVAILABLE;
    numerical/configuration errors propagate instead of being hidden. External-
    data capabilities are executable via run-recipe, not fabricated here.
    """
    import matplotlib.pyplot as plt
    selected=set(_GROUPS) if groups=="all" else (set() if groups=="none" else set(groups.split(",") if isinstance(groups,str) else groups))
    if not selected<=set(_GROUPS): raise ValueError(f"Unknown groups: {sorted(selected-set(_GROUPS))}")
    options=options or {}
    allowed={"profile_top_metres","rotor_bottom_metres","rotor_top_metres","flow_heights_metres",
        "filter_cutoff_metres","turbulence_average","minimum_turbulence_samples","max_turbulence_interval_seconds"}
    if set(options)-allowed: raise ValueError(f"Unknown diagnostic options: {sorted(set(options)-allowed)}")
    output=Path(output_directory); output.mkdir(parents=True,exist_ok=True)
    results={}
    for name,function in _GROUPS.items():
        if name not in selected:
            results[name]=dict(status="NOT_SELECTED",reason="Not selected by the researcher"); continue
        missing=set(_REQUIRED[name].split())-set(dataset.variables)
        if missing:
            results[name]=dict(status="UNAVAILABLE",reason=f"Missing WRF variables: {', '.join(sorted(missing))}"); continue
        try:
            figure,arrays,note,functions=function(dataset,cell,options)
        except (KeyError,_Unavailable,ImportError) as exc:
            results[name]=dict(status="UNAVAILABLE",reason=str(exc)); continue
        prefix=output/f"{domain}_analysis_{name}"
        try:
            figure.savefig(prefix.with_suffix(".png"),dpi=180)
            figure.savefig(prefix.with_suffix(".svg"))
        finally:
            plt.close(figure)
        np.savez(prefix.with_suffix(".npz"),**arrays)
        results[name]=dict(status="COMPLETE",figure=prefix.with_suffix(".png").name,
            data=prefix.with_suffix(".npz").name,functions=functions,methods=note,
            data_arrays={key:dict(shape=list(np.shape(value)),dtype=str(np.asarray(value).dtype)) for key,value in arrays.items()})
    return results
