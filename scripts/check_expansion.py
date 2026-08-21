"""Smoke-test expanded post-processing APIs against one real WRF output."""
from __future__ import annotations
import argparse
import json
import numpy as np
from wrf_tools.extract import horizontal_plane, point, transect
from wrf_tools.filters import butterworth_spatial, top_hat_coarsen
from wrf_tools.io import open_wrf, validate_wrf_dataset
from wrf_tools.les import load_velocity
from wrf_tools.reporting import dataset_summary
from wrf_tools.spectra import radial_wavenumber_spectrum

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("path"); args=parser.parse_args()
    with open_wrf(args.path) as dataset:
        validate_wrf_dataset(dataset)
        u,_,_=load_velocity(dataset)
        plane=horizontal_plane(u.to_dataset(name="u"),"u",level=0,time=0).values
        dx=float(dataset.attrs.get("DX",1.0)); dy=float(dataset.attrs.get("DY",dx)); cutoff=3*max(dx,dy)
        filtered=butterworth_spatial(plane,dx=dx,dy=dy,cutoff_wavelength=cutoff,order=2)
        coarse=top_hat_coarsen(plane,factor_y=3,factor_x=3,trim=True)
        wave,energy=radial_wavenumber_spectrum(plane,dx=dx,dy=dy)
        lat=dataset["XLAT"].isel(Time=0); lon=dataset["XLONG"].isel(Time=0); cy,cx=lat.shape[0]//2,lat.shape[1]//2
        site=point(dataset,float(lat[cy,cx]),float(lon[cy,cx]),variables=["T2"],time=0)
        section,_,_=transect(plane,(0,0),(plane.shape[-2]-1,plane.shape[-1]-1),points=25)
        result={"dataset":dataset_summary(dataset),"plane_shape":plane.shape,"filtered_finite":bool(np.isfinite(filtered).all()),"coarse_shape":coarse.shape,"spectrum_bins":wave.size,"spectrum_finite":bool(np.isfinite(energy).all()),"site_t2":float(site["T2"]),"transect_points":section.size}
    print(json.dumps(result,indent=2,default=str)); return 0

if __name__=="__main__": raise SystemExit(main())
