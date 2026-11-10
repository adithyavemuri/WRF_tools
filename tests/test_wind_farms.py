"""Reporting regressions, not wake/physics validation."""
import json

import numpy as np
import pytest
import xarray as xr

from wrf_tools.wind_farms import (
    _file_hash as file_hash, _load_turbine_layout as load_turbine_layout,
    _overlay_turbines as overlay_turbines, _wind_farm_evidence as wind_farm_evidence,
    _load_farm_diagnostics as load_farm_diagnostics,
)


def test_layout_validates_coordinates_and_keeps_filename_only(tmp_path):
    source=tmp_path/"turbines.csv"
    source.write_text("farm,latitude,longitude\nA,52,4\nA,52.1,4.1\n")
    layout=load_turbine_layout(source)
    assert layout["turbine_count"] == 2 and layout["farms"] == ["A"]
    assert layout["source"] == "turbines.csv"
    assert layout["sha256"] == file_hash(source)
    for value in ("nan", "91"):
        source.write_text(f"latitude,longitude\n{value},4\n")
        with pytest.raises(ValueError,match="coordinates"):
            load_turbine_layout(source)


def test_overlay_is_small_map_only_and_does_not_change_extent():
    ccrs=pytest.importorskip("cartopy.crs")
    import matplotlib.pyplot as plt
    fig=plt.figure()
    ax=fig.add_subplot(121,projection=ccrs.PlateCarree())
    profile=fig.add_subplot(122)
    ax.set_extent([3,6,51,54],crs=ccrs.PlateCarree())
    ax.plot([3,4],[51,52],label="Domain")
    ax.legend(loc="upper right")
    before=ax.get_xlim(),ax.get_ylim()
    overlay_turbines(fig,dict(longitude=[4,120],latitude=[52,60]),label="Turbines | WFP off")
    assert (ax.get_xlim(),ax.get_ylim()) == before
    assert len(profile.collections) == 0
    assert ax.collections[-1].get_sizes().tolist() == [2]
    assert [text.get_text() for text in ax.get_legend().texts] == ["Domain","Turbines | WFP off"]
    plt.close(fig)


def test_power_is_cell_sum_not_area_or_turbine_weighted():
    ds=xr.Dataset({"POWER":(("Time","south_north","west_east"),
        [[[0.,0.]],[[1e6,2e6]]],{"units":"W"})},attrs={"DX":3000.,"DY":3000.})
    result=wind_farm_evidence(ds,flag=1)
    assert result["activation"] == "Fitch active"
    assert result["fleet_power_mw"] == [0.,3.]
    assert result["powered_cells"] == [0,2]
    assert "context only" in wind_farm_evidence(ds,flag=0)["activation"]
    assert wind_farm_evidence(ds)["activation"] == "Activation not established"
    ds.attrs["WINDFARM_OPT"]=0
    assert wind_farm_evidence(ds,flag=1)["windfarm_opt"] == 0
    ds.POWER.attrs["units"]="MW"
    with pytest.raises(ValueError,match="in W"):
        wind_farm_evidence(ds)


@pytest.mark.parametrize("field,value",[("domain","d01"),("times_utc",[]),("input_sha256",{}),
    ("layout_sha256","wrong"),("configuration_sha256","wrong")])
def test_companion_rejects_mixed_runs(tmp_path,field,value):
    history=tmp_path/"wrfout_d02_test"; history.write_bytes(b"run A")
    record=dict(domain="d02",times_utc=["2025-01-10T00:00:00"],
        input_sha256={history.name:file_hash(history)},layout_sha256="layout",configuration_sha256="config")
    path=tmp_path/"farm-diagnostics.json"
    path.write_text(json.dumps(record))
    options=dict(files=[history],times=record["times_utc"],domain="d02",layout={"sha256":"layout"},configuration_hash="config")
    assert load_farm_diagnostics(path,**options) == record
    record[field]=value
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError,match="match"):
        load_farm_diagnostics(path,**options)


def test_cli_autoloads_layout_relative_to_configuration(tmp_path,monkeypatch):
    from wrf_tools.cli import build_parser
    config=tmp_path/"case.toml"
    config.write_text('[wind_farms]\nenabled=true\nlayout_csv="input/turbines.csv"\n')
    observed={}
    def report(*args,**kwargs):
        observed.update(kwargs)
        return {}
    monkeypatch.setattr("wrf_tools.hindcast.create_hindcast_report",report)
    args=build_parser().parse_args(["hindcast-report","run","report","--configuration",str(config)])
    args.handler(args)
    assert observed["turbine_layout"] == tmp_path/"input/turbines.csv"
    assert "wind_farms" not in observed["configuration"]["case_configuration"]["data"]


def test_beginner_example_exposes_optional_inputs_without_changing_defaults(tmp_path,monkeypatch):
    import importlib.util
    from pathlib import Path
    source=Path(__file__).parents[1]/"examples/create_hindcast_report.py"
    spec=importlib.util.spec_from_file_location("beginner_report",source)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    monkeypatch.setattr("sys.argv",[str(source),str(tmp_path)])
    args=module.parse_arguments()
    assert args.turbine_layout is None and args.farm_diagnostics is None
    monkeypatch.setattr("sys.argv",[str(source),str(tmp_path),"--turbine-layout","turbines.csv",
                                  "--farm-diagnostics","farm-diagnostics.json"])
    args=module.parse_arguments()
    assert args.turbine_layout == Path("turbines.csv")
    assert args.farm_diagnostics == Path("farm-diagnostics.json")


def test_full_report_contains_farm_section_and_companion_images(tmp_path,monkeypatch):
    pytest.importorskip("cartopy"); pytest.importorskip("reportlab"); pytest.importorskip("netCDF4")
    from wrf_tools.hindcast import create_hindcast_report
    import matplotlib.pyplot as plt
    # Minimal surface-only output: no farm physics is fabricated by this fixture.
    times=["2025-01-10_00:00:00","2025-01-10_01:00:00"]
    dims=("Time","south_north","west_east")
    ds=xr.Dataset({
        "Times":("Time",np.array(times,dtype="S19")),
        "XLAT":(dims,np.broadcast_to([[52.,52.],[52.1,52.1]],(2,2,2))),
        "XLONG":(dims,np.broadcast_to([[4.,4.1],[4.,4.1]],(2,2,2))),
        "T2":(dims,np.full((2,2,2),280.)),
        "HGT":(dims,np.zeros((2,2,2))),
        "POWER":(dims,np.full((2,2,2),1e6),{"units":"W"}),
    },attrs={"GRID_ID":2,"DX":3000.,"DY":3000.,"MAP_PROJ":1})
    history=tmp_path/"wrfout_d02_2025-01-10_00:00:00"; ds.to_netcdf(history)
    layout=tmp_path/"turbines.csv"; layout.write_text("farm,latitude,longitude\nA,52.05,4.05\n")
    companion=tmp_path/"farm-diagnostics.json"
    record=dict(domain="d02",times_utc=[stamp.replace("_","T") for stamp in times],inputs=[history.name],input_sha256={history.name:file_hash(history)},
        layout_sha256=file_hash(layout),scope="Analytic test, not wake validation.",
        farms={"A":dict(turbines=1,unique_cells=1)})
    companion.write_text(json.dumps(record))
    for name in ("offshore-map.png","farm-timeseries.png","farm-profiles.png"):
        fig,ax=plt.subplots(); ax.plot([0,1],[0,1]); fig.savefig(tmp_path/name); plt.close(fig)
    monkeypatch.setattr("wrf_tools.hindcast.add_cached_features",lambda ax:False)
    paths=create_hindcast_report(tmp_path,tmp_path/"report",domain="d02",diagnostic_groups="none",
        configuration={"case_manifest":{"data":{"effective_namelist":{"physics":{"windfarm_opt":[0,1]}}}}},
        turbine_layout=layout,farm_diagnostics=companion)
    summary=json.loads(paths["summary"].read_text())
    assert summary["domains"]["d02"]["wind_farms"]["fleet_power_mw"] == [4.,4.]
    assert summary["wind_farms"]["farm_averages"]["domain"] == "d02"
    assert "/private/" not in paths["html"].read_text()
    for name in ("offshore-map.png","farm-timeseries.png","farm-profiles.png"):
        assert (paths["html"].parent/("windfarm_"+name)).is_file()
        assert "windfarm_"+name in paths["html"].read_text()
    assert paths["pdf"].stat().st_size > 5000
