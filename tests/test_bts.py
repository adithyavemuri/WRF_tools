import numpy as np

from wrf_tools.coupling.openfast import WindField, read_bts, validate_bts, write_bts


def test_bts_round_trip(tmp_path):
    rng = np.random.default_rng(42)
    velocity = rng.normal(10.0, 2.0, size=(12, 4, 5, 3))
    expected = WindField(
        velocity=velocity,
        dy=8.0,
        dz=10.0,
        dt=0.2,
        hub_height=30.0,
        bottom_height=0.0,
        description="round trip",
    )
    path = write_bts(tmp_path / "wind.bts", expected)
    actual = validate_bts(path, expected)
    assert actual.velocity.shape == velocity.shape
    assert read_bts(path).description == "round trip"


def test_bts_round_trip_preserves_constant_components(tmp_path):
    velocity = np.zeros((4, 3, 2, 3))
    velocity[..., 0] = np.linspace(7.0, 8.0, 4)[:, None, None]
    velocity[..., 1] = 0.2
    velocity[..., 2] = -0.05
    expected = WindField(
        velocity=velocity, dy=10.0, dz=10.0, dt=0.1,
        hub_height=100.0, bottom_height=10.0,
    )
    actual = validate_bts(write_bts(tmp_path / "constant.bts", expected), expected)
    np.testing.assert_allclose(actual.velocity[..., 1:], velocity[..., 1:], atol=1e-7)
