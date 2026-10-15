#!/usr/bin/env python3
"""Export real WRF contours for the separate optional Manim renderer.

    .venv/bin/python examples/export_3d_contours.py /path/to/wrf/run --domain d02

Edit the scientific choices below. These are actual horizontal isolines at
physical heights, not an explanatory cartoon or volumetric isosurfaces.
"""
import argparse
from wrf_tools.contours3d import export_contour_sequence

# USER SETTINGS: no guessed TKE when the required field is absent.
VARIABLE = "wind_speed"       # Or "model_tke" with suitable saved TKE fields.
HEIGHTS_METRES = [100, 500, 1000, 1500]
HEIGHT_REFERENCE = "MSL"      # "AGL" produces an AGL-coordinate stack instead.
CONTOUR_VALUES = [4, 8, 12, 16, 20]  # m/s for wind; m²/s² when plotting TKE.
VERTICAL_EXAGGERATION = 150
MAXIMUM_FRAMES = 7            # Actual output records, not intermediate states.


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory")
    parser.add_argument("--domain", default="d02")
    parser.add_argument("--output", default="example_results/contours3d/contours.json")
    args = parser.parse_args()
    print(export_contour_sequence(args.run_directory, args.output, domain=args.domain,
        variable=VARIABLE, heights=HEIGHTS_METRES, reference=HEIGHT_REFERENCE,
        thresholds=CONTOUR_VALUES, vertical_exaggeration=VERTICAL_EXAGGERATION,
        maximum_frames=MAXIMUM_FRAMES))
