import numpy as np
from wrf_tools.diagnostics import circular_mean, friction_velocity, monin_obukhov_length
from wrf_tools.validation import cluster_profiles, comparison_summary, correlation, spatial_scores, standard_error
from wrf_tools.wind_models import kaimal_spectrum, synthetic_wind_field
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
