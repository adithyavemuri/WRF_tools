#!/usr/bin/env python3
"""Make a simple movie from actual WRF history outputs.

Run from the WRF_tools repository after its normal local installation:

    .venv/bin/python examples/animate_wrf_wind.py /path/to/wrf/run --domain d02

The default GIF needs no external FFmpeg executable. Numbered PNG frames and a
JSON methods manifest are saved beside it for inspection and reuse.
No new simulation is run. Start with --maximum-frames 7 to check your settings.
"""
from pathlib import Path
import argparse

from wrf_tools.animations import create_wind_animation


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--output", type=Path, default=Path("example_results/wind_animation"))
    parser.add_argument("--domain", default="d01")
    parser.add_argument("--fps", type=float, default=1)
    parser.add_argument("--maximum-frames", type=int, default=7)
    parser.add_argument("--stride", type=int, default=1)
    args = parser.parse_args()
    print("STEP 1: Read actual output times and determine one shared wind scale")
    print("STEP 2: Render geographic frames and save the animation")
    products = create_wind_animation(args.run_directory, args.output,
        domain=args.domain, fps=args.fps, stride=args.stride, maximum_frames=args.maximum_frames)
    print("STEP 3: Open the movie; keep the JSON file with it as processing evidence")
    for name, path in products.items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
