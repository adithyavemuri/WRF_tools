"""Analytical comparisons test mechanics without claiming a sensitivity study."""
import numpy as np
import pytest
import xarray as xr

from wrf_tools.averaging import layer_thickness, mean, to_height, wrf_cell_area
from wrf_tools.comparison import align_cases, plot_profiles, plot_timeseries


def series(values=(1., 2., 3.), start="2025-01-01T00"):
    stamps = np.datetime64(start) + np.arange(len(values)) * np.timedelta64(1, "h")
    return xr.DataArray(np.asarray(values), dims="Time", coords={"Time": stamps}, attrs={"units": "m s-1"})


def profile(values=(2., 3., 4.), reference="AGL"):
    data = xr.DataArray(np.asarray(values), dims="height", coords={"height": [50., 100., 200.]}, attrs={"units": "m s-1"})
    data.height.attrs = {"units": "m", "reference": reference}
    return data


def test_alignment_is_explicit_and_does_not_interpolate():
    a, b = series(), series(start="2025-01-01T01")
    with pytest.raises(ValueError, match="Samples differ"):
        align_cases({"A": a, "B": b}, coordinate="Time")
    aligned = align_cases({"A": a, "B": b}, coordinate="Time", alignment="intersection")
    np.testing.assert_allclose(aligned["A"], [2., 3.])
    np.testing.assert_allclose(aligned["B"], [1., 2.])
    with pytest.raises(ValueError, match="No common"):
        align_cases({"A": a, "B": series(start="2026-01-01T00")}, coordinate="Time", alignment="intersection")


def test_bad_units_duplicate_times_and_coordinate_references_are_rejected():
    a, b = series(), series()
    b.attrs["units"] = "knots"
    with pytest.raises(ValueError, match="units"):
        align_cases({"A": a, "B": b}, coordinate="Time")
    b = a.assign_coords(Time=[a.Time.values[0]] * 3)
    with pytest.raises(ValueError, match="unique"):
        align_cases({"A": a, "B": b}, coordinate="Time")
    with pytest.raises(ValueError, match="references differ"):
        align_cases({"A": profile(), "B": profile(reference="MSL")}, coordinate="height")


def test_time_and_profile_difference_plots_have_known_values(tmp_path):
    mpl = pytest.importorskip("matplotlib")
    mpl.use("Agg")
    import matplotlib.pyplot as plt
    # No fixed case limit; exercise more cases than the standard style cycle.
    cases = {f"case{i}": series(np.array([1., 2., 3.]) + i) for i in range(6)}
    fig, ax = plot_timeseries(cases, baseline="case0", value_label="Wind speed")
    for offset, line in enumerate(ax.lines[:5], 1):
        np.testing.assert_allclose(line.get_ydata(), offset)
    fig.savefig(tmp_path / "timeseries.svg")
    plt.close(fig)
    fig, ax = plot_profiles({"control": profile(), "test": profile((3., 4., 5.))}, baseline="control")
    np.testing.assert_allclose(ax.lines[0].get_xdata(), 1.)
    assert "AGL" in ax.get_ylabel()
    plt.close(fig)
    with pytest.raises(ValueError, match="baseline"):
        plot_timeseries(cases, baseline="missing")


def test_weighted_means_exclude_missing_cells_and_apply_mask():
    data = xr.DataArray([[1., 3.], [np.nan, 9.]], dims=("y", "x"), attrs={"units": "K"})
    area = xr.DataArray([[1., 3.], [10., 2.]], dims=data.dims)
    assert mean(data, ["y", "x"], weighting="uniform").item() == pytest.approx(13 / 3)
    assert mean(data, ["y", "x"], weighting="area", weights=area).item() == pytest.approx(28 / 6)
    mask = xr.DataArray([[True, True], [False, False]], dims=data.dims)
    result = mean(data, ["y", "x"], weighting="area", weights=area, mask=mask)
    assert result.item() == 2.5
    assert result.attrs["units"] == "K"
    assert np.isnan(mean(data, ["y", "x"], weighting="uniform", mask=mask & False))


def test_layer_mean_and_invalid_weights():
    data = xr.DataArray([1., 5.], dims="bottom_top")
    thickness = xr.DataArray([10., 30.], dims="bottom_top")
    assert mean(data, "bottom_top", weighting="layer", weights=thickness).item() == 4.
    with pytest.raises(ValueError, match="explicit weights"):
        mean(data, "bottom_top", weighting="layer")
    with pytest.raises(ValueError, match="nonnegative"):
        mean(data, "bottom_top", weighting="layer", weights=-thickness)
    with pytest.raises(ValueError, match="subset"):
        mean(data, "bottom_top", weighting="layer", weights=thickness.rename(bottom_top="other"))
    with pytest.raises(ValueError):
        mean(data.assign_coords(bottom_top=[0, 1]), "bottom_top", weighting="layer",
             weights=thickness.assign_coords(bottom_top=[1, 2]))


def test_native_level_mean_differs_from_mean_at_common_physical_height():
    z = xr.DataArray([[10., 110.], [30., 130.]], dims=("x", "bottom_top"))
    field = 2 * z
    field.attrs["units"] = "m s-1"
    native = mean(field, "x", weighting="uniform")
    np.testing.assert_allclose(native, [40., 240.])
    physical = to_height(field, z, [20., 50., 100., 140.], reference="AGL")
    averaged = mean(physical, "x", weighting="uniform")
    np.testing.assert_allclose(averaged[:3], [40., 100., 200.])
    assert np.isnan(averaged[-1])
    assert averaged.height.attrs["reference"] == "AGL"
    assert np.isnan(physical.sel(x=1, height=20.))
    with pytest.raises(ValueError, match="increasing"):
        to_height(field, z.isel(bottom_top=slice(None, None, -1)), [50.], reference="AGL")


def test_cell_area_uses_map_factors_without_fallback():
    ds = xr.Dataset({"MAPFAC_M": (("y", "x"), [[1., 2.]])}, attrs={"DX": 100., "DY": 200., "MAP_PROJ": 1})
    np.testing.assert_allclose(wrf_cell_area(ds), [[20000., 5000.]])
    with pytest.raises(ValueError, match="supply cell areas"):
        wrf_cell_area(ds.drop_vars("MAPFAC_M"))


def test_layer_thickness_clips_partial_boundary_layers():
    interfaces = xr.DataArray([[0., 100., 300., 600.], [50., 150., 350., 650.]],
                              dims=("x", "bottom_top_stag"))
    weights = layer_thickness(interfaces, 75., 250.)
    assert weights.dims == ("x", "bottom_top")
    np.testing.assert_allclose(weights, [[25., 150., 0.], [75., 100., 0.]])
    # Second column: 75-150 overlaps the FIRST layer, then 150-250 the second.
    np.testing.assert_allclose(weights[1], [75., 100., 0.])
    with pytest.raises(ValueError, match="bounds"):
        layer_thickness(interfaces, 250., 75.)
    with pytest.raises(ValueError, match="increasing"):
        layer_thickness(interfaces.isel(bottom_top_stag=slice(None, None, -1)), 75., 250.)
