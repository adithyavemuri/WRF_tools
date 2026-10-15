#!/usr/bin/env python3
"""Create an offline browser view: rotate, zoom and inspect real WRF times.

Run from the repository root after installing the interactive/geometry extras:
    python -m pip install -e ".[isosurface,interactive]"
    python examples/interactive_isosurfaces.py /path/to/wrf/run --domain d02

Then double-click viewer.html. No web server, Manim or internet is required
when viewing. This writes a separate output and does not alter the MP4.
The default now includes a diagnostic dropdown and a movable vertical section.
Use --single-variable for the original wind-speed-only export.
"""
import argparse
from pathlib import Path

from wrf_tools.isosurfaces import export_isosurface_sequence
from wrf_tools.interactive import write_isosurface_html

# USER SETTINGS: full means all saved mass levels, not a guessed altitude.
THRESHOLDS = [12.,16.]       # m/s; fixed across the entire time sequence.
TOP = None                  # None = full column; e.g. 4000 = 4 km MSL cutout.
STRIDE = 5                  # Explicit display subsampling; 1 retains full grid.
VERTICAL_EXAGGERATION = 5.  # Viewer also offers 1x true-scale and other scales.
OPACITY = .35               # Viewer controls can change this or hide surfaces.
MAXIMUM_FRAMES = 7          # Actual saved output times, not interpolated states.

# Every field has its OWN units and thresholds. These are editable example
# choices, NOT universal vortex/turbulence thresholds. All stay fixed in time.
# A missing field (e.g. TKE with YSU) is disabled with a reason in the viewer.
DIAGNOSTICS = {
    "wind_speed": [12.,16.],          # m/s, horizontal speed
    "vertical_velocity": [-.5,.5],   # m/s, down/up; NOT turbulent flux
    "vertical_vorticity": [-1e-4,1e-4],  # 1/s, relative to the Earth
    "q_criterion": [1e-8,5e-8],      # 1/s^2, rotation/strain diagnostic
    "model_tke": [.5,1.],            # m^2/s^2, only if written by the model
}
MAXIMUM_FACES = 150000      # Total across all selected fields per timestamp.


def _top(value):
    if value.lower() == "full":
        return None
    try:
        result = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use 'full' or a positive height in metres MSL") from exc
    if result <= 0:
        raise argparse.ArgumentTypeError("Height must be positive")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_directory",nargs="?",help="Directory containing your wrfout files")
    parser.add_argument("--geometry",type=Path,help="Reuse an existing export instead of reading WRF")
    parser.add_argument("--domain",default="d02")
    parser.add_argument("--output",type=Path,default=Path("example_results/diagnostic-explorer"))
    parser.add_argument("--thresholds",type=float,nargs="+",default=THRESHOLDS)
    parser.add_argument("--single-variable",action="store_true",help="Original wind-only viewer; --thresholds applies here")
    parser.add_argument("--diagnostics",nargs="+",choices=list(DIAGNOSTICS),default=list(DIAGNOSTICS),
        help="Select which diagnostic fields to export; edit DIAGNOSTICS above to change their thresholds")
    parser.add_argument("--maximum-faces",type=int,default=MAXIMUM_FACES)
    parser.add_argument("--top",type=_top,default=TOP,help="full (default), or metres MSL")
    parser.add_argument("--stride",type=int,default=STRIDE)
    parser.add_argument("--vertical-exaggeration",type=float,default=VERTICAL_EXAGGERATION)
    parser.add_argument("--opacity",type=float,default=OPACITY)
    parser.add_argument("--maximum-frames",type=int,default=MAXIMUM_FRAMES)
    args = parser.parse_args(argv)
    if bool(args.run_directory) == bool(args.geometry):
        parser.error("Supply a run directory OR --geometry, not both")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Choose a new/empty output directory; no files are silently replaced")
    geometry = args.geometry
    if geometry is None:
        if args.thresholds != THRESHOLDS and not args.single_variable:
            parser.error("--thresholds is for --single-variable; edit DIAGNOSTICS for per-field thresholds")
        selection = None if args.single_variable else {name:DIAGNOSTICS[name] for name in args.diagnostics}
        geometry = export_isosurface_sequence(args.run_directory,args.output/"geometry.json",domain=args.domain,
            thresholds=args.thresholds if args.single_variable else THRESHOLDS,
            diagnostics=selection,top_metres=args.top,horizontal_stride=args.stride,
            vertical_exaggeration=args.vertical_exaggeration,maximum_frames=args.maximum_frames,
            maximum_faces=args.maximum_faces)
    result = write_isosurface_html(geometry,args.output/"viewer.html",
        vertical_exaggeration=args.vertical_exaggeration,surface_opacity=args.opacity)
    print(f"Open in your browser: {result}")
    return result


if __name__ == "__main__":
    main()
