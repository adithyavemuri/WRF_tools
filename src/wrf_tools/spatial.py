"""Terrain, land-use, resolution, conservation, and temporal diagnostics."""
from __future__ import annotations
import numpy as np

def terrain_metrics(terrain,dx,dy):
    """Nominal Cartesian terrain slope/aspect; spacing and terrain in same units."""
    dz_dy,dz_dx=np.gradient(np.asarray(terrain,float),dy,dx); slope=np.hypot(dz_dx,dz_dy); aspect=(270-np.degrees(np.arctan2(dz_dy,dz_dx)))%360
    return {"slope":slope,"slope_degrees":np.degrees(np.arctan(slope)),"aspect":aspect}

def speed_up_ratio(speed,reference,*,minimum_reference=0.1):
    """Ratio to an explicit wind-speed reference; weak references become NaN."""
    return np.asarray(speed)/np.where(np.abs(reference)>=minimum_reference,reference,np.nan)

def landuse_statistics(values,categories):
    """Unweighted finite-value summaries by categorical grid code, not MODIS decoding."""
    data=np.asarray(values,float); land=np.asarray(categories); result={}
    if land.ndim!=2 or data.shape[-2:]!=land.shape:
        raise ValueError("Categories must match the final two field dimensions")
    for category in np.unique(land[np.isfinite(land)]):
        selected=data[...,land==category]; finite=selected[np.isfinite(selected)]
        result[int(category)]={"count":int(finite.size),"sample_count":int(selected.size),
            "mean":float(finite.mean()) if finite.size else np.nan,"std":float(finite.std()) if finite.size else np.nan,
            "minimum":float(finite.min()) if finite.size else np.nan,"maximum":float(finite.max()) if finite.size else np.nan}
    return result

def resolution_metrics(fine,coarse_regridded):
    """Paired field scores after explicit regridding; no implicit broadcasting."""
    from .validation import comparison_summary
    return comparison_summary(fine,coarse_regridded)

def boundary_discontinuity(field,width=1):
    """Compare unweighted edge-band and interior means; a screening measure."""
    values=np.asarray(field,float)
    if not isinstance(width,int) or width<1 or values.ndim<2 or min(values.shape[-2:])<=2*width:
        raise ValueError("Choose a positive edge width leaving a nonempty interior")
    interior=values[...,width:-width,width:-width]; edges=np.concatenate((values[...,:width,:].ravel(),values[...,-width:,:].ravel(),values[...,width:-width,:width].ravel(),values[...,width:-width,-width:].ravel()))
    return {"edge_mean":float(np.nanmean(edges)),"interior_mean":float(np.nanmean(interior)),"difference":float(np.nanmean(edges)-np.nanmean(interior))}

def integral_conservation(source,target,source_cell_area,target_cell_area):
    """Compare supplied area-weighted field integrals; no automatic remapping."""
    before=float(np.nansum(np.asarray(source)*source_cell_area)); after=float(np.nansum(np.asarray(target)*target_cell_area)); return {"source_integral":before,"target_integral":after,"relative_error":(after-before)/before if before else np.nan}

def rotate_vectors(u,v,angle_degrees):
    """Counterclockwise Cartesian vector rotation; not meteorological wind-FROM."""
    angle=np.deg2rad(angle_degrees); return np.asarray(u)*np.cos(angle)-np.asarray(v)*np.sin(angle),np.asarray(u)*np.sin(angle)+np.asarray(v)*np.cos(angle)

def temporal_diagnostics(values,spacing=1.0,*,axis=0,ramp_threshold=None):
    """Equal-sample anomalies, increments, threshold ramps and lag-one correlation.

    Threshold units are per saved interval. increment_rate additionally divides
    by the supplied positive spacing (seconds for rates per second). Correlation
    is pooled over supplied dimensions, not a per-grid-cell persistence map.
    """
    from .validation import correlation
    data=np.asarray(values,float)
    if not np.isfinite(spacing) or spacing<=0 or data.shape[axis]<2:
        raise ValueError("Require positive finite spacing and at least two records")
    mean=np.nanmean(data,axis=axis,keepdims=True); anomaly=data-mean; increments=np.diff(data,axis=axis); threshold=float(ramp_threshold) if ramp_threshold is not None else float(2*np.nanstd(increments))
    return {"mean":np.squeeze(mean,axis=axis),"anomaly":anomaly,"increments":increments,"increment_rate":increments/spacing,
        "ramp_threshold":threshold,"ramp_events":np.abs(increments)>threshold,
        "persistence_lag1":float(correlation(np.take(data,range(data.shape[axis]-1),axis=axis),np.take(data,range(1,data.shape[axis]),axis=axis)))}

def diurnal_cycle(values,hours,*,axis=0):
    """Unweighted means grouped by supplied hour-of-day labels; no timezone inference."""
    data=np.asarray(values,float); hour=np.asarray(hours).astype(int)%24; return {int(item):np.nanmean(np.take(data,np.flatnonzero(hour==item),axis=axis),axis=axis) for item in np.unique(hour)}
