"""Chapter 3: synthetic WRF files -> selection -> physical coordinates -> report."""
import numpy as np
from wrf_tools.types import GeoBounds
from .data import synthetic_wrf


def run(c):
    call=c.call; root=c.output/"wrf"; root.mkdir()
    ds=synthetic_wrf()
    # Two files, multiple times each: opening and sorting are really exercised.
    for start,stop in [(0,16),(16,32)]:
        name=bytes(ds.Times.values[start]).decode().replace(":","_")
        ds.isel(Time=slice(start,stop)).to_netcdf(root/f"wrfout_d01_{name}")
    files=call("io.discovery.discover_wrfout",root,domain="d01")
    with call("io.datasets.open_wrf",files[0]): pass
    c.dataset=call("io.datasets.open_wrf_sequence",files)
    ds=c.dataset
    call("io.validation.validate_wrf_dataset",ds)
    call("io.datasets.get_variable",ds,"U",time=-1,destagger_native=True)
    cell=call("grid.coordinates.nearest_grid_point",ds.XLAT.isel(Time=0),ds.XLONG.isel(Time=0),52,5)
    c.cell=cell; c.files=files
    call("grid.coordinates.subset_by_bounds",ds.T2.values,ds.XLAT.isel(Time=0),ds.XLONG.isel(Time=0),GeoBounds(4.9,51.9,5.1,52.1))
    call("extract.point",ds,52,5,variables=["U","V"],destagger_native=True)
    call("extract.vertical_profile",ds,"U",x=cell.x,y=cell.y,destagger_native=True)
    call("extract.horizontal_plane",ds,"T",level=1)
    call("extract.variables",ds,{"temperature_2m":"T2"})
    call("extract.to_levels",[1,2,3],[10,20,30],[15,25])
    call("extract.transect",ds.T2.isel(Time=0),(0,0),(7,7),points=12)
    call("grid.destagger.destagger",ds.U,"west_east_stag")
    call("grid.destagger.destagger_wrf",ds.W)
    call("grid.interpolation.interpolate_to_levels",[1,2,3],[10,20,30],[15,25],axis=0)
    call("grid.interpolation.regrid_regular",np.arange(16).reshape(4,4),[0,1,2,3],[0,1,2,3],[.5,1.5],[.5,1.5])
    call("averaging.wrf_cell_area",ds)
    call("observations.collocate_grid",ds.T2.values,ds.XLAT.isel(Time=0),ds.XLONG.isel(Time=0),52,5)
    velocity=call("les.diagnostics.load_velocity",ds)
    call("les.diagnostics.calculate_fluxes",*[v.isel(south_north=cell.y,west_east=cell.x) for v in velocity])
    stress=call("les.diagnostics.load_sgs_stress",ds)
    energy=call("les.diagnostics.sgs_tke",stress)
    call("les.diagnostics.calculate_total_tke",*velocity,subgrid_tke=energy.mean(axis=0))
    call("les.diagnostics.filtered_tke",*[v.isel(Time=0).values for v in velocity],method="top_hat",factor_y=2)
    call("turbulence.model_tke_sources",ds)
    call("turbulence.model_tke",ds)
    call("turbulence.tke_diagnostics_data",ds,cell)
    call("turbulence.save_tke_diagnostics",ds,cell,c.output/"synthetic-tke",top=600,sources=files)
    call("visualization.history_times",ds)
    call("visualization.rotate_wind",1,0,0,1)
    call("visualization.surface_wind",ds,time=0)
    call("visualization.mass_heights",ds.PH.isel(Time=0),ds.PHB.isel(Time=0),axis=0)
    call("visualization.temperature_celsius",ds.T.isel(Time=0),ds.PB.isel(Time=0))
    call("visualization.interpolate_columns",[[1,2,3]],[[10,20,30]],[15,25])
    call("visualization.wrf_projection",ds)
    call("visualization.wind_overview_data",ds,cell,top=600)
    figure,_=call("visualization.plot_wind_overview",ds,cell,top=600)
    c.save(figure,"synthetic-wind-overview.png")
    call("visualization.save_wind_overview",ds,cell,c.output/"synthetic-wind-overview",top=600,sources=files)
    issues=call("quality.quality_control",ds[["T2","U10","V10","Times"]])
    call("quality.print_qc_report",issues)
    call("hindcast.summarize_hindcast",ds,files=files,cell=cell)
    call("diagnostic_groups.run_diagnostic_groups",ds,cell,c.output/"groups",groups="all",options={
        "flow_heights_metres":[100,200,300],"turbulence_average":"time", "profile_top_metres":600,
        "minimum_turbulence_samples":32,"max_turbulence_interval_seconds":10})
    # Compact report exercises the full writer; groups were exercised above.
    call("hindcast.create_hindcast_report",root,c.output/"synthetic-report",diagnostic_groups="none")
    call("contours3d.horizontal_contours",np.ones((2,8,8))*np.arange(8)[None,None,:],np.arange(8),np.arange(8),[100,200],[2,4])
    call("contours3d.export_contour_sequence",root,c.output/"synthetic-contours.json",domain="d01",
        heights=[100,200,300],thresholds=[6,7,8,9],maximum_frames=2)
    # Same model-shaped fixture, explicitly synthetic. Do not invent coastline
    # observations: this binary mask only exercises land/water display handling.
    iso_ds = ds.copy()
    iso_ds["LANDMASK"] = (ds.HGT.dims, np.broadcast_to(np.arange(8)[None,None,:] >= 3, ds.HGT.shape).astype(float))
    iso_root = c.output/"isosurface-input"; iso_root.mkdir()
    iso_ds.isel(Time=slice(0,2)).to_netcdf(iso_root/"wrfout_d01_2025-01-01_00_00_00")
    k,j,i = np.indices((3,3,3), dtype=float)
    call("isosurfaces.isosurface_mesh", i+j+k, 50+100*k, [0,1,2], [0,1,2], 2.5)
    iso_geometry = call("isosurfaces.export_isosurface_sequence", iso_root,c.output/"synthetic-isosurfaces.json",domain="d01",
        thresholds=[7,8],top_metres=500,horizontal_stride=1,maximum_frames=2)
    call("interactive.isosurface_figure",iso_geometry)
    call("interactive.write_isosurface_html",iso_geometry,c.output/"synthetic-interactive.html")
    # Same public exporter, optional multi-diagnostic mode. These are synthetic
    # execution checks, not a claim that these coarse fields contain LES eddies.
    diagnostics = call("isosurfaces.export_isosurface_sequence",iso_root,
        c.output/"synthetic-diagnostics.json",domain="d01",top_metres=500,horizontal_stride=2,
        maximum_frames=2,diagnostics={"wind_speed":[7,8],"vertical_velocity":[-.1,.1],
            "vertical_vorticity":[-1e-4,1e-4],"q_criterion":[1e-8],"model_tke":[.5,1.]})
    call("interactive.isosurface_figure",diagnostics)
    call("interactive.write_isosurface_html",diagnostics,c.output/"synthetic-diagnostic-explorer.html")
    # Two frames keep this example quick; not a Manim render or energy diagnosis.
    movie=call("animations.create_wind_animation",root,c.output/"synthetic-animation",maximum_frames=2)
    call("animations.read_animation_manifest",movie["manifest"])
    with call("workflow.aggregate_wrf",files,variables=["T2"],load=True,output=c.output/"aggregated.nc"): pass
    call("workflow.archive_outputs",[c.output/"aggregated.nc"],c.output/"archive")
