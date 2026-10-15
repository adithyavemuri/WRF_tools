"""Advanced atmospheric, wind-energy, turbulence, and event diagnostics."""
from __future__ import annotations
import numpy as np

G=9.80665; RD=287.05; CP=1004.0; LV=2.5e6

def _vertical_gradient(values, height, *, axis=0):
    """Column-wise nonuniform three-point derivative; first-order edges.

    Uses the nonuniform finite-difference weights documented by numpy.gradient.
    A shared 1-D height vector or co-located column heights are accepted.
    Missing field values propagate; heights must be finite and increasing.
    """
    data = np.asarray(values, float)
    z = np.asarray(height, float)
    if z.ndim == 1 and data.ndim > 1:
        shape = [1] * data.ndim
        shape[axis] = z.size
        z = np.broadcast_to(z.reshape(shape), data.shape)
    if z.shape != data.shape:
        raise ValueError("Values and heights must be co-located or use a shared 1-D height vector")
    data, z = np.moveaxis(data, axis, 0), np.moveaxis(z, axis, 0)
    dz = np.diff(z, axis=0)
    if len(z) < 2 or not np.isfinite(z).all() or np.any(dz <= 0):
        raise ValueError("Heights must be finite and strictly increasing with at least two levels")
    slopes = np.diff(data, axis=0) / dz
    result = np.empty_like(data)
    result[0], result[-1] = slopes[0], slopes[-1]
    result[1:-1] = (dz[1:] * slopes[:-1] + dz[:-1] * slopes[1:]) / (dz[:-1] + dz[1:])
    return np.moveaxis(result, 0, axis)

def height_agl(height_msl, terrain):
    """Subtract co-located terrain metres from MSL height to obtain AGL height."""
    return np.asarray(height_msl)-np.asarray(terrain)

def interpolate_height(values, height, target_heights, *, axis=0):
    """Linear co-located column interpolation; no extrapolation or NaN bridging."""
    data=np.moveaxis(np.asarray(values,float),axis,0); z=np.moveaxis(np.asarray(height,float),axis,0)
    if data.shape!=z.shape or not np.isfinite(z).all() or np.any(np.diff(z,axis=0)<=0):
        raise ValueError("Values/heights must be co-located; heights finite and strictly increasing")
    targets=np.atleast_1d(target_heights).astype(float); result=np.empty((targets.size,)+data.shape[1:])
    for index in np.ndindex(data.shape[1:]): result[(slice(None),)+index]=np.interp(targets,z[(slice(None),)+index],data[(slice(None),)+index],left=np.nan,right=np.nan)
    return np.moveaxis(result,0,axis)

def stability_class(monin_length):
    """Legacy length-threshold screening labels, NOT Pasquill/standard classes.

    Thresholds 50/200 m are heuristic and not height-normalized z/L.
    Missing L is 'unavailable'; infinite L denotes neutral zero-flux limit.
    """
    value=np.asarray(monin_length,float); out=np.full(value.shape,"neutral",dtype="U16")
    out[value < -200]="weak unstable"; out[(value>=-200)&(value<-50)]="unstable"; out[(value>=-50)&(value<0)]="very unstable"
    out[(value>0)&(value<=50)]="very stable"; out[(value>50)&(value<=200)]="stable"; out[value>200]="weak stable"
    out[np.isinf(value)]="neutral"; out[np.isnan(value)]="unavailable"
    return out

def diagnose_pbl_height(theta_v, height, *, threshold=0.5, axis=0):
    """First theta-v excess above the lowest sample exceeding threshold (K).

    This is a configurable screening rule, not a universal WRF PBL diagnosis.
    No crossing returns NaN; the returned value is the sampled crossing height.
    """
    theta=np.moveaxis(np.asarray(theta_v,float),axis,0); z=np.moveaxis(np.asarray(height,float),axis,0)
    condition=theta-theta[0:1] >= threshold; index=np.argmax(condition,axis=0); found=np.any(condition,axis=0)
    return np.where(found,np.take_along_axis(z,index[None],axis=0)[0],np.nan)

def convective_velocity_scale(kinematic_heat_flux,pbl_height,theta_v):
    """Return Deardorff convective velocity scale ``w*``.

    ``w* = [(g/theta_v) (w'theta_v')_0 z_i]^(1/3)``. The first argument is
    kinematic heat flux in K m s-1, not sensible heat flux in W m-2. Negative
    buoyancy flux is clipped to zero. See Deardorff (1970),
    doi:10.1175/1520-0469(1970)027<1211:CVATSF>2.0.CO;2.
    """
    buoyancy=np.maximum(G*np.asarray(kinematic_heat_flux)/np.asarray(theta_v),0); return np.cbrt(buoyancy*np.asarray(pbl_height))

def rotor_equivalent_wind_speed(speed, height, bottom, top, *, axis=0):
    """Return cube-mean rotor-equivalent wind speed over 41 height samples.

    This is a uniformly height-weighted approximation to rotor-area weighting.
    See Wagner et al. (2014), doi:10.1088/1742-6596/524/1/012108.
    """
    targets=np.linspace(bottom,top,41); profile=interpolate_height(speed,height,targets,axis=axis)
    return np.cbrt(np.mean(profile**3,axis=axis))

def rotor_shear_veer(speed,direction,height,bottom,top,*,axis=0):
    """Return two-height power-law shear and wrapped directional veer."""
    sampled_speed=interpolate_height(speed,height,[bottom,top],axis=axis); sampled_dir=interpolate_height(np.unwrap(np.deg2rad(direction),axis=axis),height,[bottom,top],axis=axis)
    shear=np.log(sampled_speed.take(1,axis=axis)/sampled_speed.take(0,axis=axis))/np.log(top/bottom)
    veer=np.rad2deg(np.angle(np.exp(1j*(sampled_dir.take(1,axis=axis)-sampled_dir.take(0,axis=axis)))))
    return shear,veer

def weibull_fit(speed):
    """Estimate Weibull shape/scale using the Justus moment approximation.

    ``k = (sigma/mean)^-1.086``; see Justus et al. (1978),
    doi:10.1175/1520-0450(1978)017<0350:MFEWSF>2.0.CO;2.
    """
    values=np.asarray(speed,float); values=values[np.isfinite(values)&(values>0)]
    if values.size<2: return np.nan,np.nan
    if np.std(values)==0: return np.inf,float(np.mean(values))
    from math import gamma
    shape=(np.std(values)/np.mean(values))**-1.086; scale=np.mean(values)/gamma(1+1/shape)
    return float(shape),float(scale)

def wind_power_density(speed,density=1.225,*,axis=None):
    """Return mean kinetic power flux ``0.5 rho U^3`` in W m-2."""
    return 0.5*np.nanmean(np.asarray(density)*np.asarray(speed)**3,axis=axis)

def component_spectra(u,v,w,*,spacing,axis=-1):
    """One-sided component PSDs and half their sum; spacing sets frequency units."""
    from ..spectra import power_spectrum
    frequency,su=power_spectrum(u,spacing=spacing,axis=axis); _,sv=power_spectrum(v,spacing=spacing,axis=axis); _,sw=power_spectrum(w,spacing=spacing,axis=axis)
    return frequency,{"u":su,"v":sv,"w":sw,"tke":0.5*(su+sv+sw)}

def premultiplied_spectrum(frequency,spectrum):
    """Multiply PSD by frequency; does not establish any inertial subrange."""
    return np.asarray(frequency)*np.asarray(spectrum)

def fit_spectral_slope(frequency,spectrum,*,minimum=None,maximum=None):
    """Log10 least-squares slope/intercept on positive selected spectral samples."""
    f=np.asarray(frequency,float); s=np.asarray(spectrum,float); mask=(f>0)&(s>0)
    if minimum is not None: mask &= f>=minimum
    if maximum is not None: mask &= f<=maximum
    if mask.sum()<2: return np.nan,np.nan
    slope,intercept=np.polyfit(np.log10(f[mask]),np.log10(s[mask]),1); return float(slope),float(intercept)

def integral_time_scale(signal,spacing=1.0):
    """Integrate normalized autocorrelation to its first zero crossing.

    Uses the biased finite-record autocorrelation, with a linearly interpolated
    zero crossing and trapezoidal integration. If no crossing is sampled,
    integrates to the final lag. Constant series return NaN.
    See Pope (2000), section 6.4, doi:10.1017/CBO9780511840531.
    """
    x=np.asarray(signal,float)
    if x.ndim!=1 or x.size<2 or not np.isfinite(x).all() or not np.isfinite(spacing) or spacing<=0:
        raise ValueError("Require finite 1-D signal with >=2 samples and positive spacing")
    x=x-x.mean(); correlation=np.correlate(x,x,mode="full")[x.size-1:]
    if correlation[0]==0: return np.nan,np.full_like(correlation,np.nan)
    correlation/=correlation[0]
    stop=np.flatnonzero(correlation<=0)
    if stop.size:
        index=int(stop[0])
        crossing=(index-1+correlation[index-1]/(correlation[index-1]-correlation[index]))*spacing
        lags=np.r_[np.arange(index)*spacing,crossing]
        positive=np.r_[correlation[:index],0.]
    else:
        lags=np.arange(correlation.size)*spacing; positive=correlation
    trapezoid=getattr(np,"trapezoid",None) or np.trapz
    return float(trapezoid(positive,x=lags)),correlation

def dew_point(temperature,relative_humidity):
    """Dew point from the inverse Bolton liquid-water saturation-pressure fit.

    See Bolton (1980), doi:10.1175/1520-0493(1980)108<1046:TCOEPT>2.0.CO;2.
    """
    tc=np.asarray(temperature)-273.15; rh=np.clip(np.asarray(relative_humidity),1e-6,100); gamma=np.log(rh/100)+17.67*tc/(243.5+tc); return 243.5*gamma/(17.67-gamma)+273.15

def relative_humidity(temperature,pressure,mixing_ratio):
    """Return RH using vapor pressure from mixing ratio and Bolton saturation pressure."""
    vapor=np.asarray(mixing_ratio)*np.asarray(pressure)/(0.622+np.asarray(mixing_ratio)); tc=np.asarray(temperature)-273.15; saturation=611.2*np.exp(17.67*tc/(tc+243.5)); return np.clip(100*vapor/saturation,0,100)

def equivalent_potential_temperature(temperature,pressure,mixing_ratio):
    """Return a simplified equivalent-potential-temperature approximation.

    Uses ``theta_e ~= theta exp(Lv r/(cp T))``. This is not the full Bolton
    (1980) pseudoadiabatic formulation and should be treated as a screening
    diagnostic. See Emanuel (1994), *Atmospheric Convection*, section 4.5.
    """
    return np.asarray(temperature)*(100000/np.asarray(pressure))**(RD/CP)*np.exp(LV*np.asarray(mixing_ratio)/(CP*np.asarray(temperature)))

def brunt_vaisala_frequency(theta,height,*,axis=0):
    """Return dry Brunt-Vaisala frequency ``sqrt((g/theta)dtheta/dz)``.

    Negative squared frequency is clipped to zero; use the underlying gradient
    to diagnose unstable layers. See Durran and Klemp (1982),
    doi:10.1175/1520-0469(1982)039<2152:OTEOFF>2.0.CO;2.
    """
    return np.sqrt(np.maximum(G/np.asarray(theta)*_vertical_gradient(theta,height,axis=axis),0))

def inversion_layers(temperature,height,*,minimum_gradient=0.001,axis=0):
    """Flag nonuniform-level gradients above a threshold (K/m); no layer merging.

    Missing derivatives are unclassified (False), not evidence of no inversion.
    """
    return _vertical_gradient(temperature,height,axis=axis)>minimum_gradient

def tke_budget(u,v,w,theta,height,*,time_axis=0,vertical_axis=1):
    """Return resolved TKE plus vertical shear and dry buoyancy production terms.

    theta is potential temperature (K); dry buoyancy omits moisture/condensate
    contributions. Supply virtual potential temperature only if that explicit
    approximation is justified. Omits transport, pressure correlation, dissipation,
    moving-coordinate and SGS terms. Signs
    follow the standard Reynolds-averaged TKE equation; see Stull (1988),
    doi:10.1007/978-94-009-3027-8.
    """
    u,v,w,theta=[np.asarray(item,float) for item in (u,v,w,theta)]
    if u.ndim<2 or any(item.shape!=u.shape for item in (v,w,theta)):
        raise ValueError("Co-located u/v/w/theta need identical shapes with time and vertical axes")
    if any(not isinstance(axis,(int,np.integer)) or not -u.ndim<=axis<u.ndim for axis in (time_axis,vertical_axis)):
        raise ValueError("Time and vertical axes must be valid dimension indexes")
    time_axis%=u.ndim; vertical_axis%=u.ndim
    if time_axis==vertical_axis: raise ValueError("Time and vertical axes must differ")
    if u.shape[time_axis]<2: raise ValueError("A Reynolds budget needs at least two time samples")
    up=u-np.mean(u,axis=time_axis,keepdims=True); vp=v-np.mean(v,axis=time_axis,keepdims=True); wp=w-np.mean(w,axis=time_axis,keepdims=True); tp=theta-np.mean(theta,axis=time_axis,keepdims=True)
    mean_u=np.mean(u,axis=time_axis); mean_v=np.mean(v,axis=time_axis); z=np.mean(height,axis=time_axis) if np.asarray(height).ndim==np.asarray(u).ndim else np.asarray(height)
    zaxis=vertical_axis-1 if time_axis<vertical_axis else vertical_axis
    if z.ndim==1:
        shape=[1]*mean_u.ndim; shape[zaxis]=z.size; z=z.reshape(shape)
    z=np.broadcast_to(z,mean_u.shape)
    if z.shape[zaxis]<2 or not np.isfinite(z).all() or np.any(np.diff(z,axis=zaxis)<=0):
        raise ValueError("Budget heights must increase strictly along the vertical axis")
    shear=-(np.mean(up*wp,axis=time_axis)*_vertical_gradient(mean_u,z,axis=zaxis)+np.mean(vp*wp,axis=time_axis)*_vertical_gradient(mean_v,z,axis=zaxis))
    buoyancy=G*np.mean(wp*tp,axis=time_axis)/np.mean(theta,axis=time_axis); return {"shear_production":shear,"buoyancy_production":buoyancy,"resolved_tke":0.5*np.mean(up**2+vp**2+wp**2,axis=time_axis)}

def horizontal_kinematics(u,v,dx,dy):
    """Return Cartesian divergence, vertical vorticity, and strain components."""
    du_dy,du_dx=np.gradient(np.asarray(u),dy,dx,axis=(-2,-1)); dv_dy,dv_dx=np.gradient(np.asarray(v),dy,dx,axis=(-2,-1))
    return {"divergence":du_dx+dv_dy,"vertical_vorticity":dv_dx-du_dy,"strain_normal":du_dx-dv_dy,"strain_shear":dv_dx+du_dy}

def q_criterion(u,v,w,dx,dy,dz):
    """Return ``Q = 0.5 (||Omega||^2 - ||S||^2)``.

    Positive Q identifies rotation-dominated regions. See Hunt, Wray, and
    Moin (1988), NTRS 19890015184, pp. 193-208.

    Uniform Cartesian spacing only; terrain-following WRF fields require
    coordinate/metric treatment before using this helper for physical gradients.
    """
    # np.gradient returns z,y,x derivatives; tensor columns must be x,y,z
    # to match the u,v,w rows in strain/rotation decomposition.
    gradients=[np.stack(np.gradient(np.asarray(c),dz,dy,dx,axis=(-3,-2,-1)),axis=-1)[...,::-1] for c in (u,v,w)]
    tensor=np.stack(gradients,axis=-2); symmetric=.5*(tensor+np.swapaxes(tensor,-1,-2)); rotation=.5*(tensor-np.swapaxes(tensor,-1,-2)); return .5*(np.sum(rotation**2,axis=(-2,-1))-np.sum(symmetric**2,axis=(-2,-1)))

def low_level_jet(speed,height,*,minimum_speed=8.0,drop=2.0,axis=0):
    """Screen an interior profile maximum with speed/drop thresholds (m/s).

    Compares the core with the highest supplied level; not a universal LLJ
    definition or a search for the nearest local minimum above the core.
    """
    s=np.moveaxis(np.asarray(speed),axis,0); z=np.moveaxis(np.asarray(height),axis,0); index=np.argmax(s,axis=0); core=np.take_along_axis(s,index[None],axis=0)[0]; core_z=np.take_along_axis(z,index[None],axis=0)[0]; top=s[-1]
    return {"detected":(core>=minimum_speed)&((core-top)>=drop)&(index>0)&(index<s.shape[0]-1),"core_speed":core,"core_height":core_z,"drop_above":core-top}

def precipitation_diagnostics(rainc,rainnc,*,time_axis=0,wet_threshold=0.1):
    """Counter differences in mm; negative changes flag resets, never clipped.

    Resets are checked in RAINC and RAINNC separately, so growth in one cannot
    hide a reset in the other. No bucket/restart reconstruction is attempted.
    Resets or any missing/nonfinite
    counter sample make the period total NaN, not a partial total. First
    increment is 0 when the first counter is finite.
    """
    if np.shape(rainc)!=np.shape(rainnc):
        raise ValueError("Rainfall counters must have identical co-located shapes")
    rainc,rainnc=np.asarray(rainc,float),np.asarray(rainnc,float)
    with np.errstate(invalid="ignore"):
        total=rainc+rainnc
        increments=np.diff(total,axis=time_axis,prepend=np.take(total,[0],axis=time_axis))
        resets=np.any((np.diff(rainc,axis=time_axis)<0)|(np.diff(rainnc,axis=time_axis)<0),axis=time_axis)
    missing=np.any(~np.isfinite(total),axis=time_axis)
    finite=np.isfinite(increments)
    maximum=np.where(np.any(finite,axis=time_axis),np.max(np.where(finite,increments,-np.inf),axis=time_axis),np.nan)
    period=np.sum(np.where(finite,increments,0),axis=time_axis)
    return {"accumulated":total,"increment":increments,"wet":increments>=wet_threshold,"maximum_interval":maximum,"total":np.where(resets|missing,np.nan,period),"reset_detected":resets,"missing_detected":missing}
