"""Analytical checks for WRF figure calculations and output contracts."""
from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest
import xarray as xr

from wrf_tools.visualization import (
    GRAVITY, history_times, interpolate_columns, mass_heights, rotate_wind,
    surface_wind, temperature_celsius, wind_overview_data,
)


@pytest.fixture
def wrf_dataset():
    nt, nz, ny, nx = 3, 3, 4, 5
    y, x = np.meshgrid(np.arange(ny), np.arange(nx), indexing="ij")
    shape = (nt, ny, nx)
    ground = np.broadcast_to(100.0 + x, shape).copy()
    stagger = np.array([0., 100., 300., 600.])
    phb = GRAVITY * (ground[:, None] + stagger[None, :, None, None])
    ph = np.broadcast_to(GRAVITY * np.arange(nt)[:, None, None, None] * 10, phb.shape).copy()
    return xr.Dataset({
        "Times": ("Time", np.array([b"2025-01-01_00:00:00", b"2025-01-01_01:00:00", b"2025-01-01_02:00:00"])),
        "XLAT": (("Time", "south_north", "west_east"), np.broadcast_to(51.5 + y * .1, shape)),
        "XLONG": (("Time", "south_north", "west_east"), np.broadcast_to(4.5 + x * .1, shape)),
        "HGT": (("Time", "south_north", "west_east"), ground),
        "PH": (("Time", "bottom_top_stag", "south_north", "west_east"), ph),
        "PHB": (("Time", "bottom_top_stag", "south_north", "west_east"), phb),
        "U": (("Time", "bottom_top", "south_north", "west_east_stag"), np.broadcast_to(2.0 + np.arange(nx + 1), (nt, nz, ny, nx + 1))),
        "V": (("Time", "bottom_top", "south_north_stag", "west_east"), np.full((nt, nz, ny + 1, nx), 4.0)),
        "U10": (("Time", "south_north", "west_east"), np.broadcast_to(np.arange(nt)[:, None, None] + 3., shape)),
        "V10": (("Time", "south_north", "west_east"), np.zeros(shape)),
        "COSALPHA": (("Time", "south_north", "west_east"), np.zeros(shape)),
        "SINALPHA": (("Time", "south_north", "west_east"), np.ones(shape)),
        "PBLH": (("Time", "south_north", "west_east"), np.full(shape, 250.)),
    }, attrs={"GRID_ID": 1, "DX": 9000., "DY": 9000., "MAP_PROJ": 1,
              "STAND_LON": 5., "CEN_LAT": 52., "TRUELAT1": 52., "TRUELAT2": 52.})


def test_analytical_rotation_preserves_speed_and_orientation():
    east, north = rotate_wind([3., 0.], [4., 5.], 0., 1.)
    np.testing.assert_allclose(east, [-4., -5.])
    np.testing.assert_allclose(north, [3., 0.])
    np.testing.assert_allclose(np.hypot(east, north), [5., 5.])
    with pytest.raises(ValueError, match="unit rotation"):
        rotate_wind(1, 0, 2, 0)


def test_mass_height_and_time_dependent_ground_broadcast():
    ph = np.zeros((2, 3))
    phb = GRAVITY * np.array([[100, 200, 400], [150, 250, 450]])
    np.testing.assert_allclose(mass_heights(ph, phb, [100, 150], axis=1, agl=True), [[50, 200], [50, 200]])
    np.testing.assert_allclose(mass_heights(ph[0], phb[0]), [150, 300])


def test_wrf_constants_and_temperature_against_known_dry_states():
    assert GRAVITY == 9.81
    np.testing.assert_allclose(temperature_celsius([0, 10], [100000, 100000]), [26.85, 36.85])
    assert temperature_celsius(0, 50000) == pytest.approx(300 * 0.5 ** (2 / 7) - 273.15)
    with pytest.raises(ValueError, match="pressure"):
        temperature_celsius(0, 0)


def test_vertical_interpolation_uses_each_times_physical_height():
    height = np.array([[0., 100., 200.], [50., 150., 250.]])
    field = 2 * height + 1
    result = interpolate_columns(field, height, [0, 100, 200, 300])
    np.testing.assert_allclose(result[:, 1:3], [[201, 401], [201, 401]])
    assert np.isnan(result[1, 0]) and np.isnan(result[:, -1]).all()
    with pytest.raises(ValueError, match="increasing"):
        interpolate_columns(field, height[:, ::-1], [100])
    field[0, 1] = np.nan
    assert np.isnan(interpolate_columns(field, height, [50])[0, 0])


def test_rotation_absence_is_labelled_and_summary_uses_earth_coordinates(wrf_dataset, tmp_path):
    from wrf_tools.hindcast import summarize_hindcast
    u, v, reference = surface_wind(wrf_dataset, 0)
    np.testing.assert_allclose(u, 0)
    np.testing.assert_allclose(v, 3)
    assert reference == "earth-relative"
    cell = SimpleNamespace(x=1, y=1, latitude=51.6, longitude=4.6)
    report = summarize_hindcast(wrf_dataset, files=[tmp_path / "wrfout"], cell=cell)
    assert report["wind_resource"]["mean_direction_degrees"] == pytest.approx(180)
    assert surface_wind(wrf_dataset.drop_vars(["COSALPHA", "SINALPHA"]), 0)[2].startswith("grid-relative")
    assert surface_wind(wrf_dataset.set_coords(["COSALPHA", "SINALPHA"]), 0)[2] == "earth-relative"


def test_history_times_handles_character_arrays_and_decoded_datetime():
    times = ["2025-01-01_00:00:00", "2025-01-01_01:00:00"]
    expected = [value.replace("_", "T") for value in times]
    for dtype in ("S1", "U1"):
        dataset = xr.Dataset({"Times": (("Time", "DateStrLen"), np.array([list(value) for value in times], dtype=dtype))})
        assert history_times(dataset) == expected
    assert history_times(xr.Dataset({"XTIME": ("Time", np.array(expected, dtype="datetime64[s]"))})) == expected


def test_overview_destaggers_and_records_section_height(wrf_dataset):
    pytest.importorskip("pyproj")
    cell = SimpleNamespace(x=1, y=1, latitude=51.6, longitude=4.6)
    data = wind_overview_data(wrf_dataset.set_coords(["XLAT", "XLONG"]), cell, top=500)
    # U on x=1 and x=2 stagger points is 3 and 4; V is 4 everywhere.
    np.testing.assert_allclose(data["speed"], np.hypot(3.5, 4))
    np.testing.assert_allclose(data["heights"][0], [50, 200, 450])
    np.testing.assert_allclose(data["heights"][2], [70, 220, 470])
    np.testing.assert_allclose(data["pbl"], 350 + np.arange(5))
    assert np.isnan(data["regular"][:, 0]).all()  # no extrapolation below the first level
    bad = wrf_dataset.copy(deep=True)
    bad["Times"][1] = bad["Times"][0]
    with pytest.raises(ValueError, match="increasing"):
        history_times(bad)


def test_overview_exports_methods_and_vector_formats(wrf_dataset, tmp_path, monkeypatch):
    mpl = pytest.importorskip("matplotlib")
    pytest.importorskip("cartopy")
    mpl.use("Agg")
    from wrf_tools.visualization import save_wind_overview
    monkeypatch.setattr("wrf_tools.maps.add_cached_features", lambda axis: False)
    cell = SimpleNamespace(x=1, y=1, latitude=51.6, longitude=4.6)
    products, metadata = save_wind_overview(wrf_dataset, cell, tmp_path / "d01_overview",
        sources=["/private/location/wrfout_d01_example"], top=500)
    assert set(products) == {"png", "pdf", "svg", "metadata"}
    assert all(path.stat().st_size > 0 for path in products.values())
    saved = json.loads(products["metadata"].read_text())
    assert saved["source_files"] == ["wrfout_d01_example"]
    assert saved["section"]["height_reference"] == "MSL"
    assert saved["site_height_reference"] == "AGL"
    assert metadata["gravity_m_s2"] == GRAVITY
    assert saved["references"]["wrf"]["url"].startswith("https://doi.org/")


def test_animation_actual_times_shared_scale_and_manifest(wrf_dataset, tmp_path, monkeypatch):
    pytest.importorskip("cartopy")
    pytest.importorskip("netCDF4")
    from PIL import Image
    from wrf_tools.animations import create_wind_animation, read_animation_manifest
    monkeypatch.setattr("wrf_tools.maps.add_cached_features", lambda axis: False)
    wrf_dataset.to_netcdf(tmp_path / "wrfout_d01_2025-01-01_00_00_00")
    products = create_wind_animation(tmp_path, tmp_path / "movie", fps=1)
    data, frames = read_animation_manifest(products["manifest"])
    assert len(frames) == 3
    assert data["timestamps_utc"] == history_times(wrf_dataset)
    assert data["colour_limits_m_s"] == [0, 6]
    with Image.open(products["movie"]) as movie:
        assert movie.n_frames == 3
    data["frames"][0] = "../outside.png"
    products["manifest"].write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Frame paths"):
        read_animation_manifest(products["manifest"])


def test_unsupported_animation_history_is_rejected(wrf_dataset, tmp_path, monkeypatch):
    pytest.importorskip("cartopy")
    pytest.importorskip("netCDF4")
    from wrf_tools.animations import create_wind_animation
    monkeypatch.setattr("wrf_tools.maps.add_cached_features", lambda axis: False)
    moved = wrf_dataset.copy(deep=True)
    moved["XLAT"][1] = moved["XLAT"][1] + 0.1
    moved.to_netcdf(tmp_path / "wrfout_d01_2025-01-01_00_00_00")
    with pytest.raises(ValueError, match="Moving-grid"):
        create_wind_animation(tmp_path, tmp_path / "movie")
