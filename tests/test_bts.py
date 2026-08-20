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
