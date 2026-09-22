from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import xarray as xr

from wrf_tools.hindcast import summarize_hindcast


def test_hindcast_summary_covers_sequence_and_surface_fields(tmp_path):
    times = np.array(["2025-01-10T00:00:00", "2025-01-10T01:00:00"], dtype="datetime64[s]")
    shape = (2, 2, 2)
    dataset = xr.Dataset(
        {
            "Times": ("Time", np.array([b"2025-01-10_00:00:00", b"2025-01-10_01:00:00"])),
            "XTIME": ("Time", times),
            "T2": (("Time", "south_north", "west_east"), np.full(shape, 280.0)),
            "U10": (("Time", "south_north", "west_east"), np.ones(shape)),
            "V10": (("Time", "south_north", "west_east"), np.zeros(shape)),
            "RAINC": (("Time", "south_north", "west_east"), np.array([np.zeros((2, 2)), np.ones((2, 2))])),
            "RAINNC": (("Time", "south_north", "west_east"), np.zeros(shape)),
        },
        attrs={"GRID_ID": 1, "DX": 9000.0, "DY": 9000.0, "MAP_PROJ": 1},
    )
    cell = SimpleNamespace(x=0, y=1, latitude=52.0, longitude=5.0)
    report = summarize_hindcast(dataset, files=[tmp_path / "a", tmp_path / "b"], cell=cell)
    assert report["file_count"] == 2
    assert report["quality_control"]["status"] == "PASS"
    assert report["precipitation"]["selected_point_accumulation_mm"] == 1.0
    assert report["surface_statistics"]["T2"]["mean"] == 280.0
    assert report["wind_resource"]["height_metres"] == 10
    assert report["wind_resource"]["mean_speed_m_s"] == 1.0
    assert report["wind_resource"]["mean_power_density_w_m2"] > 0


def test_wrf_times_are_authoritative_over_auxiliary_xtime(tmp_path):
    dataset = xr.Dataset(
        {
            "Times": ("Time", np.array([b"2025-01-10_00:00:00", b"2025-01-10_01:00:00", b"2025-01-10_02:00:00"])),
            "XTIME": ("Time", np.array([
                "2025-01-10T00:00:00", "2025-01-10T01:00:18", "2025-01-10T02:00:36"
            ], dtype="datetime64[s]")),
            "T2": (("Time", "south_north", "west_east"), np.full((3, 2, 2), 280.0)),
        },
        attrs={"GRID_ID": 1, "DX": 9000.0, "DY": 9000.0, "MAP_PROJ": 1},
    )
    cell = SimpleNamespace(x=0, y=0, latitude=52.0, longitude=5.0)
    report = summarize_hindcast(dataset, files=[tmp_path / str(i) for i in range(3)], cell=cell)
    assert not [item for item in report["quality_control"]["issues"] if item["check"] == "time-coordinate"]
