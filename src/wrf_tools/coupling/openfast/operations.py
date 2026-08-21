from __future__ import annotations
import numpy as np
from ...types import WindField

def concatenate_fields(fields):
    fields = list(fields)
    if not fields: raise ValueError("at least one wind field is required")
    ref = fields[0]
    for field in fields[1:]:
        if field.velocity.shape[1:] != ref.velocity.shape[1:] or not np.allclose([field.dy, field.dz, field.dt, field.hub_height, field.bottom_height], [ref.dy, ref.dz, ref.dt, ref.hub_height, ref.bottom_height]):
            raise ValueError("wind fields have incompatible grids or time steps")
    return WindField(np.concatenate([f.velocity for f in fields], axis=0), ref.dy, ref.dz, ref.dt, ref.hub_height, ref.bottom_height, description="Concatenated by wrf-tools")

def velocity_at(field, *, y=0.0, z=None):
    z = field.hub_height if z is None else z
    iy = int(np.clip(round(y/field.dy+(field.velocity.shape[2]-1)/2), 0, field.velocity.shape[2]-1))
    iz = int(np.clip(round((z-field.bottom_height)/field.dz), 0, field.velocity.shape[1]-1))
    return field.velocity[:, iz, iy, :]

def horizontal_plane(field, *, z):
    iz = int(np.clip(round((z-field.bottom_height)/field.dz), 0, field.velocity.shape[1]-1))
    return field.velocity[:, iz, :, :]

def vertical_profile(field):
    return field.bottom_height+np.arange(field.velocity.shape[1])*field.dz, field.velocity.mean(axis=(0, 2))

def rotate_velocity(velocity, *, horizontal_degrees=0.0, vertical_degrees=0.0):
    values = np.asarray(velocity, float)
    h, v = np.deg2rad(horizontal_degrees), np.deg2rad(vertical_degrees)
    ch, sh, cv, sv = np.cos(h), np.sin(h), np.cos(v), np.sin(v)
    horizontal = values @ np.array([[ch, -sh, 0], [sh, ch, 0], [0, 0, 1]]).T
    return horizontal @ np.array([[cv, 0, sv], [0, 1, 0], [-sv, 0, cv]]).T

def constant_field(*, speed, duration, dt, ny, nz, dy, dz, hub_height, bottom_height, direction=0.0):
    nt = int(round(duration/dt))+1
    velocity = np.zeros((nt, nz, ny, 3)); angle = np.deg2rad(direction)
    velocity[..., 0], velocity[..., 1] = speed*np.cos(angle), speed*np.sin(angle)
    return WindField(velocity, dy, dz, dt, hub_height, bottom_height, description="Constant wind field")

def step_field(*, speeds, step_duration, dt, ny, nz, dy, dz, hub_height, bottom_height, direction=0.0):
    """Create a full-field sequence of constant wind-speed steps."""
    records=max(1,int(round(step_duration/dt))); series=np.repeat(np.asarray(speeds,float),records)
    velocity=np.zeros((series.size,nz,ny,3)); angle=np.deg2rad(direction); velocity[...,0]=series[:,None,None]*np.cos(angle); velocity[...,1]=series[:,None,None]*np.sin(angle)
    return WindField(velocity,dy,dz,dt,hub_height,bottom_height,description="Step wind field")

def write_uniform_wind(path, time, speed, *, direction=0.0, vertical_speed=0.0):
    """Write an OpenFAST uniform wind file: time, speed, direction, vertical speed."""
    from pathlib import Path
    values=np.column_stack((np.asarray(time),np.asarray(speed),np.broadcast_to(direction,np.shape(speed)),np.broadcast_to(vertical_speed,np.shape(speed))))
    target=Path(path); np.savetxt(target,values,header="Time WindSpeed WindDir VertSpeed",comments="! "); return target
