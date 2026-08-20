"""Minimal generalized WRF-LES plane to BTS example."""

import numpy as np

from wrf_tools.coupling.openfast import validate_bts, wind_field_from_components, write_bts

# Replace these arrays with data extracted from WRF or WRF-GAD plane output.
u = np.load("u.npy")  # any 3-D order is allowed when axes are specified below
v = np.load("v.npy")
w = np.load("w.npy")

field = wind_field_from_components(
    u,
    v,
    w,
    time_axis=0,
    vertical_axis=1,
    lateral_axis=2,
    dy=10.0,
    dz=10.0,
    dt=0.1,
    hub_height=120.0,
    bottom_height=10.0,
)
write_bts("inflow.bts", field)
validate_bts("inflow.bts", field)
