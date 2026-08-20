import numpy as np

from wrf_tools.coupling.openfast import wind_field_from_components


def test_arbitrary_axis_mapping():
    shape = (3, 4, 2)  # vertical, lateral, time
    u = np.ones(shape)
    v = np.ones(shape) * 2
    w = np.ones(shape) * 3
    field = wind_field_from_components(
        u,
        v,
        w,
        time_axis=2,
        vertical_axis=0,
        lateral_axis=1,
        dy=5,
        dz=6,
        dt=0.1,
        hub_height=12,
        bottom_height=0,
        component_order=("v", "u", "w"),
    )
    assert field.velocity.shape == (2, 3, 4, 3)
    np.testing.assert_allclose(field.velocity[0, 0, 0], [2, 1, 3])
