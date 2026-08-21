"""Terrain, land-use, resolution, conservation, and temporal diagnostics."""
from __future__ import annotations
import numpy as np

def terrain_metrics(terrain,dx,dy):
    dz_dy,dz_dx=np.gradient(np.asarray(terrain,float),dy,dx); slope=np.hypot(dz_dx,dz_dy); aspect=(270-np.degrees(np.arctan2(dz_dy,dz_dx)))%360
    return {"slope":slope,"slope_degrees":np.degrees(np.arctan(slope)),"aspect":aspect}

def speed_up_ratio(speed,reference,*,minimum_reference=0.1): return np.asarray(speed)/np.where(np.abs(reference)>=minimum_reference,reference,np.nan)

def landuse_statistics(values,categories):
    data=np.asarray(values,float); land=np.asarray(categories); result={}
    for category in np.unique(land[np.isfinite(land)]):
        selected=data[...,land==category]; result[int(category)]={"count":int(selected.size),"mean":float(np.nanmean(selected)),"std":float(np.nanstd(selected)),"minimum":float(np.nanmin(selected)),"maximum":float(np.nanmax(selected))}
    return result

def resolution_metrics(fine,coarse_regridded):
    difference=np.asarray(fine)-np.asarray(coarse_regridded); return {"bias":float(np.nanmean(difference)),"mae":float(np.nanmean(np.abs(difference))),"rmse":float(np.sqrt(np.nanmean(difference**2))),"correlation":float(np.corrcoef(np.asarray(fine).ravel(),np.asarray(coarse_regridded).ravel())[0,1])}

def boundary_discontinuity(field,width=1):
    values=np.asarray(field,float); interior=values[...,width:-width,width:-width]; edges=np.concatenate((values[...,:width,:].ravel(),values[...,-width:,:].ravel(),values[...,width:-width,:width].ravel(),values[...,width:-width,-width:].ravel()))
    return {"edge_mean":float(np.nanmean(edges)),"interior_mean":float(np.nanmean(interior)),"difference":float(np.nanmean(edges)-np.nanmean(interior))}

def integral_conservation(source,target,source_cell_area,target_cell_area):
    before=float(np.nansum(np.asarray(source)*source_cell_area)); after=float(np.nansum(np.asarray(target)*target_cell_area)); return {"source_integral":before,"target_integral":after,"relative_error":(after-before)/before if before else np.nan}

def rotate_vectors(u,v,angle_degrees):
    angle=np.deg2rad(angle_degrees); return np.asarray(u)*np.cos(angle)-np.asarray(v)*np.sin(angle),np.asarray(u)*np.sin(angle)+np.asarray(v)*np.cos(angle)

def temporal_diagnostics(values,spacing=1.0,*,axis=0,ramp_threshold=None):
    data=np.asarray(values,float); mean=np.nanmean(data,axis=axis,keepdims=True); anomaly=data-mean; increments=np.diff(data,axis=axis); threshold=float(ramp_threshold) if ramp_threshold is not None else float(2*np.nanstd(increments))
    return {"mean":np.squeeze(mean,axis=axis),"anomaly":anomaly,"increments":increments,"ramp_threshold":threshold,"ramp_events":np.abs(increments)>=threshold,"persistence_lag1":float(np.corrcoef(np.take(data,range(data.shape[axis]-1),axis=axis).ravel(),np.take(data,range(1,data.shape[axis]),axis=axis).ravel())[0,1])}

def diurnal_cycle(values,hours,*,axis=0):
    data=np.asarray(values,float); hour=np.asarray(hours).astype(int)%24; return {int(item):np.nanmean(np.take(data,np.flatnonzero(hour==item),axis=axis),axis=axis) for item in np.unique(hour)}
