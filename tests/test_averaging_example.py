"""Exercise the editable example against analytically known synthetic fields."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest
import xarray as xr


@pytest.fixture
def example():
    path = Path(__file__).resolve().parents[1] / "examples" / "average_wrf_fields.py"
    spec = importlib.util.spec_from_file_location("averaging_example", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_four_means_and_saved_data_preserve_all_timestamps(example, tmp_path):
    result, selected = example.calculate_means(example.synthetic_dataset())
    assert result.horizontal_mean.sizes == {"Time": 4, "height": 9}
    np.testing.assert_allclose(result.horizontal_mean.sel(height=100), 3.5 + np.arange(4))
    np.testing.assert_allclose(result.selected_area_mean.sel(height=100), 3.5 + np.arange(4))
    # Layer representatives: z=100 m for 100 m overlap; z=225 m for 50 m overlap.
    expected_layer = (3.5 * 100 + 4.125 * 50) / 150
    np.testing.assert_allclose(result.selected_area_timeseries, expected_layer + np.arange(4))
    np.testing.assert_allclose(result.vertical_mean.isel(Time=0), expected_layer)
    np.testing.assert_allclose(result.time_mean_map, expected_layer + 1.5)
    assert result.time_mean_profile.sel(height=100).item() == pytest.approx(5.)
    pytest.importorskip("netCDF4")
    result.to_netcdf(tmp_path / "means.nc")
    with xr.open_dataset(tmp_path / "means.nc") as saved:
        assert saved.sizes["Time"] == 4
        assert saved.height.attrs["reference"] == "AGL"
        assert saved.attrs["time_weighting"].startswith("equal saved")


def test_model_level_and_uniform_weighting_are_user_choices(example, monkeypatch):
    monkeypatch.setattr(example, "PROFILE_COORDINATE", "model")
    monkeypatch.setattr(example, "HORIZONTAL_WEIGHTING", "uniform")
    monkeypatch.setattr(example, "VERTICAL_WEIGHTING", "uniform")
    result, _ = example.calculate_means(example.synthetic_dataset().drop_vars("MAPFAC_M"))
    assert "bottom_top" in result.horizontal_mean.dims and "height" not in result.dims
    np.testing.assert_allclose(result.vertical_mean.isel(Time=0), (3.5 + 4.125) / 2)


def test_selected_region_and_period_really_change_reductions(example, monkeypatch):
    monkeypatch.setattr(example, "REGION", dict(south=50., north=54., west=3.9, east=4.1))
    monkeypatch.setattr(example, "START_UTC", "2025-01-01T01:00:00")
    monkeypatch.setattr(example, "END_UTC", "2025-01-01T02:00:00")
    dataset = example.synthetic_dataset().copy(deep=True)
    # An x gradient ensures the selected western column differs from the domain.
    dataset["U"] = dataset.U + xr.DataArray(np.arange(6), dims="west_east_stag")
    result, _ = example.calculate_means(dataset)
    assert result.sizes["Time"] == 2
    assert bool((result.selected_area_mean < result.horizontal_mean).where(result.horizontal_mean.notnull(), True).all())
    monkeypatch.setattr(example, "REGION", dict(south=-1., north=1., west=-1., east=1.))
    with pytest.raises(ValueError, match="no grid-cell"):
        example.calculate_means(dataset)


def test_auxiliary_wrf_coordinates_do_not_conflict_in_saved_results(example):
    dataset = example.synthetic_dataset()
    auxiliary = np.array(["2025-01-01T00:00:00", "2025-01-01T01:00:18",
                          "2025-01-01T02:00:36", "2025-01-01T03:00:54"], dtype="datetime64[s]")
    dataset = dataset.assign_coords(XTIME=("Time", auxiliary)).set_coords(["XLAT", "XLONG"])
    result, _ = example.calculate_means(dataset)
    assert "XTIME" not in result
    assert "latitude" in result and "longitude" in result
    assert result.Time.values[1] == np.datetime64("2025-01-01T01:00:00")


def test_msl_reference_is_not_silently_treated_as_agl(example, monkeypatch):
    monkeypatch.setattr(example, "HEIGHT_REFERENCE", "MSL")
    result, _ = example.calculate_means(example.synthetic_dataset())
    assert result.height.attrs["reference"] == "MSL"
    # Mean terrain is 22 m; at 100 m MSL, mean AGL is 78 m.
    np.testing.assert_allclose(result.horizontal_mean.sel(height=100), 3.39 + np.arange(4))
