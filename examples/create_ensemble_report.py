#!/usr/bin/env python3
"""Edit the member folders, then run. Reads existing output; no simulation.

Every time series shows all members and the mean. CONTOUR_MEMBER controls
only the maps, so selecting a member does not hide the other member traces.
"""
from pathlib import Path
from wrf_tools.ensemble import create_ensemble_report

# Replace these with the folders containing each simulation's wrfout files.
MEMBERS = {"control": Path("runs/control/wrf"),
           "alternative-physics": Path("runs/alternative-physics/wrf")}
OUTPUT = Path("example_results/ensemble_report")
REPORT_DOMAINS = ["d02"]  # None means every domain; overview still shows all nests.
CONTOUR_MEMBER = "mean"  # Or a key in MEMBERS, e.g. "control".
VARIABLES = None  # Default suite; or ["wind_speed_10m", "T2", "PBLH"].
LATITUDE = None  # Set both, or leave both None for each domain's centre.
LONGITUDE = None

if __name__ == "__main__":
    files = create_ensemble_report(MEMBERS, OUTPUT, report_domains=REPORT_DOMAINS,
        contour_member=CONTOUR_MEMBER, variables=VARIABLES,
        latitude=LATITUDE, longitude=LONGITUDE)
    for kind, path in files.items():
        print(f"{kind}: {path}")
