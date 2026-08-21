from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .coupling.openfast import read_bts
from .io import discover_wrfout, open_wrf, open_wrf_sequence, validate_wrf_dataset


def _discover(args: argparse.Namespace) -> int:
    files = discover_wrfout(args.directory, domain=args.domain, recursive=args.recursive)
    for path in files:
        print(path)
    return 0


def _inspect(args: argparse.Namespace) -> int:
    with open_wrf(args.path) as dataset:
        summary = {
            "path": str(Path(args.path).resolve()),
            "dimensions": dict(dataset.sizes),
            "variables": sorted(dataset.data_vars),
            "attributes": dict(dataset.attrs),
        }
    print(json.dumps(summary, indent=2, default=str))
    return 0


def _bts_info(args: argparse.Namespace) -> int:
    field = read_bts(args.path)
    summary = {
        "path": str(Path(args.path).resolve()),
        "shape": list(field.velocity.shape),
        "dy": field.dy,
        "dz": field.dz,
        "dt": field.dt,
        "hub_height": field.hub_height,
        "bottom_height": field.bottom_height,
        "mean_speed": field.mean_speed,
        "description": field.description,
    }
    print(json.dumps(summary, indent=2))
    return 0

def _validate(args: argparse.Namespace) -> int:
    with open_wrf(args.path) as dataset:
        validate_wrf_dataset(dataset)
    print(f"valid: {Path(args.path).resolve()}")
    return 0

def _concat(args: argparse.Namespace) -> int:
    with open_wrf_sequence(args.paths) as dataset:
        dataset.to_netcdf(args.output)
    print(Path(args.output).resolve())
    return 0

def _bts_compare(args: argparse.Namespace) -> int:
    import numpy as np
    first, second = read_bts(args.first), read_bts(args.second)
    if first.velocity.shape != second.velocity.shape:
        raise ValueError(f"BTS shapes differ: {first.velocity.shape} and {second.velocity.shape}")
    report = {"shape": first.velocity.shape, "maximum_absolute_error": float(np.max(np.abs(first.velocity-second.velocity))), "rmse": float(np.sqrt(np.mean((first.velocity-second.velocity)**2)))}
    print(json.dumps(report, indent=2))
    return 0

def _extract(args: argparse.Namespace) -> int:
    from .extract import point
    with open_wrf(args.path) as dataset:
        result=point(dataset,args.latitude,args.longitude,variables=args.variables,time=args.time)
        result.to_netcdf(args.output)
    print(Path(args.output).resolve()); return 0

def _filter(args: argparse.Namespace) -> int:
    import numpy as np
    from .filters import butterworth_spatial
    values=np.load(args.input); result=butterworth_spatial(values,dx=args.dx,dy=args.dy,cutoff_wavelength=args.cutoff,order=args.order,kind=args.kind)
    np.save(args.output,result); print(Path(args.output).resolve()); return 0

def _spectra(args: argparse.Namespace) -> int:
    import numpy as np
    from .spectra import power_spectrum
    values=np.load(args.input); frequency,power=power_spectrum(values,spacing=args.spacing,axis=args.axis)
    np.savez(args.output,frequency=frequency,power=power); print(Path(args.output).resolve()); return 0

def _report(args: argparse.Namespace) -> int:
    from .reporting import dataset_summary,write_json_report
    with open_wrf(args.path) as dataset: report=dataset_summary(dataset)
    print(write_json_report(report,args.output).resolve()); return 0

def _openfast_info(args: argparse.Namespace) -> int:
    from .openfast import read_ascii_output,read_binary_output
    dataset=read_binary_output(args.path) if Path(args.path).suffix.lower() in {".outb",".bin"} else read_ascii_output(args.path)
    print(json.dumps({"dimensions":dict(dataset.sizes),"channels":sorted(dataset.data_vars),"attributes":dict(dataset.attrs)},indent=2,default=str)); return 0


def _doctor(args: argparse.Namespace) -> int:
    from .doctor import environment_report, print_environment_report
    if args.json:
        print(json.dumps(environment_report(), indent=2))
        return 0
    return 0 if print_environment_report(include_optional=not args.core_only) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wrf-tools", description="General WRF workflow utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover = subparsers.add_parser("discover", help="discover wrfout files")
    discover.add_argument("directory")
    discover.add_argument("--domain")
    discover.add_argument("--recursive", action="store_true")
    discover.set_defaults(handler=_discover)

    inspect = subparsers.add_parser("inspect", help="inspect a WRF NetCDF file")
    inspect.add_argument("path")
    inspect.set_defaults(handler=_inspect)

    validate = subparsers.add_parser("validate", help="validate a WRF NetCDF file")
    validate.add_argument("path")
    validate.set_defaults(handler=_validate)

    concat = subparsers.add_parser("concat", help="concatenate sequential files from one WRF domain")
    concat.add_argument("output")
    concat.add_argument("paths", nargs="+")
    concat.set_defaults(handler=_concat)

    bts = subparsers.add_parser("bts-info", help="inspect a TurbSim/OpenFAST BTS file")
    bts.add_argument("path")
    bts.set_defaults(handler=_bts_info)
    compare = subparsers.add_parser("bts-compare", help="compare two BTS fields")
    compare.add_argument("first"); compare.add_argument("second")
    compare.set_defaults(handler=_bts_compare)

    extract = subparsers.add_parser("extract", help="extract variables at the nearest geographic point")
    extract.add_argument("path"); extract.add_argument("output"); extract.add_argument("latitude",type=float); extract.add_argument("longitude",type=float); extract.add_argument("variables",nargs="+"); extract.add_argument("--time",type=int)
    extract.set_defaults(handler=_extract)

    filtering = subparsers.add_parser("filter", help="Butterworth-filter a NumPy array")
    filtering.add_argument("input"); filtering.add_argument("output"); filtering.add_argument("--dx",type=float,required=True); filtering.add_argument("--dy",type=float); filtering.add_argument("--cutoff",type=float,required=True); filtering.add_argument("--order",type=int,default=2); filtering.add_argument("--kind",choices=("lowpass","highpass"),default="lowpass")
    filtering.set_defaults(handler=_filter)

    spectra = subparsers.add_parser("spectra", help="calculate a periodogram from a NumPy array")
    spectra.add_argument("input"); spectra.add_argument("output"); spectra.add_argument("--spacing",type=float,default=1.0); spectra.add_argument("--axis",type=int,default=-1)
    spectra.set_defaults(handler=_spectra)

    report = subparsers.add_parser("report", help="write a JSON WRF dataset report")
    report.add_argument("path"); report.add_argument("output"); report.set_defaults(handler=_report)

    openfast = subparsers.add_parser("openfast-info", help="inspect OpenFAST ASCII or binary output")
    openfast.add_argument("path"); openfast.set_defaults(handler=_openfast_info)

    doctor = subparsers.add_parser("doctor", help="check Python and optional dependencies")
    doctor.add_argument("--core-only", action="store_true", help="show only required dependencies")
    doctor.add_argument("--json", action="store_true", help="emit a machine-readable report")
    doctor.set_defaults(handler=_doctor)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
