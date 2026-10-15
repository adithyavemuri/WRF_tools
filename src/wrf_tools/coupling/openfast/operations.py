from __future__ import annotations
import numpy as np
from ...types import WindField

def concatenate_fields(fields):
    """Concatenate compatible wind records in time; no temporal resampling."""
    fields = list(fields)
    if not fields: raise ValueError("at least one wind field is required")
    ref = fields[0]
    for field in fields[1:]:
        if field.velocity.shape[1:] != ref.velocity.shape[1:] or not np.allclose([field.dy, field.dz, field.dt, field.hub_height, field.bottom_height], [ref.dy, ref.dz, ref.dt, ref.hub_height, ref.bottom_height]):
            raise ValueError("wind fields have incompatible grids or time steps")
    return WindField(np.concatenate([f.velocity for f in fields], axis=0), ref.dy, ref.dz, ref.dt, ref.hub_height, ref.bottom_height, description="Concatenated by wrf-tools")

def velocity_at(field, *, y=0.0, z=None):
    """Nearest lateral/vertical sample (clipped at grid edges), all timestamps."""
    z = field.hub_height if z is None else z
    iy = int(np.clip(round(y/field.dy+(field.velocity.shape[2]-1)/2), 0, field.velocity.shape[2]-1))
    iz = int(np.clip(round((z-field.bottom_height)/field.dz), 0, field.velocity.shape[1]-1))
    return field.velocity[:, iz, iy, :]

def horizontal_plane(field, *, z):
    """Nearest-height time/lateral/component slice; height clips at grid edges."""
    iz = int(np.clip(round((z-field.bottom_height)/field.dz), 0, field.velocity.shape[1]-1))
    return field.velocity[:, iz, :, :]

def vertical_profile(field):
    """Physical z coordinates and velocity averaged equally over time/lateral."""
    return field.bottom_height+np.arange(field.velocity.shape[1])*field.dz, field.velocity.mean(axis=(0, 2))

def rotate_velocity(velocity, *, horizontal_degrees=0.0, vertical_degrees=0.0):
    """Right-handed Cartesian rotations in degrees: horizontal, then vertical."""
    values = np.asarray(velocity, float)
    h, v = np.deg2rad(horizontal_degrees), np.deg2rad(vertical_degrees)
    ch, sh, cv, sv = np.cos(h), np.sin(h), np.cos(v), np.sin(v)
    horizontal = values @ np.array([[ch, -sh, 0], [sh, ch, 0], [0, 0, 1]]).T
    return horizontal @ np.array([[cv, 0, sv], [0, 1, 0], [-sv, 0, cv]]).T

def constant_field(*, speed, duration, dt, ny, nz, dy, dz, hub_height, bottom_height, direction=0.0):
    """Synthetic constant inflow; direction is a Cartesian angle, not wind-FROM."""
    nt = int(round(duration/dt))+1
    velocity = np.zeros((nt, nz, ny, 3)); angle = np.deg2rad(direction)
    velocity[..., 0], velocity[..., 1] = speed*np.cos(angle), speed*np.sin(angle)
    return WindField(velocity, dy, dz, dt, hub_height, bottom_height, description="Constant wind field")

def step_field(*, speeds, step_duration, dt, ny, nz, dy, dz, hub_height, bottom_height, direction=0.0):
    """Create a full-field sequence of constant wind-speed steps."""
    records=max(1,int(round(step_duration/dt))); series=np.repeat(np.asarray(speeds,float),records)
    velocity=np.zeros((series.size,nz,ny,3)); angle=np.deg2rad(direction); velocity[...,0]=series[:,None,None]*np.cos(angle); velocity[...,1]=series[:,None,None]*np.sin(angle)
    return WindField(velocity,dy,dz,dt,hub_height,bottom_height,description="Step wind field")

def write_uniform_wind(path, time, speed, *, direction=0.0, vertical_speed=0.0,
                       horizontal_shear=0.0, power_law_shear=0.0, vertical_shear=0.0, gust=0.0):
    """Write the eight-column OpenFAST InflowWind WindType=2 format.

    Columns: time (s), horizontal speed (m/s), direction (degrees clockwise
    looking down, NOT meteorological wind-FROM), vertical speed (m/s), horizontal
    linear shear, vertical power-law exponent, vertical linear shear, gust (m/s).
    Shear/gust default to zero; set RefHt/RefLength separately in InflowWind.
    Requires >=2 increasing finite times. Optional fields may be scalars/series.
    Reference: InflowWind User's Guide, Table 1 (OpenFAST documentation).
    """
    from pathlib import Path
    time, speed = np.asarray(time, float), np.asarray(speed, float)
    if time.ndim != 1 or speed.shape != time.shape or time.size < 2:
        raise ValueError("time and speed must be matching 1-D arrays with at least two records")
    values=np.column_stack([time,speed]+[np.broadcast_to(item,time.shape) for item in
        (direction,vertical_speed,horizontal_shear,power_law_shear,vertical_shear,gust)])
    if not np.isfinite(values).all() or np.any(np.diff(time)<=0) or np.any(speed<0):
        raise ValueError("Uniform wind values must be finite, times strictly increasing and speed nonnegative")
    target=Path(path)
    np.savetxt(target,values,header="Time WindSpeed WindDir VertSpeed HLinShr VShr VLinShr VGust",comments="! ")
    return target
