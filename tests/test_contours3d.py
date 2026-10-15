"""Contour coordinates and fixed-level contracts, independent of Manim."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from wrf_tools.contours3d import horizontal_contours, export_contour_sequence


def test_contour_geometry_has_known_crossing_and_physical_height():
    pytest.importorskip("contourpy")
    x, y = np.arange(4.), np.arange(3.)
    field = np.broadcast_to(x, (3,4))[None]
    paths = horizontal_contours(field, x, y, [500.], [1.5])
    assert len(paths) == 1
    points = np.array(paths[0]["points_km"])
    np.testing.assert_allclose(points[:,0], 1.5)
    np.testing.assert_allclose(points[:,2], .5)
    with pytest.raises(ValueError, match="one"):
        horizontal_contours(field, x, y, [500.,1000.], [1.5])


def test_export_uses_actual_times_fixed_thresholds_and_no_tke_fallback(tmp_path):
    pytest.importorskip("contourpy"); pytest.importorskip("netCDF4"); pytest.importorskip("matplotlib")
    path = Path(__file__).resolve().parents[1]/"examples"/"average_wrf_fields.py"
    spec = importlib.util.spec_from_file_location("contour_fixture", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    ds = module.synthetic_dataset().copy(deep=True)
    # Add horizontal variation so isolines, rather than constant planes, exist.
    ds.U.values = ds.U.values + np.arange(6)[None,None,None,:]
    ds.to_netcdf(tmp_path/"wrfout_d01_2025-01-01_00_00_00")
    output = export_contour_sequence(tmp_path, tmp_path/"contours.json", domain="d01",
        heights=[100,200], thresholds=[5,6,7], maximum_frames=2)
    data = json.loads(output.read_text())
    assert len(data["frames"]) == 2 and data["frames"][1]["time_utc"] == "2025-01-01T01:00:00"
    assert data["height_reference"] == "MSL" and data["temporal_interpolation"] == "none"
    assert all(item["height_m"] in (100,200) for f in data["frames"] for item in f["contours"])
    with pytest.raises(LookupError, match="No supported"):
        export_contour_sequence(tmp_path, tmp_path/"tke.json", domain="d01", variable="model_tke")
    ds["QKE"] = ds.U.isel(west_east_stag=slice(0,5)).rename(west_east_stag="west_east")*2
    ds.QKE.attrs = {"units":"m2 s-2"}
    ds.to_netcdf(tmp_path/"wrfout_d01_2025-01-01_00_00_00")
    energy_path = export_contour_sequence(tmp_path, tmp_path/"tke.json", domain="d01",
        variable="model_tke", heights=[100,200], thresholds=[5,6,7], maximum_frames=2)
    energy = json.loads(energy_path.read_text())
    assert energy["source"]["source_variable"] == "QKE"
    assert energy["source"]["conversion_factor"] == .5
