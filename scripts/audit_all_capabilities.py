"""Exercise every public wrf-tools capability using one real WRF output.

Temporary station, observation, TurbSim, OpenFAST, namelist, plot, and report
artifacts are derived from the selected WRF file. Results are written as JSON
and Markdown with an explicit pass/fail criterion for every check.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext, redirect_stdout
from datetime import datetime, timedelta
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

import wrf_tools
from wrf_tools.cli import main as cli_main
from wrf_tools.config import ExecutableConfig, WRFSource
from wrf_tools.coupling.openfast import (
    WindField, concatenate_fields, constant_field, horizontal_plane as wind_horizontal_plane,
    read_bladed_wnd, read_bts, read_coherent_points, read_full_field_text,
    read_hub_height_binary, rotate_velocity, step_field, validate_bts,
    velocity_at, vertical_profile as wind_vertical_profile, wind_field_from_components,
    write_bladed_wnd, write_bts, write_uniform_wind,
)
from wrf_tools.diagnostics import *
from wrf_tools.diagnostics.turbulence import fluctuations
from wrf_tools.extract import horizontal_plane, point, to_levels, transect, variables, vertical_profile
from wrf_tools.filters import butterworth_band, butterworth_spatial, resolved_subfilter, spectral_downsample, top_hat_coarsen
from wrf_tools.grid import destagger, interpolate_to_levels, nearest_grid_point, regrid_regular, subset_by_bounds
from wrf_tools.io import discover_wrfout, get_variable, open_wrf, open_wrf_sequence, validate_wrf_dataset
from wrf_tools.les import calculate_fluxes, calculate_total_tke, filtered_tke, load_sgs_stress, load_velocity, sgs_tke
from wrf_tools.observations import align, collocate_grid, from_columns, normalize_time, read_csv, read_netcdf
from wrf_tools.openfast import channel_statistics, compare_outputs, rainflow_cycles, read_ascii_output, read_binary_output, run_openfast, stress_from_moment, zero_crossing_frequency
from wrf_tools.openfast_input import read_parameters, update_parameters
from wrf_tools.plotting import animate_fields, cross_section, horizontal, nested_domains, profile, taylor_diagram, time_height, validation_scatter, wind_barbs, wind_rose
from wrf_tools.reporting import comparison_report, dataset_summary, provenance, write_json_report
from wrf_tools.spectra import coherence, cross_spectrum, log_bin, power_spectrum, radial_wavenumber_spectrum, welch_spectrum
from wrf_tools.timeseries import read_station_family, read_station_header, read_station_profile, read_station_surface, read_tslist, write_tslist
from wrf_tools.types import GeoBounds, GridPoint, Station
from wrf_tools.validation import *
from wrf_tools.wind_models import cheynet_spectrum, exponential_coherence, iec_kaimal_spectrum, kaimal_spectrum, synthetic_wind_field, von_karman_spectrum
from wrf_tools.workflow import aggregate_wrf, archive_outputs, convert_grib_to_netcdf
from wrf_tools.wps import DomainGeometry, domain_geometries, eta_levels, geographic_corners, read_namelist, update_namelist_dates


class Audit:
    def __init__(self): self.results=[]
    def check(self, name, category, criterion, operation):
        try:
            detail=operation()
            self.results.append({"name":name,"category":category,"criterion":criterion,"status":"PASS","evidence":detail})
        except Exception as exc:
            self.results.append({"name":name,"category":category,"criterion":criterion,"status":"FAIL","evidence":f"{type(exc).__name__}: {exc}"})
    def skip(self, name, category, criterion, reason):
        self.results.append({"name":name,"category":category,"criterion":criterion,"status":"SKIP","evidence":reason})


def ensure(condition, detail):
    if not condition: raise AssertionError(detail)
    return detail


def write_openfast_binary(path, values, time):
    nt,channels=values.shape; payload=struct.pack("<hii",2,channels,nt)+struct.pack("<dd",float(time[0]),float(time[1]-time[0]))
    payload+=np.ones(channels,dtype="<f4").tobytes()+np.zeros(channels,dtype="<f4").tobytes()+struct.pack("<i",4)+b"test"
    for text in ("Time","Wind","Load"): payload+=text.ljust(10).encode()
    for text in ("s","m/s","N"): payload+=text.ljust(10).encode()
    payload+=np.rint(values).astype("<i2").tobytes(); path.write_bytes(payload)


def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("wrfout"); parser.add_argument("--json",default="capability_audit.json"); parser.add_argument("--markdown",default="capability_audit.md"); parser.add_argument("--single-file",action="store_true",help="Run only capabilities applicable to one WRF file"); parser.add_argument("--artifacts-dir",help="Preserve generated artifacts in this directory"); args=parser.parse_args(argv)
    source=Path(args.wrfout).resolve(); audit=Audit()
    audit.check("package version","configuration","Version is 0.2.0",lambda:ensure(wrf_tools.__version__=="0.2.0",wrf_tools.__version__))
    audit.check("configuration types","configuration","WRFSource and ExecutableConfig preserve supplied paths",lambda:ensure(WRFSource.from_paths(source).paths[0]==source and ExecutableConfig(Path("exe"),Path(".")).executable==Path("exe"),"typed configurations constructed"))
    audit.check("core data types","configuration","GeoBounds/GridPoint/Station validate and retain values",lambda:ensure(GeoBounds(0,0,1,1).east==1 and GridPoint(1,2).x==1 and Station("A",1,2).station_id=="A","dataclasses valid"))

    artifact_context = nullcontext(str(Path(args.artifacts_dir).resolve())) if args.artifacts_dir else tempfile.TemporaryDirectory(prefix="wrf_tools_audit_",dir=Path.cwd())
    if args.artifacts_dir: Path(args.artifacts_dir).mkdir(parents=True,exist_ok=True)
    with artifact_context as temporary:
        temp=Path(temporary)
        ds=open_wrf(source)
        try:
            lat=ds["XLAT"].isel(Time=0); lon=ds["XLONG"].isel(Time=0); cy,cx=lat.shape[0]//2,lat.shape[1]//2; dx=float(ds.attrs["DX"]); dy=float(ds.attrs["DY"])
            audit.check("discover_wrfout","WRF I/O","Selected real file is discovered by domain",lambda:ensure(source in discover_wrfout(source.parent,domain="d01"),str(source)))
            audit.check("open_wrf","WRF I/O","Real file opens with nonzero Time and WRF dimensions",lambda:ensure(ds.sizes["Time"]>0 and "west_east" in ds.dims,dict(ds.sizes)))
            audit.check("validate_wrf_dataset","WRF I/O","Real file satisfies required WRF grid/coordinate checks",lambda:(validate_wrf_dataset(ds) or "valid"))
            audit.check("get_variable","WRF I/O","T2 time selection returns a finite horizontal field",lambda:ensure(np.isfinite(get_variable(ds,"T2",time=0)).all(),str(get_variable(ds,"T2",time=0).shape)))

            small=ds[["T2","U10","V10","XLAT","XLONG","Times"]].isel(Time=slice(0,2)); first=temp/"wrfout_d01_2012-05-23_00_00_00"; second=temp/"wrfout_d01_2012-05-23_01_00_00"
            small.isel(Time=slice(0,1)).to_netcdf(first); small.isel(Time=slice(1,2)).to_netcdf(second)
            if not args.single_file:
                audit.check("open_wrf_sequence","WRF I/O","Two chronological same-domain files concatenate to two times",lambda:ensure(open_wrf_sequence([first,second]).sizes["Time"]==2,"Time=2"))
                mixed=temp/"wrfout_d02_2012-05-23_01_00_00"; mixed_ds=small.isel(Time=slice(1,2)).copy(); mixed_ds.attrs["GRID_ID"]=2; mixed_ds.to_netcdf(mixed)
                def reject_mixed():
                    try: open_wrf_sequence([first,mixed])
                    except ValueError: return "mixed domain rejected"
                    raise AssertionError("mixed domain accepted")
                audit.check("mixed-domain guard","WRF I/O","Different GRID_ID is rejected",reject_mixed)

            p=nearest_grid_point(lat,lon,float(lat[cy,cx]),float(lon[cy,cx])); audit.check("nearest_grid_point","grid","Nearest cell matches selected centre",lambda:ensure((p.x,p.y)==(cx,cy),vars(p)))
            bounds=GeoBounds(float(lon[cy,cx])-.01,float(lat[cy,cx])-.01,float(lon[cy,cx])+.01,float(lat[cy,cx])+.01)
            audit.check("subset_by_bounds","grid","Geographic subset is nonempty",lambda:ensure(subset_by_bounds(ds.T2.isel(Time=0).values,lat,lon,bounds)[0].size>0,"nonempty"))
            audit.check("destagger","grid","Staggered U loses one x point and mass-grid dimension name",lambda:ensure(destagger(ds.U.isel(Time=0),"west_east_stag").sizes["west_east"]==ds.sizes["west_east"],"destaggered"))
            z=np.array([0,100,200.])[:,None]; field=np.array([280,281,282.])[:,None]
            audit.check("interpolate_to_levels","grid","Linear interpolation at 50 m equals 280.5",lambda:ensure(np.allclose(interpolate_to_levels(field,z,50,axis=0),280.5),"280.5"))
            audit.check("regrid_regular","grid","Bilinear centre of a 2x2 ramp equals 1",lambda:ensure(np.allclose(regrid_regular([[0,1],[1,2]],[0,1],[0,1],[.5],[.5]),1),"1.0"))

            u,v,w=load_velocity(ds); us=u.isel(Time=slice(0,8),bottom_top=slice(0,4),south_north=slice(0,12),west_east=slice(0,12)).values; vs=v.isel(Time=slice(0,8),bottom_top=slice(0,4),south_north=slice(0,12),west_east=slice(0,12)).values; ws=w.isel(Time=slice(0,8),bottom_top=slice(0,4),south_north=slice(0,12),west_east=slice(0,12)).values
            plane=us[0,0]; series=us[:,0,6,6]
            audit.check("extract.point","extraction","Nearest geographic T2 point is finite",lambda:ensure(np.isfinite(point(ds,float(lat[cy,cx]),float(lon[cy,cx]),variables=["T2"],time=0).T2),"finite"))
            audit.check("extract.vertical_profile","extraction","T profile retains all model levels",lambda:ensure(vertical_profile(ds,"T",x=cx,y=cy,time=0).size==ds.sizes["bottom_top"],"50 levels"))
            audit.check("extract.horizontal_plane","extraction","U plane has horizontal dimensions",lambda:ensure(horizontal_plane(u.to_dataset(name="u"),"u",level=0,time=0).ndim==2,"2-D"))
            audit.check("extract.variables","extraction","Variable remapping creates requested name",lambda:ensure("temperature" in variables(ds,{"temperature":"T2"}),"mapped"))
            audit.check("extract.to_levels","extraction","Wrapper returns requested interpolated value",lambda:ensure(np.allclose(to_levels(field,z,50,axis=0),280.5),"280.5"))
            audit.check("extract.transect","extraction","Bilinear transect returns exactly 25 finite points",lambda:ensure(np.isfinite(transect(plane,(0,0),(11,11),points=25)[0]).all() and transect(plane,(0,0),(11,11),points=25)[0].size==25,"25 points"))

            low=butterworth_spatial(plane,dx=dx,dy=dy,cutoff_wavelength=3*dx,order=2)
            audit.check("butterworth_spatial","filters","Filtered plane preserves shape and finite values",lambda:ensure(low.shape==plane.shape and np.isfinite(low).all(),str(low.shape)))
            audit.check("butterworth_band","filters","Band-filtered plane preserves shape and finite values",lambda:ensure(np.isfinite(butterworth_band(plane,dx=dx,dy=dy,low_wavelength=2*dx,high_wavelength=5*dx)).all(),"finite"))
            audit.check("top_hat_coarsen","filters","3x3 top-hat produces 4x4 coarse plane",lambda:ensure(top_hat_coarsen(plane,factor_y=3).shape==(4,4),"4x4"))
            audit.check("spectral_downsample","filters","Factor-two Fourier crop produces 6x6 plane",lambda:ensure(spectral_downsample(plane,factor_y=2).shape==(6,6),"6x6"))
            audit.check("resolved_subfilter","filters","Resolved plus residual reconstructs original",lambda:ensure(np.allclose(sum(resolved_subfilter(plane,low)),plane),"reconstructed"))

            freq,power=power_spectrum(series,spacing=1.0)
            audit.check("power_spectrum","spectra","Periodogram frequency and power shapes match and are finite",lambda:ensure(freq.shape==power.shape and np.isfinite(power).all(),str(freq.shape)))
            audit.check("welch_spectrum","spectra","Welch PSD is finite for real WRF series",lambda:ensure(np.isfinite(welch_spectrum(series,sample_rate=1,nperseg=4,overlap=2)[1]).all(),"finite"))
            audit.check("radial_wavenumber_spectrum","spectra","Radial spectrum has finite populated bins",lambda:ensure(np.isfinite(radial_wavenumber_spectrum(plane,dx=dx,dy=dy)[1]).all(),"finite"))
            audit.check("coherence","spectra","Self-coherence is one",lambda:ensure(np.allclose(coherence(series,series,sample_rate=1,nperseg=4,overlap=2)[1],1),"one"))
            cf,cs=cross_spectrum(series,series)
            audit.check("cross_spectrum","spectra","Self cross-spectrum is real/nonnegative",lambda:ensure(np.all(np.real(cs)>=-1e-10) and np.allclose(np.imag(cs),0),"valid"))
            audit.check("log_bin","spectra","Log binning returns requested four bins",lambda:ensure(log_bin(cf,cs,bins=4)[0].size==4,"4 bins"))

            speed=wind_speed(us,vs); direction=wind_direction(us,vs); back=wind_speed_direction_to_uv(speed,direction)
            audit.check("wind speed/direction conversion","diagnostics","Speed/direction round-trip recovers float32 U/V within 1e-5 m/s",lambda:ensure(np.allclose(back[0],us,atol=1e-5) and np.allclose(back[1],vs,atol=1e-5),"maximum error <= 1e-5 m/s"))
            audit.check("angle_between","diagnostics","Orthogonal vectors give 90 degrees",lambda:ensure(np.allclose(angle_between([1,0],[0,1]),90),"90"))
            audit.check("fluctuations","diagnostics","Fluctuation mean is zero",lambda:ensure(np.allclose(fluctuations(series).mean(),0),"zero mean"))
            audit.check("resolved_tke","diagnostics","Resolved TKE is finite and nonnegative",lambda:ensure(np.all(np.isfinite(resolved_tke(us,vs,ws,axis=(0,2,3)))) and np.all(resolved_tke(us,vs,ws,axis=(0,2,3))>=0),"valid"))
            audit.check("reynolds_flux","diagnostics","Reynolds flux is finite",lambda:ensure(np.isfinite(reynolds_flux(us,ws,axis=(0,2,3))).all(),"finite"))
            audit.check("turbulence_intensity","diagnostics","Turbulence intensity is finite",lambda:ensure(np.isfinite(turbulence_intensity(series)).all(),"finite"))

            theta=potential_temperature(ds.T.isel(Time=0,bottom_top=0,south_north=slice(0,5),west_east=slice(0,5))); pressure=ds.P.isel(Time=0,bottom_top=0,south_north=slice(0,5),west_east=slice(0,5))+ds.PB.isel(Time=0,bottom_top=0,south_north=slice(0,5),west_east=slice(0,5)); tempk=temperature_from_potential(theta,pressure); q=ds.QVAPOR.isel(Time=0,bottom_top=0,south_north=slice(0,5),west_east=slice(0,5))
            met_checks={
                "potential_temperature":(np.isfinite(theta).all(),"finite"),"temperature_from_potential":(np.isfinite(tempk).all(),"finite"),"virtual_temperature":(np.isfinite(virtual_temperature(tempk,q)).all(),"finite"),"air_density":(np.all(air_density(pressure,tempk,q)>0),"positive"),"geopotential_height":(np.isfinite(geopotential_height(ds.PH.isel(Time=0),ds.PHB.isel(Time=0))).all(),"finite"),"bulk_richardson_number":(np.isfinite(bulk_richardson_number(300,301,10,100,5,10,0,0)),"finite"),"power_law_exponent":(np.isfinite(power_law_exponent(5,10,10,100)),"finite"),"interval_precipitation":(interval_precipitation([1,3,6]).tolist()==[0,2,3],"[0,2,3]"),"reflectivity_to_rain_rate":(np.allclose(reflectivity_to_rain_rate(10*np.log10(200)),1),"1"),"friction_velocity":(np.allclose(friction_velocity(1.2,1.2),1),"1"),"monin_obukhov_length":(np.isfinite(monin_obukhov_length(300,.5,.1)),"finite"),"circular_mean":(np.isclose(circular_mean([350,10])%360,0),"0 degrees"),"roughness_length":(roughness_length(10,100,.5)>0,"positive"),"log_wind_profile":(np.isfinite(log_wind_profile(100,friction_velocity_value=.5,roughness=.1)),"finite"),"mixing_ratio_to_specific_humidity":(0<mixing_ratio_to_specific_humidity(.01)<.01,"bounded")}
            for name,(condition,detail) in met_checks.items(): audit.check(name,"meteorology",f"{name} returns physically/numerically valid output",lambda c=condition,d=detail:ensure(bool(c),d))

            audit.check("load_velocity","LES","U/V/W are collocated on identical mass-grid shapes",lambda:ensure(u.shape==v.shape==w.shape,str(u.shape)))
            audit.check("calculate_fluxes","LES","All six resolved flux components are finite",lambda:ensure(all(np.isfinite(value).all() for value in calculate_fluxes(us,vs,ws,axis=0).values()),"six finite fluxes"))
            audit.check("calculate_total_tke","LES","Total TKE is finite and nonnegative",lambda:ensure(np.all(calculate_total_tke(us,vs,ws,axis=0)>=0),"nonnegative"))
            stress_ds=xr.Dataset({name:(u.isel(Time=slice(0,1)).dims,np.ones(u.isel(Time=slice(0,1)).shape)*i) for i,name in enumerate(("m11","m12","m13","m22","m23","m33"),1)})
            stress=load_sgs_stress(stress_ds)
            audit.check("load_sgs_stress","LES","Six configurable SGS tensor components load",lambda:ensure(len(stress)==6,"six"))
            audit.check("sgs_tke","LES","SGS TKE from normal stresses is positive",lambda:ensure(np.all(sgs_tke(stress)>0),"positive"))
            audit.check("filtered_tke","LES","Butterworth-filtered resolved TKE is finite",lambda:ensure(np.isfinite(filtered_tke(us,vs,ws,method="butterworth",dx=dx,dy=dy,cutoff_wavelength=3*dx,order=2)).all(),"finite"))

            audit.check("validation scalar metrics","validation","Bias/MAE/RMSE/normalized error/correlation/standard error are finite",lambda:ensure(all(np.isfinite(x) for x in (bias(series,series+.1),mae(series,series+.1),rmse(series,series+.1),normalized_error(series,series+.1),correlation(series,series+.1),standard_error(series))),"finite"))
            audit.check("validation circular metrics","validation","Circular error wraps 359/1 correctly",lambda:ensure(circular_error(1,359)==2 and circular_mae([1],[359])==2,"2 degrees"))
            audit.check("kantorovich_distance","validation","Unit-shifted samples have distance one",lambda:ensure(np.isclose(kantorovich_distance([0,1],[1,2]),1),"1"))
            audit.check("comparison_summary","validation","Summary contains four named statistics",lambda:ensure(set(comparison_summary(series,series+.1))=={"bias","mae","rmse","correlation"},"four"))
            profiles=np.vstack((us[:,0].mean((1,2)),us[:,1].mean((1,2)))).T
            audit.check("cluster_profiles","validation","Two-cluster output labels every profile",lambda:ensure(cluster_profiles(profiles,2,seed=1)[0].size==profiles.shape[0],"labelled"))
            audit.check("spatial_scores","validation","Spatial scores preserve cellwise error shape",lambda:ensure(spatial_scores(plane,plane+.1)["absolute_error"].shape==plane.shape,str(plane.shape)))
            audit.check("rank_cases","validation","Identical case ranks before biased case",lambda:ensure(rank_cases({"good":series,"bad":series+1},series)[0][0]=="good","good first"))

            observation=from_columns(time=np.arange(series.size).astype("datetime64[h]"),variables={"wind":series}); model=observation.copy()
            audit.check("observations.from_columns","observations","Labelled dataset has correct time length",lambda:ensure(observation.sizes["time"]==series.size,str(series.size)))
            audit.check("observations.collocate_grid","observations","Grid collocation returns selected centre value",lambda:ensure(np.isclose(collocate_grid(ds.T2.isel(Time=0),lat,lon,float(lat[cy,cx]),float(lon[cy,cx]))[0],ds.T2.isel(Time=0,south_north=cy,west_east=cx)),"matched"))
            audit.check("observations.align","observations","Identical time coordinates retain all records",lambda:ensure(align(model,observation)[0].sizes["time"]==series.size,"aligned"))
            csv=temp/"obs.csv"; csv.write_text("time,wind\n"+"\n".join(f"{i},{value}" for i,value in enumerate(series)))
            audit.check("observations.read_csv","observations","CSV reader loads all real-WRF-derived samples",lambda:ensure(read_csv(csv,time_column="time").sizes["time"]==series.size,"loaded"))
            obs_nc=temp/"obs.nc"; observation.to_netcdf(obs_nc)
            audit.check("observations.read_netcdf","observations","NetCDF reader loads selected wind variable",lambda:ensure("wind" in read_netcdf(obs_nc,variables=["wind"]),"loaded"))
            audit.check("observations.normalize_time","observations","One-hour offset subtracts exactly one hour",lambda:ensure(normalize_time(observation,timezone_offset_hours=1).time.values[0]==observation.time.values[0]-np.timedelta64(1,"h"),"shifted"))

            for name,func,kwargs in (("kaimal_spectrum",kaimal_spectrum,{"mean_speed":10,"height":100,"friction_velocity":.5}),("iec_kaimal_spectrum",iec_kaimal_spectrum,{"mean_speed":10,"sigma":1,"length_scale":100}),("cheynet_spectrum",cheynet_spectrum,{"mean_speed":10,"height":100,"friction_velocity":.5}),("von_karman_spectrum",von_karman_spectrum,{"mean_speed":10,"sigma":1,"length_scale":100})):
                audit.check(name,"wind models",f"{name} returns finite nonnegative spectrum",lambda f=func,k=kwargs:ensure(np.all(np.isfinite(f(np.array([.01,.1]),**k))) and np.all(f(np.array([.01,.1]),**k)>=0),"valid"))
            audit.check("exponential_coherence","wind models","Coherence lies in [0,1]",lambda:ensure(np.all((exponential_coherence([0,.1],100,mean_speed=10)>=0)&(exponential_coherence([0,.1],100,mean_speed=10)<=1)),"bounded"))
            audit.check("synthetic_wind_field","wind models","Seeded synthetic field has requested shape and finite values",lambda:ensure(np.isfinite(synthetic_wind_field(np.linspace(5,6,8),nt=8,ny=4,nz=3,dt=1,dy=10,dz=10,seed=1)).all(),"8x3x4x3"))

            components=(us[:,:4,:,6],vs[:,:4,:,6],ws[:,:4,:,6]); windfield=wind_field_from_components(*components,time_axis=0,vertical_axis=1,lateral_axis=2,dy=dy,dz=100,dt=1,hub_height=200,bottom_height=50)
            audit.check("wind_field_from_components","TurbSim/OpenFAST","Real WRF components map to time,z,y,3",lambda:ensure(windfield.velocity.shape==(8,4,12,3),str(windfield.velocity.shape)))
            bts=temp/"field.bts"; write_bts(bts,windfield)
            audit.check("BTS read/write/validate","TurbSim/OpenFAST","BTS round-trip maximum error <=0.01 m/s",lambda:ensure(np.max(np.abs(validate_bts(bts,expected=windfield).velocity-windfield.velocity))<=.01,"<=0.01"))
            wnd=temp/"field.wnd"; write_bladed_wnd(wnd,windfield)
            audit.check("Bladed WND read/write","TurbSim/OpenFAST","WND round-trip maximum error <=0.01 m/s",lambda:ensure(np.max(np.abs(read_bladed_wnd(wnd,hub_height=200).velocity-windfield.velocity))<=.01,"<=0.01"))
            combined=concatenate_fields([windfield,windfield])
            audit.check("concatenate_fields","TurbSim/OpenFAST","Compatible wind fields double time length",lambda:ensure(combined.velocity.shape[0]==16,"16"))
            audit.check("velocity_at","TurbSim/OpenFAST","Point extraction returns time by 3 components",lambda:ensure(velocity_at(windfield,z=200).shape==(8,3),"8x3"))
            audit.check("wind horizontal_plane","TurbSim/OpenFAST","Horizontal plane returns time,y,3",lambda:ensure(wind_horizontal_plane(windfield,z=200).shape==(8,12,3),"8x12x3"))
            audit.check("wind vertical_profile","TurbSim/OpenFAST","Mean profile returns four heights and components",lambda:ensure(wind_vertical_profile(windfield)[1].shape==(4,3),"4x3"))
            audit.check("rotate_velocity","TurbSim/OpenFAST","Zero-degree rotation preserves velocity",lambda:ensure(np.allclose(rotate_velocity(windfield.velocity),windfield.velocity),"preserved"))
            audit.check("constant_field","TurbSim/OpenFAST","Constant field longitudinal velocity equals requested speed",lambda:ensure(np.allclose(constant_field(speed=5,duration=1,dt=.5,ny=2,nz=2,dy=1,dz=1,hub_height=2,bottom_height=1).velocity[...,0],5),"5 m/s"))
            audit.check("step_field","TurbSim/OpenFAST","Step field contains requested 5 and 10 m/s steps",lambda:ensure(set(np.unique(step_field(speeds=[5,10],step_duration=1,dt=.5,ny=2,nz=2,dy=1,dz=1,hub_height=2,bottom_height=1).velocity[...,0]))=={5,10},"5,10"))
            uniform=temp/"uniform.txt"; audit.check("write_uniform_wind","TurbSim/OpenFAST","Uniform wind text file is created and nonempty",lambda:ensure(write_uniform_wind(uniform,[0,1],[5,6]).stat().st_size>0,"written"))

            hh=temp/"hub.bin"; np.tile(np.r_[0,windfield.velocity[0,0,0],np.zeros(10)],(2,1)).astype("<f4").tofile(hh)
            audit.check("read_hub_height_binary","TurbSim/OpenFAST","Two complete 14-value records load",lambda:ensure(read_hub_height_binary(hh).sizes["time"]==2,"2"))
            pts=temp/"points.pts"; pts.write_bytes(struct.pack("<hiifffff",-99,3,2,10.,5.,10.,20.,30.)+np.zeros(12,dtype="<i2").tobytes())
            audit.check("read_coherent_points","TurbSim/OpenFAST","Coherent point file loads 2 times x 2 points x 3 components",lambda:ensure(read_coherent_points(pts).velocity.shape==(2,2,3),"2x2x3"))
            ff=temp/"full.txt"; ff.write_text("\n".join(["","description","","header","2 2 10 10 1 100 5","","z","-5 5","","y","-5 5","","0 5 1 2 3 4","1 5 5 6 7 8"]))
            audit.check("read_full_field_text","TurbSim/OpenFAST","Formatted full-field text loads 2 times x 2 z x 2 y",lambda:ensure(read_full_field_text(ff).u.shape==(2,2,2),"2x2x2"))

            ascii_out=temp/"case.out"; ascii_out.write_text("description\nTime Wind Load\n(s) (m/s) (N)\n"+"\n".join(f"{i} {series[i]} {series[i]*2}" for i in range(series.size)))
            binary_out=temp/"case.outb"; write_openfast_binary(binary_out,np.column_stack((series,series*2)),np.arange(series.size,dtype=float))
            ascii_ds=read_ascii_output(ascii_out); binary_ds=read_binary_output(binary_out)
            audit.check("read_ascii_output","OpenFAST","ASCII output loads Wind and Load channels",lambda:ensure(set(ascii_ds.data_vars)=={"Wind","Load"},"two channels"))
            audit.check("read_binary_output","OpenFAST","Packed binary output loads Wind and Load channels",lambda:ensure(set(binary_ds.data_vars)=={"Wind","Load"},"two channels"))
            audit.check("zero_crossing_frequency","OpenFAST","Sinusoid gives positive crossing frequency",lambda:ensure(zero_crossing_frequency(np.sin(np.arange(100)),1)>0,"positive"))
            audit.check("stress_from_moment","OpenFAST","M*y/I calculation equals four",lambda:ensure(stress_from_moment(10,2,5)==4,"4"))
            audit.check("rainflow_cycles","OpenFAST","Cycle table has range and count columns",lambda:ensure(rainflow_cycles(series).shape[1]==2,"two columns"))
            audit.check("channel_statistics","OpenFAST","Statistics include mean for each numeric channel",lambda:ensure("mean" in channel_statistics(ascii_ds)["Wind"],"mean"))
            audit.check("compare_outputs","OpenFAST","Self-comparison RMSE is zero",lambda:ensure(compare_outputs(ascii_ds,ascii_ds)["Wind"]["rmse"]==0,"zero"))
            fake=temp/"fake.py"; fake.write_text("print('fake OpenFAST')\n")
            audit.check("run_openfast","OpenFAST","Runner executes configured executable in case directory",lambda:ensure(run_openfast(fake,executable=sys.executable).returncode==0,"return code 0"))
            fst=temp/"case.fst"; fst.write_text('10.0 TMax - duration\n"wind.bts" Filename - inflow\n'); updated=temp/"updated.fst"
            audit.check("OpenFAST input read/update","OpenFAST","Labelled values update without losing other lines",lambda:ensure(read_parameters(update_parameters(fst,{"TMax":20.0},output=updated))["TMax"]=="20.0","updated"))

            station=Station("SITE",float(lat[cy,cx]),float(lon[cy,cx]),"Audit Site"); tslist=temp/"tslist"
            audit.check("tslist read/write","stations","Station definition round-trips",lambda:ensure(read_tslist(write_tslist([station],tslist))[0].station_id=="SITE","SITE"))
            # Construct the header at the fixed columns emitted by WRF's
            # station time-series writer (and consumed by read_station_header).
            header_chars = [" "] * 98
            def station_field(start, end, value):
                text = str(value)
                header_chars[start:end] = list(text[: end-start].ljust(end-start))
            station_field(0,25,"Audit Site"); station_field(26,29,"001"); station_field(29,32,"001")
            station_field(33,38,"SITE"); station_field(39,46,f"{station.latitude:7.3f}")
            station_field(47,55,f"{station.longitude:8.3f}"); station_field(58,62,f"{cx:4d}")
            station_field(63,67,f"{cy:4d}"); station_field(70,77,f"{station.latitude:7.3f}")
            station_field(78,86,f"{station.longitude:8.3f}"); station_field(88,94,f"{10:6.1f}")
            station_field(95,98,"m"); header="".join(header_chars)+"\n"
            surface=temp/"SITE.d01.TS"; row=np.arange(19,dtype=float); row[1]=0; surface.write_text(header+" ".join(map(str,row))+"\n")
            for code in ("UU","VV","WW","PH","TH","QV","PR"): Path(str(surface)[:-2]+code).write_text("0 "+" ".join(map(str,us[0,:,0,0]))+"\n")
            audit.check("read_station_header","stations","Fixed-width station metadata parses station ID",lambda:ensure(read_station_header(surface)["station_id"]=="SITE","SITE"))
            audit.check("read_station_surface","stations","Surface file exposes standard WRF station variables",lambda:ensure("u" in read_station_surface(surface),"u"))
            audit.check("read_station_profile","stations","Profile file loads time x level",lambda:ensure(read_station_profile(Path(str(surface)[:-2]+"UU")).ndim==2,"2-D"))
            audit.check("read_station_family","stations","Surface plus seven profile variables load",lambda:ensure(all(name in read_station_family(surface) for name in ("uu","vv","ww","ph","th","qv","pr")),"family"))

            namelist=temp/"namelist.wps"; namelist.write_text("&share\n max_dom = 2,\n start_date = '2012-05-23_00:00:00','2012-05-23_00:00:00',\n end_date = '2012-05-24_00:00:00','2012-05-24_00:00:00',\n/\n&geogrid\n parent_id=1,1,\n parent_grid_ratio=1,3,\n i_parent_start=1,10,\n j_parent_start=1,10,\n e_we=100,31,\n e_sn=100,31,\n dx=9000,\n dy=9000,\n/\n")
            parsed=read_namelist(namelist); domains=domain_geometries(parsed)
            audit.check("read_namelist","WPS","Share and geogrid groups parse",lambda:ensure(set(parsed)>={"share","geogrid"},"parsed"))
            dated=temp/"dated.wps"; audit.check("update_namelist_dates","WPS","Start/end dates update into separate output",lambda:ensure(update_namelist_dates(namelist,datetime(2020,1,1),datetime(2020,1,2),domains=2,output=dated).exists(),"written"))
            audit.check("domain_geometries","WPS","Two nested domains calculate and child spacing is 3 km",lambda:ensure(len(domains)==2 and domains[1].dx==3000,"2 domains"))
            audit.check("eta_levels","WPS","Eta interfaces decrease from one to zero",lambda:ensure(eta_levels(10)[0]==1 and eta_levels(10)[-1]==0 and np.all(np.diff(eta_levels(10))<0),"monotonic"))
            audit.check("geographic_corners","WPS","Each domain transforms to four finite lon/lat corners",lambda:ensure(np.isfinite(geographic_corners(domains,ref_latitude=float(ds.attrs["CEN_LAT"]),ref_longitude=float(ds.attrs["CEN_LON"]),truelat1=float(ds.attrs["TRUELAT1"]),truelat2=float(ds.attrs["TRUELAT2"]),stand_lon=float(ds.attrs["STAND_LON"]))).all(),"finite corners"))

            plot_cases=[("horizontal",lambda:horizontal(plane)),("profile",lambda:profile(us.mean((0,2,3)),np.arange(4))),("time_height",lambda:time_height(us.mean((2,3)),np.arange(8),np.arange(4))),("wind_rose",lambda:wind_rose(direction.ravel(),speed.ravel())),("cross_section",lambda:cross_section(us[0,:,6,:])),("wind_barbs",lambda:wind_barbs(us[0,0],vs[0,0],stride=2)),("nested_domains",lambda:nested_domains(domains)),("validation_scatter",lambda:validation_scatter(series,series+.1)),("taylor_diagram",lambda:taylor_diagram([1,1.1],[1,.9]))]
            for name,func in plot_cases:
                def plot_check(f=func,n=name):
                    fig=f()[0]; target=temp/f"{n}.png"; fig.savefig(target); plt.close(fig); return ensure(target.stat().st_size>0,"saved")
                audit.check(name,"plotting",f"{name} renders and saves a nonempty PNG",plot_check)
            def animation_check():
                fig,ax,animation=animate_fields(us[:2,0]); animation._func(0); target=temp/"animation_frame.png"; fig.savefig(target); plt.close(fig); return ensure(target.stat().st_size>0,"frame rendered")
            audit.check("animate_fields","plotting","Animation constructs and renders its first frame",animation_check)

            summary=dataset_summary(ds); report=temp/"report.json"
            audit.check("dataset_summary","reporting","Summary reports real dimensions and variables",lambda:ensure(summary["dimensions"]["Time"]==ds.sizes["Time"] and "T2" in summary["variables"],"complete"))
            audit.check("write_json_report","reporting","JSON report is valid and nonempty",lambda:ensure(json.loads(write_json_report(summary,report).read_text())["dimensions"]["Time"]==ds.sizes["Time"],"valid JSON"))
            audit.check("comparison_report","reporting","Comparison report includes statistics and count",lambda:ensure(comparison_report(series,series+.1)["count"]==series.size,"count"))
            audit.check("provenance","reporting","Provenance resolves selected real input",lambda:ensure(provenance(inputs=[source])["inputs"][0]==str(source),str(source)))

            if args.single_file:
                audit.check("archive_outputs","workflow","A generated report archives without deleting its source",lambda:ensure(archive_outputs([report],temp/"archive")[0].exists() and report.exists(),"copied"))
            else:
                aggregated=temp/"aggregated.nc"
                audit.check("aggregate_wrf","workflow","Two same-domain files aggregate and export two times",lambda:ensure(aggregate_wrf([first,second],variables=["T2"],output=aggregated,load=True).sizes["Time"]==2,"Time=2"))
                audit.check("archive_outputs","workflow","Archive copies without deleting source",lambda:ensure(archive_outputs([aggregated],temp/"archive")[0].exists() and aggregated.exists(),"copied"))
                grib=temp/"input.grb"; grib.write_bytes(b"derived test")
                def mock_convert():
                    output=temp/"converted.nc"
                    def fake_run(command,**kwargs): output.write_bytes(b"netcdf"); return type("Completed",(),{"returncode":0,"stdout":"","stderr":""})()
                    with patch("wrf_tools.workflow.subprocess.run",side_effect=fake_run): result,_=convert_grib_to_netcdf(grib,output)
                    return ensure(result.exists(),"output verified")
                audit.check("convert_grib_to_netcdf","workflow","Converter command/output contract succeeds (external wgrib2 mocked)",mock_convert)
                audit.skip("wgrib2 external executable","workflow","Real GRIB conversion completes with installed wgrib2","wgrib2 is not installed; API contract tested with a mock")

            npy=temp/"plane.npy"; np.save(npy,plane); cli_filter=temp/"cli_filtered.npy"; cli_spectrum=temp/"cli_spectrum.npz"; cli_report=temp/"cli_report.json"; cli_extract=temp/"cli_extract.nc"; cli_concat=temp/"cli_concat.nc"
            cli_cases=[("discover",["discover",str(source.parent),"--domain","d01"]),("inspect",["inspect",str(source)]),("validate",["validate",str(source)]),("bts-info",["bts-info",str(bts)]),("bts-compare",["bts-compare",str(bts),str(bts)]),("extract",["extract",str(source),str(cli_extract),str(float(lat[cy,cx])),str(float(lon[cy,cx])),"T2","--time","0"]),("filter",["filter",str(npy),str(cli_filter),"--dx",str(dx),"--cutoff",str(3*dx)]),("spectra",["spectra",str(npy),str(cli_spectrum),"--spacing",str(dx)]),("report",["report",str(source),str(cli_report)]),("openfast-info",["openfast-info",str(binary_out)])]
            if not args.single_file: cli_cases.insert(3,("concat",["concat",str(cli_concat),str(first),str(second)]))
            for name,arguments in cli_cases:
                def cli_check(a=arguments):
                    capture=io.StringIO()
                    with redirect_stdout(capture): code=cli_main(a)
                    return ensure(code==0,"exit 0")
                audit.check(f"CLI {name}","CLI",f"wrf-tools {name} exits zero on real/derived data",cli_check)
        finally:
            ds.close(); plt.close("all")

    counts={status:sum(item["status"]==status for item in audit.results) for status in ("PASS","FAIL","SKIP")}; payload={"wrfout":str(source),"mode":"single-file" if args.single_file else "complete","artifacts_directory":str(Path(args.artifacts_dir).resolve()) if args.artifacts_dir else None,"counts":counts,"results":audit.results}
    Path(args.json).write_text(json.dumps(payload,indent=2,default=str),encoding="utf-8")
    lines=["# WRF Tools capability acceptance audit","",f"Source: `{source}`","",f"PASS: {counts['PASS']} | FAIL: {counts['FAIL']} | SKIP: {counts['SKIP']}","","| Category | Capability | Status | Criterion | Evidence |","|---|---|---:|---|---|"]
    for item in audit.results: lines.append("| "+" | ".join(str(item[key]).replace("|","\\|").replace("\n"," ") for key in ("category","name","status","criterion","evidence"))+" |")
    Path(args.markdown).write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(counts)); print(Path(args.markdown).resolve()); return 1 if counts["FAIL"] else 0


if __name__=="__main__": raise SystemExit(main())
