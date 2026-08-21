"""Legacy TurbSim/AeroDyn post-processing formats."""
from __future__ import annotations
from pathlib import Path
import struct
import numpy as np
import xarray as xr
from ...types import WindField

def read_hub_height_binary(path, *, dtype="<f4"):
    values = np.fromfile(path, dtype=dtype)
    if values.size % 14:
        raise ValueError("hub-height file does not contain complete 14-value records")
    values = values.reshape(-1, 14)
    names = ("u", "uh", "ut", "v", "w", "u_prime", "v_prime", "w_prime", "uw", "uv", "vw", "tke", "ctke")
    return xr.Dataset({name: ("time", values[:, i+1]) for i, name in enumerate(names)}, coords={"time": values[:, 0]})

def read_full_field_text(path):
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    metadata = np.fromstring(lines[4], sep=" ")
    if metadata.size < 7:
        raise ValueError("invalid full-field text grid metadata")
    ny, nz = int(metadata[0]), int(metadata[1]); dy, dz, dt, hub_height, mean_speed = metadata[2:7]
    z = np.fromstring(lines[7], sep=" ")[:nz] + hub_height
    y = np.fromstring(lines[10], sep=" ")[:ny]
    tokens = np.fromstring(" ".join(lines[12:]), sep=" ")
    record = 2+ny*nz
    if tokens.size % record: raise ValueError("incomplete full-field text record")
    rows = tokens.reshape(-1, record)
    velocity = rows[:, 2:].reshape(-1, nz, ny)[:, :, ::-1]
    return xr.Dataset({"u": (("time","z","y"), velocity), "hub_wind": ("time", rows[:,1])}, coords={"time": rows[:,0], "z": z, "y": y}, attrs={"dy":dy,"dz":dz,"dt":dt,"hub_height":hub_height,"mean_speed":mean_speed})

def read_coherent_points(path):
    with Path(path).open("rb") as stream:
        identifier, components, nt = struct.unpack("<hii", stream.read(10))
        if identifier != -99 or components != 3: raise ValueError("unsupported coherent-points file")
        dx, mean_speed, tiu, tiv, tiw = struct.unpack("<fffff", stream.read(20))
        raw = np.frombuffer(stream.read(), dtype="<i2")
    if raw.size % (nt*3): raise ValueError("incomplete coherent-points data")
    points = raw.size//(nt*3)
    encoded = raw.reshape(nt, points, 3)
    scale = 1e-5*mean_speed*np.array([tiu,tiv,tiw]); offset=np.array([mean_speed,0,0])
    return xr.Dataset({"velocity": (("time","point","component"), encoded*scale+offset)}, coords={"time":np.arange(nt)*dx/mean_speed,"component":["u","v","w"]}, attrs={"mean_speed":mean_speed,"turbulence_intensity":[tiu,tiv,tiw]})

def read_bladed_wnd(path, *, hub_height=None, clockwise=False):
    """Read the newer-style Bladed/AeroDyn full-field `.wnd` format."""
    source=Path(path)
    with source.open("rb") as stream:
        identifier, format_code = struct.unpack("<hh",stream.read(4))
        if identifier != -99: raise ValueError("only newer-style Bladed .wnd files are supported")
        (components,) = struct.unpack("<i",stream.read(4)); lat,z0,zoffset,tiu,tiv,tiw,dz,dy,dx=struct.unpack("<fffffffff",stream.read(36))
        (half_nt,) = struct.unpack("<i",stream.read(4)); (mean_speed,) = struct.unpack("<f",stream.read(4))
        stream.read(12+8); nz,ny=struct.unpack("<ii",stream.read(8)); stream.read(12*(components-1))
        nt=max(2*half_nt,1); raw=np.frombuffer(stream.read(),dtype="<i2")
    count=nt*nz*ny*components
    if raw.size<count: raise ValueError("Bladed .wnd file ended before the grid was complete")
    encoded=raw[:count].reshape(nt,nz,ny,components)
    scale=1e-5*mean_speed*np.array([tiu,tiv,tiw]); velocity=encoded*scale+np.array([mean_speed,0,0])
    if clockwise: velocity=velocity[:,:,::-1,:]
    bottom=zoffset-dz*(nz-1)/2
    return WindField(velocity,dy,dz,dx/mean_speed,hub_height or zoffset,bottom,description=f"Bladed wind field from {source.name}",mean_speed=mean_speed,source=source)

def write_bladed_wnd(path, field, *, latitude=0.0, roughness=0.0, clockwise=False):
    """Write the newer-style Bladed/AeroDyn `.wnd` format."""
    target=Path(path); velocity=np.asarray(field.velocity,float)
    if velocity.shape[0]%2: raise ValueError("Bladed .wnd requires an even number of time steps")
    if clockwise: velocity=velocity[:,:,::-1,:]
    mean=float(field.mean_speed); fluctuations=velocity-np.array([mean,0,0]); ti=100*np.std(fluctuations,axis=(0,1,2))/max(abs(mean),np.finfo(float).eps)
    ti=np.where(ti>0,ti,1e-6); scale=1e-5*mean*ti; encoded=np.clip(np.rint(fluctuations/scale),-32768,32767).astype("<i2")
    nt,nz,ny,_=velocity.shape; zoffset=field.bottom_height+field.dz*(nz-1)/2
    with target.open("wb") as stream:
        stream.write(struct.pack("<hhi",-99,4,3)); stream.write(struct.pack("<fffffffff",latitude,roughness,zoffset,*ti,field.dz,field.dy,field.dt*mean)); stream.write(struct.pack("<if",nt//2,mean)); stream.write(struct.pack("<fffii",0,0,0,0,0)); stream.write(struct.pack("<ii",nz,ny)); stream.write(struct.pack("<iiiiii",0,0,0,0,0,0)); stream.write(encoded.tobytes())
    return target
