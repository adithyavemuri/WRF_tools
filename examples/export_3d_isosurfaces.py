#!/usr/bin/env python3
"""Export real wind/TKE isosurfaces, terrain and ocean for Manim.

From the repository root, with its Python environment active:
    python examples/export_3d_isosurfaces.py /path/to/wrf/run --domain d02

This prepares geometry, not a movie. Then use manim_wrf_isosurfaces.py in your
optional Manim environment. See docs/ISOSURFACES.md for the complete commands.
"""
import argparse

from wrf_tools.isosurfaces import export_isosurface_sequence

# EDIT THESE: thresholds are fixed throughout the movie, not inferred per frame.
VARIABLE = "wind_speed"           # Or "model_tke" if your WRF run saved it.
ISOSURFACE_VALUES = [12., 16.]      # m/s for wind, m2/s2 for TKE.
TOP_METRES_MSL = 4000.
HORIZONTAL_STRIDE = 5              # 1 = full grid; 5 = every fifth point + edge.
VERTICAL_EXAGGERATION = 25.         # Applied to terrain AND the atmosphere.
MAXIMUM_FRAMES = 7                 # Actual timestamps only; None = all.


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory")
    parser.add_argument("--domain", default="d02")
    parser.add_argument("--output", default="example_results/isosurfaces3d/geometry.json")
    parser.add_argument("--thresholds", type=float, nargs="+", default=ISOSURFACE_VALUES)
    parser.add_argument("--top", type=float, default=TOP_METRES_MSL)
    parser.add_argument("--stride", type=int, default=HORIZONTAL_STRIDE)
    parser.add_argument("--maximum-frames", type=int, default=MAXIMUM_FRAMES)
    args = parser.parse_args()
    print(export_isosurface_sequence(args.run_directory, args.output,
        domain=args.domain, variable=VARIABLE, thresholds=args.thresholds,
        top_metres=args.top, horizontal_stride=args.stride,
        vertical_exaggeration=VERTICAL_EXAGGERATION, maximum_frames=args.maximum_frames))
