from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .coupling.openfast import read_bts
from .io import discover_wrfout, open_wrf


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

    bts = subparsers.add_parser("bts-info", help="inspect a TurbSim/OpenFAST BTS file")
    bts.add_argument("path")
    bts.set_defaults(handler=_bts_info)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
