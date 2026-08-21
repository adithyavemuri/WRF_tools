"""Convert an extracted WRF-LES velocity plane to TurbSim/OpenFAST BTS.

Input arrays must each describe the same plane. By default their layout is
``(time, vertical, lateral)``. They should already be destaggered onto a common
grid and rotated so U is normal to the inflow plane, V is lateral, and W is
vertical. Axis numbers and component signs are explicit command-line options.

References
----------
Jonkman (2009), *TurbSim User's Guide*, NREL/TP-500-46198.
OpenFAST Toolbox ``TurbSimFile`` reference implementation:
https://github.com/OpenFAST/openfast_toolbox/blob/main/openfast_toolbox/io/turbsim_file.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from wrf_tools.coupling.openfast import validate_bts, wind_field_from_components, write_bts


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--u", type=Path, required=True, help="longitudinal-component .npy file")
    parser.add_argument("--v", type=Path, required=True, help="lateral-component .npy file")
    parser.add_argument("--w", type=Path, required=True, help="vertical-component .npy file")
    parser.add_argument("--output", type=Path, required=True, help="output TurbSim .bts file")
    parser.add_argument("--dt", type=float, required=True, help="time step [s]")
    parser.add_argument("--dy", type=float, required=True, help="lateral spacing [m]")
    parser.add_argument("--dz", type=float, required=True, help="vertical spacing [m]")
    parser.add_argument("--hub-height", type=float, required=True, help="hub height [m]")
    parser.add_argument("--bottom-height", type=float, required=True, help="lowest grid height [m]")
    parser.add_argument("--time-axis", type=int, default=0)
    parser.add_argument("--vertical-axis", type=int, default=1)
    parser.add_argument("--lateral-axis", type=int, default=2)
    parser.add_argument("--signs", type=float, nargs=3, default=(1.0, 1.0, 1.0),
                        metavar=("U", "V", "W"), help="OpenFAST component sign multipliers")
    return parser.parse_args()


def main() -> None:
    args = arguments()
    field = wind_field_from_components(
        np.load(args.u), np.load(args.v), np.load(args.w),
        time_axis=args.time_axis,
        vertical_axis=args.vertical_axis,
        lateral_axis=args.lateral_axis,
        dy=args.dy, dz=args.dz, dt=args.dt,
        hub_height=args.hub_height,
        bottom_height=args.bottom_height,
        component_signs=args.signs,
    )
    output = write_bts(args.output, field)
    decoded = validate_bts(output, expected=field)
    maximum_error = float(np.max(np.abs(decoded.velocity - field.velocity)))
    print(f"Wrote {output} with shape {field.velocity.shape}")
    print(f"Round-trip validation passed; maximum velocity error = {maximum_error:.6g} m/s")


if __name__ == "__main__":
    main()
