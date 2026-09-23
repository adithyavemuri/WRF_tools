#!/usr/bin/env python3
"""Create a compact scientific report from an existing WRF run.

This example does not run WRF. Point it at a directory containing one or more
time-ordered WRF output sequences named wrfout_d??_*. Every discovered domain
is analysed; --domain selects the primary domain named in the report.

Run from the WRF_tools repository root:

    .venv/bin/python examples/create_hindcast_report.py \
        /path/to/wrf/run \
        --output reports/example \
        --domain d02 \
        --latitude 52.0 \
        --longitude 5.0

Latitude and longitude are optional. If omitted, the centre of each domain is
used. The output directory receives JSON, HTML, PDF and PNG figures.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from wrf_tools.hindcast import create_hindcast_report


# =============================================================================
# EDITABLE DEFAULTS
# =============================================================================
# These values make it convenient to rerun the example from an IDE. Command-line
# arguments override them. Leave RUN_DIRECTORY as None when using the CLI.
RUN_DIRECTORY: Path | None = None
OUTPUT_DIRECTORY = Path("example_results/hindcast_report")
PRIMARY_DOMAIN = "d01"
TARGET_LATITUDE: float | None = None
TARGET_LONGITUDE: float | None = None


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "run_directory",
        nargs="?",
        type=Path,
        help="directory containing wrfout_d01_*, wrfout_d02_*, and so on",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIRECTORY,
        help=f"report directory (default: {OUTPUT_DIRECTORY})",
    )
    parser.add_argument(
        "--domain",
        default=PRIMARY_DOMAIN,
        help=f"primary analysis domain (default: {PRIMARY_DOMAIN})",
    )
    parser.add_argument("--latitude", type=float, default=TARGET_LATITUDE)
    parser.add_argument("--longitude", type=float, default=TARGET_LONGITUDE)
    arguments = parser.parse_args()

    arguments.run_directory = arguments.run_directory or RUN_DIRECTORY
    if arguments.run_directory is None:
        parser.error("provide RUN_DIRECTORY or set it in EDITABLE DEFAULTS")
    if (arguments.latitude is None) != (arguments.longitude is None):
        parser.error("--latitude and --longitude must be supplied together")
    return arguments


def main() -> int:
    arguments = parse_arguments()
    run_directory = arguments.run_directory.expanduser().resolve()
    output_directory = arguments.output.expanduser().resolve()

    if not run_directory.is_dir():
        raise SystemExit(f"WRF run directory does not exist: {run_directory}")
    if not any(run_directory.glob("wrfout_d??_*")):
        raise SystemExit(f"No wrfout_d??_* files found in: {run_directory}")

    print(f"Reading WRF output from: {run_directory}")
    print(f"Writing the report to:   {output_directory}")
    print(f"Primary domain:          {arguments.domain}")

    products = create_hindcast_report(
        run_directory,
        output_directory,
        domain=arguments.domain,
        latitude=arguments.latitude,
        longitude=arguments.longitude,
    )

    print("\nReport complete:")
    for product, path in products.items():
        print(f"  {product:8s} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
