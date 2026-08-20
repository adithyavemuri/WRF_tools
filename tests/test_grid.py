import numpy as np
import xarray as xr

from wrf_tools.grid import destagger, interpolate_to_levels, nearest_grid_point


def test_destagger_any_axis():
    values = np.array([[0.0, 2.0, 4.0], [2.0, 4.0, 6.0]])
    np.testing.assert_allclose(destagger(values, 1), [[1.0, 3.0], [3.0, 5.0]])


def test_destagger_renames_wrf_xarray_dimension():
    values = xr.DataArray(
        np.array([[0.0, 2.0, 4.0], [2.0, 4.0, 6.0]]),
        dims=("south_north", "west_east_stag"),
        attrs={"units": "m s-1"},
        name="U",
    )
    result = destagger(values, "west_east_stag")
    assert result.dims == ("south_north", "west_east")
    assert result.attrs["units"] == "m s-1"
    assert result.name == "U"
    np.testing.assert_allclose(result, [[1.0, 3.0], [3.0, 5.0]])


def test_vertical_interpolation():
    height = np.array([[[0.0]], [[100.0]], [[200.0]]])
    field = height * 0.1
    result = interpolate_to_levels(field, height, 50.0, axis=0)
    np.testing.assert_allclose(result, [[5.0]])


def test_nearest_grid_point():
    lat = np.array([[50.0, 50.0], [51.0, 51.0]])
    lon = np.array([[3.0, 4.0], [3.0, 4.0]])
    point = nearest_grid_point(lat, lon, 50.9, 3.9)
    assert (point.y, point.x) == (1, 1)
