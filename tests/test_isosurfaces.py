"""Independent physical-coordinate checks; no Manim/native graphics required."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("skimage")

from wrf_tools.isosurfaces import isosurface_mesh, export_isosurface_sequence


def test_affine_scalar_on_sloping_nonuniform_height_grid():
    k,j,i = np.indices((4,5,6), dtype=float)
    # Nonuniform vertical spacing and bilinear terrain-following geometry.
    z = 100 + 200*k + 15*k*i + 10*i + 20*j
    scalar = i + 2*j + 3*k
    mesh = isosurface_mesh(scalar, z, 2*np.arange(6), 3*np.arange(5), 7.5)
    points = np.asarray(mesh["vertices_km"])
    assert len(points) and len(mesh["faces"])
    ii,jj = points[:,0]/2, points[:,1]/3
    kk = (points[:,2]*1000 - 100 - 10*ii - 20*jj)/(200+15*ii)
    np.testing.assert_allclose(ii+2*jj+3*kk, 7.5, atol=2e-6)
    faces = np.asarray(mesh["faces"])
    assert faces.min() >= 0 and faces.max() < len(points)


def test_sphere_geometry_matches_known_implicit_field():
    x = np.linspace(-2,2,25)
    k,j,i = np.meshgrid(x,x,x,indexing="ij")
    mesh = isosurface_mesh(i*i+j*j+k*k, (k+3)*1000, x, x, 1.)
    points = np.asarray(mesh["vertices_km"])
    radius_squared = points[:,0]**2+points[:,1]**2+(points[:,2]-3)**2
    # Linear interpolation of squared coordinates has an O(dx^2) error.
    np.testing.assert_allclose(radius_squared, 1., atol=(4/24)**2/4+1e-6)


def test_top_clips_crossing_triangles_without_capping_or_extrapolation():
    k,j,i = np.indices((4,4,4),dtype=float)
    mesh = isosurface_mesh(i+j+k, 100+200*k+30*i, np.arange(4), np.arange(4), 3.5, top_metres=425)
    points = np.asarray(mesh["vertices_km"])
    assert len(points)
    assert np.max(points[:,2]) <= .425+1e-12
    assert np.any(np.isclose(points[:,2], .425))
    ii,jj = points[:,0],points[:,1]
    kk = (points[:,2]*1000-100-30*ii)/200
    np.testing.assert_allclose(ii+jj+kk, 3.5, atol=2e-6)


def test_clip_through_native_vertex_does_not_leave_zero_area_faces():
    k,j,i = np.indices((4,4,4),dtype=float)
    mesh = isosurface_mesh(i+j+k, 100+200*k, np.arange(4), np.arange(4), 3., top_metres=300)
    triangles = np.asarray(mesh["vertices_km"])[np.asarray(mesh["faces"])]
    areas = np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0], triangles[:,2]-triangles[:,0]), axis=1)
    assert len(areas) and (areas > 0).all()


@pytest.mark.parametrize("level", [-10,0,3,10])
def test_absent_or_extreme_threshold_is_empty_not_fabricated(level):
    k,j,i = np.indices((2,2,2),dtype=float)
    mesh = isosurface_mesh(i+j+k, 100+100*k, [0,1],[0,1], level)
    assert mesh["vertices_km"] == [] and mesh["faces"] == []


@pytest.mark.parametrize("problem", ["missing_value","missing_height","folded_height","folded_x","shape","level"])
def test_invalid_volume_is_rejected(problem):
    k,j,i = np.indices((3,3,3),dtype=float)
    values, heights, x, level = i+j+k, 100+100*k, [0,1,2], 2.5
    if problem == "missing_value": values[0,0,0] = np.nan
    if problem == "missing_height": heights[0,0,0] = np.nan
    if problem == "folded_height": heights[1,0,0] = 0
    if problem == "folded_x": x = [0,2,1]
    if problem == "shape": heights = heights[:2]
    if problem == "level": level = np.inf
    with pytest.raises(ValueError):
        isosurface_mesh(values, heights, x, [0,1,2], level)


def _fixture():
    path = Path(__file__).resolve().parents[1]/"examples/showcase/data.py"
    spec = importlib.util.spec_from_file_location("isosurface_fixture", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    ds = module.synthetic_wrf().isel(Time=slice(0,2)).copy(deep=True)
    ds["LANDMASK"] = (ds.HGT.dims, np.broadcast_to(np.arange(8)[None,None,:]>=3, ds.HGT.shape).astype(float))
    return ds


def test_export_records_actual_time_terrain_ocean_and_no_overwrite(tmp_path):
    pytest.importorskip("netCDF4"); pytest.importorskip("matplotlib")
    ds = _fixture()
    ds.HGT.values[:,:,4:] = -2   # Below-sea-level land must not be raised.
    ds.to_netcdf(tmp_path/"wrfout_d01_2025-01-01_00_00_00")
    path = export_isosurface_sequence(tmp_path, tmp_path/"geometry.json",domain="d01",
        thresholds=[7,8],top_metres=500,horizontal_stride=3,maximum_frames=2)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert [row["time_utc"] for row in data["frames"]] == ["2025-01-01T00:00:00","2025-01-01T00:00:10"]
    assert data["thresholds"] == [7,8] and data["temporal_interpolation"] == "none"
    terrain = np.asarray(data["terrain"]["vertices_km"])
    assert set(terrain[:,2]) == {-.002,0.,.01}
    assert terrain[:,0].max() == 7 and terrain[:,1].max() == 7  # Last endpoint retained.
    assert data["terrain"]["coastlines_km"]
    assert all(len(mesh["faces"]) for frame in data["frames"] for mesh in frame["meshes"])
    with pytest.raises(FileExistsError):
        export_isosurface_sequence(tmp_path,path,domain="d01")


def test_missing_landmask_or_tke_is_not_invented_and_face_limit_is_visible(tmp_path):
    pytest.importorskip("netCDF4"); pytest.importorskip("matplotlib")
    ds = _fixture()
    file = tmp_path/"wrfout_d01_2025-01-01_00_00_00"
    ds.drop_vars("LANDMASK").to_netcdf(file)
    with pytest.raises(ValueError,match="LANDMASK"):
        export_isosurface_sequence(tmp_path,tmp_path/"missing.json",domain="d01")
    ds.drop_vars("QKE").to_netcdf(file)
    with pytest.raises(LookupError,match="No supported"):
        export_isosurface_sequence(tmp_path,tmp_path/"missing.json",domain="d01",variable="model_tke")
    with pytest.raises(ValueError,match="maximum_faces"):
        export_isosurface_sequence(tmp_path,tmp_path/"large.json",domain="d01",thresholds=[7,8],horizontal_stride=1,maximum_faces=1)
    assert not (tmp_path/"large.json").exists()


def test_tke_export_records_qke_half_and_rejects_a_moving_grid(tmp_path):
    pytest.importorskip("netCDF4"); pytest.importorskip("matplotlib")
    ds = _fixture()
    k,j,i = np.indices((4,8,8),dtype=float)
    ds.QKE.values[:] = 2*(2+k+.1*j+.2*i)
    # Extraneous NetCDF attributes must not leak non-JSON values into metadata.
    ds.QKE.attrs["unused_array"] = np.array([1.,2.])
    file = tmp_path/"wrfout_d01_2025-01-01_00_00_00"
    ds.to_netcdf(file)
    path = export_isosurface_sequence(tmp_path,tmp_path/"tke.json",domain="d01",variable="model_tke",
        thresholds=[3,4],top_metres=500,horizontal_stride=1)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["source"]["source_variable"] == "QKE"
    assert data["source"]["conversion_factor"] == .5
    assert data["source"]["units"] == "m2 s-2"
    assert all(frame["face_count"] for frame in data["frames"])
    ds.XLAT.values[1] += .01
    ds.to_netcdf(file)
    with pytest.raises(ValueError,match="Moving"):
        export_isosurface_sequence(tmp_path,tmp_path/"moving.json",domain="d01")


def test_full_column_export_records_model_top_separately_from_display(tmp_path):
    pytest.importorskip("netCDF4"); pytest.importorskip("matplotlib")
    ds = _fixture()
    ds.to_netcdf(tmp_path/"wrfout_d01_2025-01-01_00_00_00")
    path = export_isosurface_sequence(tmp_path,tmp_path/"full.json",domain="d01",
        thresholds=[7,8],top_metres=None,horizontal_stride=1)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["requested_top_metres"] is None
    assert data["top_metres"] == pytest.approx(610.)
    assert data["model_top"]["interface_msl_m"] == pytest.approx([810.,810.])
    assert data["model_top"]["highest_mass_msl_m"] == pytest.approx([610.,610.])
    assert data["model_top"]["pressure_pa"] is None
    clipped = export_isosurface_sequence(tmp_path,tmp_path/"clipped.json",domain="d01",
        thresholds=[7,8],top_metres=300,horizontal_stride=1)
    cut = json.loads(clipped.read_text(encoding="utf-8"))
    assert cut["requested_top_metres"] == 300
    assert cut["model_top"] == data["model_top"]


@pytest.mark.parametrize("options", [{"horizontal_stride":0},{"maximum_frames":0},{"top_metres":np.nan},
    {"thresholds":[8,7]},{"variable":"pressure"},{"maximum_faces":0}])
def test_export_invalid_options_fail_before_io(tmp_path,options):
    with pytest.raises(ValueError):
        export_isosurface_sequence(tmp_path,tmp_path/"bad.json",**options)
