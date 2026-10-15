"""Small SYNTHETIC WRF-shaped data, not an atmospheric simulation."""
import numpy as np
import xarray as xr


def synthetic_wrf():
    nt,nz,ny,nx=32,4,8,8
    dims=("Time","bottom_top","south_north","west_east")
    surface=("Time","south_north","west_east")
    lat,lon=np.meshgrid(np.linspace(51.8,52.2,ny),np.linspace(4.8,5.2,nx),indexing="ij")
    ground=np.full((nt,ny,nx),10.)
    faces=np.array([0.,50.,150.,400.,800.])
    z=(faces[:-1]+faces[1:])/2
    phase=np.sin(np.arange(nt)*2*np.pi/8)
    u=6+.005*z[None,:,None,None]+phase[:,None,None,None]+np.arange(nx+1)[None,None,None,:]*.1
    v=np.ones((nt,nz,ny+1,nx))
    w=np.broadcast_to(.2*phase[:,None,None,None],(nt,nz+1,ny,nx)).copy()
    phb=9.81*(ground[:,None]+faces[None,:,None,None])
    time=np.datetime64("2025-01-01T00:00:00")+np.arange(nt)*np.timedelta64(10,"s")
    ds=xr.Dataset({
        "Times":("Time",np.array([str(t).replace("T","_").encode() for t in time])),
        "XLAT":(surface,np.broadcast_to(lat,ground.shape)),
        "XLONG":(surface,np.broadcast_to(lon,ground.shape)),
        "HGT":(surface,ground),
        "PH":(("Time","bottom_top_stag","south_north","west_east"),np.zeros_like(phb)),
        "PHB":(("Time","bottom_top_stag","south_north","west_east"),phb),
        "U":(("Time","bottom_top","south_north","west_east_stag"),np.broadcast_to(u,(nt,nz,ny,nx+1))),
        "V":(("Time","bottom_top","south_north_stag","west_east"),v),
        "W":(("Time","bottom_top_stag","south_north","west_east"),w),
    },attrs=dict(TITLE="SYNTHETIC API DEMONSTRATION — NOT A WRF SIMULATION",GRID_ID=1,
        MAP_PROJ=1,DX=1000.,DY=1000.,CEN_LAT=52.,CEN_LON=5.,STAND_LON=5.,TRUELAT1=52.,TRUELAT2=52.,
        BL_PBL_PHYSICS=5,KM_OPT=2))
    for name,value,units in [("T",z[None,:,None,None]*.003,"K"),("P",0,"Pa"),("PB",95000,"Pa"),
        ("QVAPOR",.005,"kg kg-1"),("QKE",2,"m2 s-2")]:
        ds[name]=(dims,np.broadcast_to(value,(nt,nz,ny,nx)).copy(),{"units":units})
    for name,value,units in [("T2",280+phase[:,None,None],"K"),("PSFC",100000,"Pa"),("Q2",.005,"kg kg-1"),
        ("U10",6+phase[:,None,None]+np.arange(nx)[None,None,:]*.1,"m s-1"),("V10",1,"m s-1"),
        ("HFX",40,"W m-2"),("LH",20,"W m-2"),("UST",.3,"m s-1"),("PBLH",500,"m"),
        ("RAINC",0,"mm"),("RAINNC",np.arange(nt)[:,None,None]*.1,"mm"),("COSALPHA",1,""),
        ("SINALPHA",0,""),("MAPFAC_M",1,""),("LU_INDEX",1+np.arange(nx)[None,None,:]%3,"")]:
        ds[name]=(surface,np.broadcast_to(value,(nt,ny,nx)).copy(),{"units":units})
    for i,name in enumerate(("m11","m12","m13","m22","m23","m33")):
        ds[name]=(dims,np.full((nt,nz,ny,nx),.1*(i+1)),{"units":"m2 s-2"})
    return ds
