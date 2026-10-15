#!/usr/bin/env python3
"""Compare a real user-supplied station CSV with a WRF site time series.

    python examples/compare_observations.py /path/to/wrf/run station.csv \
      --latitude 52 --longitude 5 --domain d02 --variable wind_speed \
      --time-column time --value-column speed --observation-units 'm s-1' \
      --tolerance-minutes 15 --output reports/station-check

CSV times must be ISO timestamps (explicit timezone offsets are converted to
UTC; use the fixed-offset flag only for naive local timestamps).
Values must already have matching units,
height (10 m for wind, 2 m for temperature), and averaging conventions. No
instrument QC, calibration, height conversion, or gap filling is invented.
"""
import argparse
import json
from pathlib import Path
import numpy as np

from wrf_tools.io import discover_wrfout,open_wrf_sequence
from wrf_tools.grid import nearest_grid_point
from wrf_tools.observations import read_csv,normalize_time,from_columns,align
from wrf_tools.validation import comparison_summary
from wrf_tools.visualization import history_times
from wrf_tools.plotting import validation_scatter


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_directory",type=Path)
    parser.add_argument("observations",type=Path)
    parser.add_argument("--latitude",type=float,required=True)
    parser.add_argument("--longitude",type=float,required=True)
    parser.add_argument("--domain",default="d01")
    parser.add_argument("--variable",choices=["wind_speed","T2"],default="wind_speed")
    parser.add_argument("--time-column",default="time")
    parser.add_argument("--value-column",default="speed")
    parser.add_argument("--observation-units",required=True,help="Exact units: 'm s-1' for 10 m speed or 'K' for T2")
    parser.add_argument("--timezone-offset-hours",type=float,default=0,help="Fixed offset from UTC, not a daylight-saving timezone conversion")
    parser.add_argument("--tolerance-minutes",type=float,required=True,help="Maximum nearest-time separation; never match outside this tolerance")
    parser.add_argument("--output",type=Path,default=Path("example_results/observations"))
    args=parser.parse_args(argv)
    expected="m s-1" if args.variable=="wind_speed" else "K"
    if args.observation_units!=expected: parser.error(f"Convert observations to {expected!r} first")
    if not np.isfinite(args.tolerance_minutes) or args.tolerance_minutes<=0: parser.error("Tolerance must be positive and finite")
    observations=normalize_time(read_csv(args.observations,time_column=args.time_column,columns=[args.value_column]),
        timezone_offset_hours=args.timezone_offset_hours).rename({args.value_column:"value"})
    if not observations.indexes["time"].is_unique: raise ValueError("Observation timestamps must be unique; aggregate/QC explicitly first")
    files=discover_wrfout(args.run_directory,domain=args.domain)
    with open_wrf_sequence(files) as ds:
        cell=nearest_grid_point(ds.XLAT.isel(Time=0),ds.XLONG.isel(Time=0),args.latitude,args.longitude)
        point=dict(south_north=cell.y,west_east=cell.x)
        values=np.hypot(ds.U10.isel(point),ds.V10.isel(point)) if args.variable=="wind_speed" else ds.T2.isel(point)
        model=from_columns(time=np.asarray(history_times(ds),dtype="datetime64[s]"),variables={"value":values})
        tolerance_ms=round(args.tolerance_minutes*60*1000)
        if tolerance_ms<1: raise ValueError("Tolerance must be at least one millisecond")
        matched,observed=align(model,observations,tolerance=np.timedelta64(tolerance_ms,"ms"))
        valid=np.isfinite(matched.value)&np.isfinite(observed.value)
        if int(valid.sum())<2: raise ValueError("Fewer than two finite matched pairs; inspect times, missing values and tolerance")
        scores={key:float(value) if np.isfinite(value) else None for key,value in comparison_summary(matched.value.values,observed.value.values).items()}
        report=dict(data_origin="User-supplied observations; not independently quality-controlled",
            variable=args.variable,units=expected,matching="Nearest saved WRF time, no interpolation",tolerance_minutes=args.tolerance_minutes,
            matched_pairs=int(valid.sum()),unmatched_or_nonfinite=int((~valid).sum()),statistics=scores,
            site=dict(x=int(cell.x),y=int(cell.y),latitude=cell.latitude,longitude=cell.longitude),
            inputs=[p.name for p in files]+[args.observations.name])
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"comparison.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    import matplotlib.pyplot as plt
    fig,_,_=validation_scatter(matched.value.values[valid],observed.value.values[valid])
    fig.suptitle(f"{args.domain.upper()} {args.variable} ({expected}) | user observations")
    fig.savefig(args.output/"comparison.png",dpi=180,bbox_inches="tight"); plt.close(fig)
    pairs=matched.rename(value="model").assign(observed=observed.value)
    pairs.model.attrs={"units":expected,"long_name":"Nearest-time WRF value"}
    pairs.observed.attrs={"units":expected,"long_name":"User-supplied measurement, not independently quality controlled"}
    pairs.attrs={"time_reference":"UTC","tolerance_minutes":args.tolerance_minutes,
        "height_metres":10 if args.variable=="wind_speed" else 2,
        "matching":"Nearest saved WRF time, no interpolation; unmatched pairs remain NaN"}
    pairs.to_netcdf(args.output/"matched-pairs.nc")
    print(json.dumps(report,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
