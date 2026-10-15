"""Analytical model TKE tests; not meteorological validation."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import xarray as xr

from wrf_tools.turbulence import model_tke, model_tke_sources, tke_diagnostics_data, save_tke_diagnostics


@pytest.fixture
def dataset():
    path = Path(__file__).resolve().parents[1]/"examples"/"average_wrf_fields.py"
    spec = importlib.util.spec_from_file_location("tke_example_fixture", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    ds = module.synthetic_dataset()
    shape = (ds.sizes["Time"], ds.sizes["bottom_top"], ds.sizes["south_north"], ds.sizes["west_east"])
    ds["QKE"] = xr.DataArray(np.full(shape, 4.), dims=("Time", "bottom_top", "south_north", "west_east"), attrs={"units":"m2 s-2"})
    return ds


def test_qke_conversion_is_not_double_counted(dataset):
    dataset["TKE_PBL"] = dataset.QKE * 3
    assert model_tke_sources(dataset) == ["QKE", "TKE_PBL"]
    energy = model_tke(dataset)
    np.testing.assert_allclose(energy, 2)
    assert energy.attrs["source_variable"] == "QKE"
    np.testing.assert_allclose(model_tke(dataset, source="tke_pbl"), 12)
    assert "Not resolved" in energy.attrs["warning"]


def test_staggered_tke_is_selected_then_collocated(dataset):
    ds = dataset.drop_vars("QKE")
    faces = np.arange(5)*2.
    ds["TKE_PBL"] = xr.DataArray(np.broadcast_to(faces[None,:,None,None], (4,5,4,5)),
        dims=("Time", "bottom_top_stag", "south_north", "west_east"), attrs={"units":"m2 s-2"})
    energy = model_tke(ds, indexers={"Time":0, "south_north":1, "west_east":1})
    np.testing.assert_allclose(energy, [1,3,5,7])
    assert energy.dims == ("bottom_top",)
    assert "interface" in energy.attrs["vertical_processing"]


def test_negative_tke_is_preserved_and_reported(dataset):
    dataset.QKE.values[0,2,0,0] = -6
    data = tke_diagnostics_data(dataset, SimpleNamespace(x=1,y=1))
    assert data["negative_count"] == 1 and data["minimum"] == -3
    np.testing.assert_allclose(data["maxima"], 2)


def test_missing_or_invalid_model_tke_is_not_invented(dataset):
    with pytest.raises(LookupError, match="No supported"):
        model_tke(dataset.drop_vars("QKE"))
    with pytest.raises(ValueError, match="source"):
        model_tke(dataset, source="not_energy")
    dataset.QKE.attrs["units"] = "m/s"
    with pytest.raises(ValueError, match="units"):
        model_tke(dataset)


def test_tke_figure_exports_provenance_and_source(dataset, tmp_path, monkeypatch):
    pytest.importorskip("cartopy")
    import matplotlib
    matplotlib.use("Agg")
    monkeypatch.setattr("wrf_tools.maps.add_cached_features", lambda ax: False)
    cell = SimpleNamespace(x=1,y=1)
    image, summary = save_tke_diagnostics(dataset, cell, tmp_path/"tke", top=600,
                                         sources=["/private/wrfout_d01_example"])
    assert image.is_file() and image.with_suffix(".pdf").is_file()
    saved = json.loads(image.with_suffix(".json").read_text())
    assert saved["source_variable"] == "QKE" and saved["conversion_factor"] == .5
    assert saved["source_files"] == ["wrfout_d01_example"]
    assert len(saved["domain_maximum_by_native_level"]) == 4


def test_report_includes_tke_without_needing_wind_temperature_profiles(dataset, tmp_path, monkeypatch):
    pytest.importorskip("cartopy"); pytest.importorskip("reportlab"); pytest.importorskip("netCDF4")
    from wrf_tools.hindcast import create_hindcast_report
    monkeypatch.setattr("wrf_tools.maps.add_cached_features", lambda ax: False)
    monkeypatch.setattr("wrf_tools.hindcast.add_cached_features", lambda ax: False)
    dataset.to_netcdf(tmp_path/"wrfout_d01_2025-01-01_00_00_00")
    paths = create_hindcast_report(tmp_path, tmp_path/"report")
    summary = json.loads(paths["summary"].read_text())
    assert summary["domains"]["d01"]["turbulence"]["status"] == "available"
    assert paths["pdf"].stat().st_size > 0
