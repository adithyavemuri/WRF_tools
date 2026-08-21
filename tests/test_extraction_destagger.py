import numpy as np
import xarray as xr

from wrf_tools.extract import horizontal_plane, point, vertical_profile
from wrf_tools.cli import build_parser
from wrf_tools.io import get_variable


def sample_dataset():
    return xr.Dataset(
        {
            "U": (("Time", "bottom_top", "south_north", "west_east_stag"),
                  np.arange(1 * 2 * 2 * 4, dtype=float).reshape(1, 2, 2, 4)),
            "XLAT": (("Time", "south_north", "west_east"),
                     np.array([[[50.0, 50.0, 50.0], [51.0, 51.0, 51.0]]])),
            "XLONG": (("Time", "south_north", "west_east"),
                      np.array([[[3.0, 4.0, 5.0], [3.0, 4.0, 5.0]]])),
        }
    )


def test_get_variable_destagger_is_explicit_and_recorded():
    dataset = sample_dataset()
    native = get_variable(dataset, "U")
    mass = get_variable(dataset, "U", destagger_native=True)
    assert native.sizes["west_east_stag"] == 4
    assert native.attrs["wrf_tools_grid_processing"] == "native WRF grid preserved"
    assert mass.sizes["west_east"] == 3
    np.testing.assert_allclose(mass.isel(Time=0, bottom_top=0, south_north=0), [0.5, 1.5, 2.5])
    assert mass.attrs["wrf_tools_destaggered_dimensions"] == "west_east_stag"


def test_extractors_destagger_before_spatial_selection():
    dataset = sample_dataset()
    site = point(dataset, 50.0, 4.0, variables=["U"], destagger_native=True)
    np.testing.assert_allclose(site["U"].isel(Time=0), [1.5, 9.5])
    profile = vertical_profile(dataset, "U", x=1, y=0, destagger_native=True)
    np.testing.assert_allclose(profile, [1.5, 9.5])
    plane = horizontal_plane(dataset, "U", level=0, time=0, destagger_native=True)
    assert plane.dims == ("south_north", "west_east")


def test_extract_cli_exposes_destagger_choice():
    args = build_parser().parse_args([
        "extract", "wrfout", "site.nc", "50", "4", "U", "--destagger",
    ])
    assert args.destagger is True
