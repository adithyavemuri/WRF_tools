import numpy as np

from wrf_tools.diagnostics import resolved_tke, wind_direction, wind_speed


def test_wind_speed_and_direction():
    np.testing.assert_allclose(wind_speed([3], [4]), [5])
    np.testing.assert_allclose(wind_direction([0], [-1]), [0])


def test_resolved_tke():
    u = np.array([0.0, 2.0])
    zeros = np.zeros(2)
    assert resolved_tke(u, zeros, zeros) == 0.5
