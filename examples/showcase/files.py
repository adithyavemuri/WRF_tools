"""Chapter 2: actual file operations with SYNTHETIC format fixtures.

These fixtures exercise supported parsers and round trips, not real instrument
validation or external OpenFAST interoperability. Nothing is run externally.
"""
from datetime import datetime
import struct
import numpy as np
from wrf_tools.types import Station


def run(c):
    call=c.call; root=c.output/"formats"; root.mkdir()
    prefix="coupling.openfast.operations."
    settings=dict(dt=1,ny=3,nz=3,dy=10,dz=10,hub_height=100,bottom_height=90)
    first=call(prefix+"constant_field",speed=8,duration=3,**settings)
    stepped=call(prefix+"step_field",speeds=[8,10],step_duration=3,**settings)
    call(prefix+"concatenate_fields",[first,stepped])
    call(prefix+"velocity_at",stepped,z=100)
    call(prefix+"horizontal_plane",stepped,z=100)
    call(prefix+"vertical_profile",stepped)
    call(prefix+"rotate_velocity",stepped.velocity,horizontal_degrees=30)
    # WindType=2 needs all eight columns, even for a zero-shear example. Do not
    # confuse this with the separate binary full-field Bladed .wnd format.
    uniform=call(prefix+"write_uniform_wind",root/"uniform.wnd",[0,1,2],[8,9,10],power_law_shear=.2)
    assert np.loadtxt(uniform,comments="!").shape==(3,8)
    velocity=stepped.velocity
    call("coupling.openfast.wrf_les.wind_field_from_components",velocity[...,0],velocity[...,1],velocity[...,2],
         time_axis=0,vertical_axis=1,lateral_axis=2,dy=10,dz=10,dt=1,hub_height=100,bottom_height=90)
    bts=call("coupling.openfast.bts.write_bts",root/"inflow.bts",stepped)
    call("coupling.openfast.bts.read_bts",bts)
    call("coupling.openfast.bts.validate_bts",bts,expected=stepped)
    wnd=call("coupling.openfast.formats.write_bladed_wnd",root/"bladed.wnd",stepped)
    call("coupling.openfast.formats.read_bladed_wnd",wnd,hub_height=100)

    # Deliberately minimal supported legacy record layouts, not general readers.
    np.arange(28,dtype="<f4").tofile(root/"hub.hh")
    call("coupling.openfast.formats.read_hub_height_binary",root/"hub.hh")
    points=struct.pack("<hiifffff",-99,3,2,10.,8.,10.,10.,10.)+np.zeros(12,dtype="<i2").tobytes()
    (root/"coherent.pts").write_bytes(points)
    call("coupling.openfast.formats.read_coherent_points",root/"coherent.pts")
    lines=["SYNTHETIC full-field text fixture"]*12
    lines[4]="2 2 10 10 1 100 8"; lines[7]="-5 5"; lines[10]="-5 5"
    (root/"full-field.txt").write_text("\n".join(lines+["0 8 8 9 10 11","1 9 9 10 11 12"])+"\n")
    call("coupling.openfast.formats.read_full_field_text",root/"full-field.txt")

    # Fake turbine output is labelled as such. No simulation is claimed.
    (root/"turbine.out").write_text("SYNTHETIC\nTime Wind Load\n(s) (m/s) (N)\n0 8 100\n1 9 110\n2 10 120\n")
    turbine=call("openfast.read_ascii_output",root/"turbine.out")
    payload=struct.pack("<hii",2,2,3)+struct.pack("<dd",0.,1.)
    payload+=np.ones(2,dtype="<f4").tobytes()+np.zeros(2,dtype="<f4").tobytes()+struct.pack("<i",9)+b"SYNTHETIC"
    for text in ("Time","Wind","Load","(s)","(m/s)","(N)"): payload+=text.ljust(10).encode()
    payload+=np.array([[8,100],[9,110],[10,120]],dtype="<i2").tobytes()
    (root/"turbine.outb").write_bytes(payload)
    call("openfast.read_binary_output",root/"turbine.outb")
    call("openfast.zero_crossing_frequency",np.sin(np.arange(100)*.2),10)
    call("openfast.stress_from_moment",100,2,50)
    call("openfast.rainflow_cycles",[0,1,1,0,-1,-1,0])
    call("openfast.channel_statistics",turbine)
    call("openfast.compare_outputs",turbine,turbine)
    (root/"turbine.fst").write_text('10 TMax - seconds\n"inflow.bts" WindFile - file\n')
    call("openfast_input.read_parameters",root/"turbine.fst")
    call("openfast_input.update_parameters",root/"turbine.fst",{"TMax":20},output=root/"edited.fst")

    # WPS/station configuration support: use ordinary editable text inputs.
    wps=root/"namelist.wps"
    wps.write_text("&share\nmax_dom=2,\nstart_date='2025-01-01_00:00:00',\nend_date='2025-01-01_06:00:00',\n/\n"
        "&geogrid\nparent_id=1,1,\nparent_grid_ratio=1,3,\ni_parent_start=1,5,\nj_parent_start=1,5,\n"
        "e_we=31,10,\ne_sn=31,10,\ndx=1000, dy=1000,\ngeog_data_path='/path/to/GEOG',\n/\n")
    namelist=call("wps.namelist.read_namelist",wps)
    call("wps.namelist.update_namelist_dates",wps,datetime(2025,1,2),datetime(2025,1,2,6),domains=2,output=root/"dated.wps")
    c.domains=call("wps.domains.domain_geometries",namelist)
    call("wps.domains.eta_levels",10)
    call("wps.domains.geographic_corners",c.domains,ref_latitude=52,ref_longitude=5,truelat1=52,truelat2=52,stand_lon=5)
    stations=[Station("demo",52,5,"Synthetic station")]
    tslist=call("timeseries.tslist.write_tslist",stations,root/"tslist")
    call("timeseries.tslist.read_tslist",tslist)
    chars=list(" "*100)
    for start,stop,text in [(0,25,"Synthetic station"),(26,29,"1"),(29,32,"1"),(33,38,"demo"),
        (39,46,"52.0"),(47,55,"5.0"),(58,62,"4"),(63,67,"4"),(70,77,"52.0"),(78,86,"5.0"),(88,94,"10.0"),(95,100,"m")]:
        chars[start:stop]=list(text.rjust(stop-start))
    station=root/"demo.d01.TS"
    with station.open("w") as handle:
        handle.write("".join(chars)+"\n")
        records=np.ones((3,19)); records[:,1]=[0,1,2]; np.savetxt(handle,records)
    np.savetxt(root/"demo.d01.UU",[[0,5,6],[1,6,7],[2,7,8]])
    call("timeseries.station.read_station_header",station)
    call("timeseries.station.read_station_surface",station)
    call("timeseries.station.read_station_profile",root/"demo.d01.UU")
    call("timeseries.station.read_station_family",station)

    # Observation pipeline uses fabricated data ONLY to exercise the wiring.
    (root/"observations.csv").write_text("time,speed\n2025-01-01T00:00:00,8\n2025-01-01T01:00:00,9\n2025-01-01T02:00:00,10\n")
    observations=call("observations.read_csv",root/"observations.csv",time_column="time")
    observations=call("observations.normalize_time",observations)
    observations.to_netcdf(root/"observations.nc")
    with call("observations.read_netcdf",root/"observations.nc",variables=["speed"]): pass
    model=call("observations.from_columns",time=observations.time.values,variables={"speed":[8.5,9.5,10.5]})
    matched=call("observations.align",model,observations,tolerance=np.timedelta64(30,"m"))
    call("reporting.comparison_report",matched[0].speed,matched[1].speed)
    c.observations=observations; c.model=model
