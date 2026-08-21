import numpy as np

from wrf_tools.diagnostics import (
    air_density, bulk_richardson_number, interval_precipitation,
    potential_temperature, power_law_exponent, reflectivity_to_rain_rate,
)


def test_basic_meteorology():
    np.testing.assert_allclose(potential_temperature([0, 2]), [300, 302])
    assert 1.1 < air_density(100000, 290) < 1.3
    np.testing.assert_allclose(interval_precipitation([1, 3, 6]), [0, 2, 3])
    np.testing.assert_allclose(reflectivity_to_rain_rate(10*np.log10(200)), 1.0)
    np.testing.assert_allclose(power_law_exponent(5, 10, 10, 100), np.log(2)/np.log(10))
    assert bulk_richardson_number(300, 301, 10, 100, 5, 10, 0, 0) > 0
