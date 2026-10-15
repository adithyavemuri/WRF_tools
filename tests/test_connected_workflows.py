"""Connectivity tests: numerical checks are not atmospheric validation."""
import ast
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import xarray as xr

from wrf_tools.capabilities import capability_catalog, get_capability, write_capability_guide
from wrf_tools.recipes import run_recipe
from wrf_tools.diagnostic_groups import run_diagnostic_groups

ROOT=Path(__file__).resolve().parents[1]


def test_every_public_function_is_discoverable_and_resolvable(tmp_path):
    root=ROOT/"src/wrf_tools"
    expected=set()
    for file in root.rglob("*.py"):
        module=".".join(file.relative_to(root).with_suffix("").parts)
        if file.name=="__init__.py" or module in {"cli","recipes","capabilities"}:
            continue
        expected.update(f"{module}.{node.name}" for node in ast.parse(file.read_text()).body
                        if isinstance(node,ast.FunctionDef) and not node.name.startswith("_"))
    catalog=capability_catalog()
    assert set(catalog)==expected
    for identity in expected:
        assert callable(get_capability(identity))
    assert "diagnostics.advanced.q_criterion" in catalog
    assert "diagnostics.advanced.tke_budget" in catalog
    assert "timeseries.station.read_station_surface" in catalog
    assert "wps.namelist.read_namelist" in catalog
    guide=write_capability_guide(tmp_path/"API.md").read_text()
    assert all(identity in guide for identity in expected)
    with pytest.raises(ValueError,match="Unknown capability"):
        get_capability("os.system")


@pytest.mark.parametrize("name",["coupling-demo","observations-demo"])
def test_editable_synthetic_recipes(name,tmp_path):
    manifest=run_recipe(ROOT/f"examples/recipes/{name}.toml",tmp_path)
    report=json.loads(manifest.read_text())
    assert report["status"]=="COMPLETE"
    assert all(item["status"]=="COMPLETE" for item in report["steps"])
    if name=="coupling-demo":
        assert json.loads((tmp_path/"round-trip-error.json").read_text())<.001
    else:
        assert json.loads((tmp_path/"comparison.json").read_text())["bias"]==.5
    with pytest.raises(FileExistsError):
        run_recipe(ROOT/f"examples/recipes/{name}.toml",tmp_path)


def test_recipe_wrong_reference_is_not_silently_skipped(tmp_path):
    path=tmp_path/"bad.toml"
    path.write_text('[[steps]]\nid="a"\ncall="validation.rmse"\nargs=[{ref="typo"},[1]]\n')
    with pytest.raises(ValueError,match="unknown or forward"):
        run_recipe(path,tmp_path/"out")
    assert not (tmp_path/"out").exists()


def test_external_file_recipe_lists_missing_inputs_without_claiming_success(tmp_path):
    report=json.loads(run_recipe(ROOT/"examples/recipes/external-files.toml",tmp_path).read_text())
    assert report["status"]=="COMPLETE_WITH_SKIPS"
    assert all(item["status"]=="SKIPPED" for item in report["steps"])


def test_recipe_dependency_skip_and_failure_manifest(tmp_path):
    path=tmp_path/"skip.toml"
    path.write_text('[[steps]]\nid="data"\ncall="io.datasets.open_wrf"\nargs=[{file="missing.nc"}]\noptional=true\n'
                    '[[steps]]\nid="next"\ncall="reporting.dataset_summary"\nargs=[{ref="data"}]\n')
    record=json.loads(run_recipe(path,tmp_path/"out").read_text())
    assert record["status"]=="COMPLETE_WITH_SKIPS"
    assert [item["status"] for item in record["steps"]]==["SKIPPED","SKIPPED"]
    path.write_text('[[steps]]\nid="bad"\ncall="validation.rmse"\nargs=[[1,2],[1,2,3]]\n')
    with pytest.raises(ValueError):
        run_recipe(path,tmp_path/"bad")
    record=json.loads((tmp_path/"bad/analysis-manifest.json").read_text())
    assert record["status"]=="FAILED" and record["steps"][0]["status"]=="FAILED"


def test_recipe_output_cannot_escape_folder(tmp_path):
    path=tmp_path/"escape.toml"
    path.write_text('[[steps]]\nid="a"\ncall="validation.rmse"\nargs=[[1],[2]]\nsave="../escaped.json"\n')
    with pytest.raises(ValueError,match="inside"):
        run_recipe(path,tmp_path/"out")
    assert not (tmp_path/"escaped.json").exists()


def test_all_report_groups_have_visible_status_when_inputs_missing(tmp_path):
    status=run_diagnostic_groups(xr.Dataset(),SimpleNamespace(x=0,y=0),tmp_path)
    assert len(status)==6
    assert all(item["status"]=="UNAVAILABLE" for item in status.values())
    assert "Missing WRF variables" in status["flow_structure"]["reason"]
    skipped=run_diagnostic_groups(xr.Dataset(),None,tmp_path,groups="none")
    assert all(item["status"]=="NOT_SELECTED" for item in skipped.values())
    with pytest.raises(ValueError,match="Unknown groups"):
        run_diagnostic_groups(xr.Dataset(),None,tmp_path,groups="typo")


def _synthetic():
    spec=importlib.util.spec_from_file_location("connected_fixture",ROOT/"examples/average_wrf_fields.py")
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    ds=module.synthetic_dataset()
    shape=(4,4,4,5)
    dims=("Time","bottom_top","south_north","west_east")
    ds["T"]=(dims,np.broadcast_to(np.arange(4)[None,:,None,None]*.5,shape))
    ds["W"]=(("Time","bottom_top_stag","south_north","west_east"),np.broadcast_to(np.sin(np.arange(4))[:,None,None,None],(4,5,4,5)))
    surface=("Time","south_north","west_east")
    for name,value in {"T2":280,"U10":5,"V10":1,"PBLH":500,"PSFC":100000,"Q2":.005,"HFX":40,"UST":.3,"COSALPHA":1,"SINALPHA":0}.items():
        ds[name]=(surface,np.full((4,4,5),value,dtype=float))
    for name,value in {"P":0,"PB":95000,"QVAPOR":.005}.items():
        ds[name]=(dims,np.full(shape,value,dtype=float))
    return ds


def test_stull_partial_budget_is_connected_and_requires_sampling_choice(tmp_path):
    ds=_synthetic(); cell=SimpleNamespace(x=1,y=1)
    denied=run_diagnostic_groups(ds,cell,tmp_path,groups="turbulence")
    assert denied["turbulence"]["status"]=="UNAVAILABLE"
    # Explicit synthetic averaging policy ONLY to exercise the path, not LES validation.
    accepted=run_diagnostic_groups(ds,cell,tmp_path,groups="turbulence",options={
        "turbulence_average":"time","minimum_turbulence_samples":4,"max_turbulence_interval_seconds":3600})
    record=accepted["turbulence"]
    assert record["status"]=="COMPLETE"
    assert "diagnostics.advanced.tke_budget" in record["functions"]
    with np.load(tmp_path/record["data"]) as data:
        assert np.isfinite(data["budget_shear_production"]).all()
        assert np.isfinite(data["budget_buoyancy_production"]).all()


def test_q_and_stability_groups_make_actual_artifacts(tmp_path,monkeypatch):
    pytest.importorskip("cartopy")
    monkeypatch.setattr("wrf_tools.maps.add_cached_features",lambda ax:False)
    result=run_diagnostic_groups(_synthetic(),SimpleNamespace(x=1,y=1),tmp_path,
        groups="thermodynamics,flow_structure",options={"flow_heights_metres":[100,200,300]})
    for name in ("thermodynamics","flow_structure"):
        assert result[name]["status"]=="COMPLETE"
        assert (tmp_path/result[name]["figure"]).is_file()
        assert (tmp_path/result[name]["data"]).is_file()


def test_spectral_group_saves_real_coarsening_error(tmp_path):
    from wrf_tools.diagnostic_groups import _spectral
    ds=_synthetic().isel(Time=[0,1,2,3,0,1,2])
    ds["Times"]=("Time",np.array([f"2025-01-01_0{i}:00:00".encode() for i in range(7)]))
    rng=np.random.default_rng(42)
    ds["T2"]=ds.T2.copy(data=280+rng.normal(size=ds.T2.shape))
    ds["U10"]=ds.U10.copy(data=rng.normal(size=ds.U10.shape))
    ds["V10"]=ds.V10.copy(data=rng.normal(size=ds.V10.shape))
    fig,arrays,*_=_spectral(ds,SimpleNamespace(x=1,y=1),{})
    import matplotlib.pyplot as plt
    plt.close(fig)
    assert arrays["resolution_rmse"]>0
    assert abs(arrays["conservation_relative_error"])<1e-6
    assert np.isfinite(arrays["coherence"]).any()
