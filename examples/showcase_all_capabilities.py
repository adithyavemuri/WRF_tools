#!/usr/bin/env python3
"""Run a chaptered showcase and account for EVERY cataloged capability.

Quick start (no WRF download, observations or external simulation required):
    python examples/showcase_all_capabilities.py --output example_results/showcase

Read/edit the small chapters in examples/showcase/. Inputs are explicitly
SYNTHETIC. This demonstrates execution, not atmospheric validation. A runtime
ledger records real function calls; new/unaccounted functions fail the run.
External process/download capabilities are documented, never silently simulated.
"""
from __future__ import annotations

import argparse
import hashlib
from collections import Counter
import json
import os
from pathlib import Path
import sys
import traceback

from wrf_tools.capabilities import capability_catalog, get_capability
from showcase import arrays, files, wrf, plots


# These operations are intentionally NOT run with fabricated executables/files.
# Each has a runnable public API/example path and prerequisites in the ledger.
EXTERNAL = {
    "maps.setup_map_data":dict(reason="Explicit network download; showcase is offline/cache-only", usage="wrf-tools setup-maps --resolution 50m"),
    "workflow.convert_grib_to_netcdf":dict(reason="Needs an installed wgrib2 and real GRIB input", usage="from wrf_tools.workflow import convert_grib_to_netcdf; convert_grib_to_netcdf('input.grib2','output.nc')"),
    "openfast.run_openfast":dict(reason="Needs OpenFAST plus a complete user-reviewed turbine model", usage="from wrf_tools.openfast import run_openfast; run_openfast('model/turbine.fst')"),
}


class Showcase:
    def __init__(self,output):
        self.output=Path(output).resolve()
        if self.output.exists() and any(self.output.iterdir()):
            raise FileExistsError(f"Use an empty/new output directory: {self.output}")
        self.output.mkdir(parents=True,exist_ok=True)
        self.catalog=capability_catalog(); self.calls=Counter(); self.chapters={}; self.chapter="setup"
        self.failures=[]; self.dataset=None

    def _profile(self,frame,event,arg):
        if event!="call": return
        module=frame.f_globals.get("__name__","")
        if not module.startswith("wrf_tools."): return
        identity=module[len("wrf_tools."):] + "." + frame.f_code.co_name
        if identity in self.catalog:
            self.calls[identity]+=1
            self.chapters.setdefault(identity,set()).add(self.chapter)

    def call(self,identity,*args,**kwargs):
        """Use the same callable resolver as TOML recipes; exceptions stay visible."""
        return get_capability(identity)(*args,**kwargs)

    def save(self,value,name):
        import matplotlib.pyplot as plt
        figure=value[0] if isinstance(value,(list,tuple)) else value
        figure.savefig(self.output/name,dpi=150,bbox_inches="tight"); plt.close(figure)

    def finish(self):
        rows=[]
        for identity,entry in self.catalog.items():
            if self.calls[identity]:
                status="EXERCISED_SYNTHETIC"; detail=dict(calls=self.calls[identity],chapters=sorted(self.chapters[identity]))
            elif identity in EXTERNAL:
                status="REQUIRES_EXTERNAL_INPUT"; detail=EXTERNAL[identity]
            else:
                status="UNACCOUNTED"; detail={}
            rows.append(dict(id=identity,status=status,**detail,basis=entry["basis"]))
        counts=dict(Counter(row["status"] for row in rows))
        report=dict(data_origin="SYNTHETIC — NOT A WRF SIMULATION OR REAL OBSERVATIONS",
            interpretation="Runtime entry-point coverage, not branch coverage or scientific validation. Failures invalidate the run.",
            capability_count=len(rows),counts=counts,failures=self.failures,capabilities=rows)
        import wrf_tools
        root=Path(wrf_tools.__file__).parent
        source_hash=hashlib.sha256()
        for source in sorted(root.rglob("*.py")):
            source_hash.update(source.relative_to(root).as_posix().encode()); source_hash.update(source.read_bytes())
        report["package_source_sha256"]=source_hash.hexdigest()
        (self.output/"capability-coverage.json").write_text(json.dumps(report,indent=2)+"\n")
        lines=["# Complete capability showcase","",report["data_origin"],"",report["interpretation"],"",
            f"Catalog: {len(rows)} functions. Counts: {counts}.","",
            "| Capability | Status | Chapter / required input |","|---|---|---|"]
        for row in rows:
            note=", ".join(row.get("chapters",[])) or row.get("reason","")
            lines.append(f"| `{row['id']}` | {row['status']} | {note} |")
        if self.failures: lines.extend(["","## Failures","",*self.failures])
        (self.output/"capability-coverage.md").write_text("\n".join(lines)+"\n")
        print(json.dumps(dict(capabilities=len(rows),counts=counts,failures=self.failures),indent=2))
        return 1 if self.failures or counts.get("UNACCOUNTED",0) else 0


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output",type=Path,default=Path("example_results/showcase"))
    args=parser.parse_args(argv)
    import matplotlib
    matplotlib.use("Agg")
    # Preserve/restore caller policy. No implicit downloads in a demonstration.
    previous=os.environ.get("WRF_TOOLS_OFFLINE_MAPS")
    showcase=Showcase(args.output)
    os.environ["WRF_TOOLS_OFFLINE_MAPS"]="1"
    old_profile=sys.getprofile()
    try:
        sys.setprofile(showcase._profile)
        for chapter in (arrays,files,wrf,plots):
            showcase.chapter=chapter.__name__.split(".")[-1]
            print(f"Running SYNTHETIC chapter: {showcase.chapter}",flush=True)
            try: chapter.run(showcase)
            except Exception as exc:
                showcase.failures.append(f"{showcase.chapter}: {type(exc).__name__}: {exc}")
                traceback.print_exc()
    finally:
        sys.setprofile(old_profile)
        if showcase.dataset is not None: showcase.dataset.close()
        import matplotlib.pyplot as plt
        plt.close("all")
        if previous is None: os.environ.pop("WRF_TOOLS_OFFLINE_MAPS",None)
        else: os.environ["WRF_TOOLS_OFFLINE_MAPS"]=previous
    return showcase.finish()


if __name__=="__main__":
    raise SystemExit(main())
