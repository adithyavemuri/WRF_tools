import numpy as np
from wrf_tools.diagnostics import circular_mean, friction_velocity, monin_obukhov_length
from wrf_tools.validation import cluster_profiles, comparison_summary, correlation, spatial_scores, standard_error
from wrf_tools.wind_models import cheynet_spectrum, kaimal_spectrum, synthetic_wind_field
from wrf_tools.observations import from_columns, normalize_time

def test_extended_statistics_and_stability():
    assert circular_mean([350, 10]) == 360 or np.isclose(circular_mean([350, 10]), 0)
    np.testing.assert_allclose(friction_velocity(1.2, 1.2), 1)
    assert monin_obukhov_length(300, 0.5, 0.1) < 0
    assert correlation([1,2,3], [2,4,6]) == 1
    assert standard_error([1,2,3]) > 0
    assert comparison_summary([1,2], [1,2])["rmse"] == 0
    labels,centers=cluster_profiles([[0,0],[.1,.1],[10,10],[10.1,10.1]],2,seed=1)
    assert len(np.unique(labels))==2 and centers.shape==(2,2)
    assert spatial_scores([1,2],[1,1])["absolute_error"].tolist()==[0,1]
    assert np.isfinite(kaimal_spectrum([0,.1],mean_speed=10,height=100,friction_velocity=.5)).all()

def test_synthetic_field_is_reproducible():
    first = synthetic_wind_field(np.linspace(5, 6, 4), nt=4, ny=3, nz=2, dt=1, dy=10, dz=10, seed=4)
    second = synthetic_wind_field(np.linspace(5, 6, 4), nt=4, ny=3, nz=2, dt=1, dy=10, dz=10, seed=4)
    assert first.shape == (4,2,3,3)
    np.testing.assert_allclose(first, second)
    obs=from_columns(time=np.array(["2020-01-01T01:00"],dtype="datetime64[m]"),variables={"u":[1]})
    assert str(normalize_time(obs,timezone_offset_hours=1).time.values[0]).startswith("2020-01-01T00:00")


def test_cheynet_spectrum_matches_author_supplied_equations():
    frequency = np.array([0.1, 0.2])
    reduced = frequency * 81.5 / 10.0

    # Neutral u component: Cheynet et al. Eq. 26, 81.5 m coefficients.
    expected_neutral = (
        189*reduced/(1+111*reduced)**(5/3)
        + 9.6*reduced/(1+40*reduced**(5/3))
    ) * 0.5**2 / frequency
    np.testing.assert_allclose(
        cheynet_spectrum(frequency, mean_speed=10, height=81.5,
                         friction_velocity=0.5, stability=0.0, component="u"),
        expected_neutral,
    )

    # Stable u component: Eq. 28 for 1 <= zeta < 2.
    expected_stable = (
        0.03*reduced**(-2/3)
        + 5*reduced/(1+4.4*reduced**(5/3))
        + 1.5e-5*reduced**-2
    ) * 0.5**2 / frequency
    np.testing.assert_allclose(
        cheynet_spectrum(frequency, mean_speed=10, height=81.5,
                         friction_velocity=0.5, stability=1.5, component="u"),
        expected_stable,
    )

    for zeta in (-2, -1, -0.5, -0.3, -0.1, 0.1, 0.3, 0.5, 1.0, 1.999):
        for component in "uvw":
            result = cheynet_spectrum(
                frequency, mean_speed=10, height=81.5,
                friction_velocity=0.5, stability=zeta, component=component,
            )
            assert result.shape == frequency.shape
            assert np.all(np.isfinite(result)) and np.all(result >= 0)
