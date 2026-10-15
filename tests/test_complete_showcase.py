"""The runnable showcase must account for the entire current public surface."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from wrf_tools.capabilities import capability_catalog


def test_complete_showcase_has_no_unaccounted_capabilities(tmp_path):
    for module in ("cartopy","reportlab","netCDF4","matplotlib","PIL"):
        pytest.importorskip(module)
    root=Path(__file__).resolve().parents[1]
    output=tmp_path/"showcase"
    completed=subprocess.run([sys.executable,str(root/"examples/showcase_all_capabilities.py"),"--output",str(output)],
        cwd=root,env={**os.environ,"MPLBACKEND":"Agg","MPLCONFIGDIR":str(tmp_path/"mpl")},
        capture_output=True,text=True,timeout=300)
    assert completed.returncode==0,completed.stdout+completed.stderr
    report=json.loads((output/"capability-coverage.json").read_text())
    assert {row["id"] for row in report["capabilities"]}==set(capability_catalog())
    assert not report["failures"] and "UNACCOUNTED" not in report["counts"]
    external={row["id"] for row in report["capabilities"] if row["status"]=="REQUIRES_EXTERNAL_INPUT"}
    assert external=={"maps.setup_map_data","openfast.run_openfast","workflow.convert_grib_to_netcdf"}
    assert report["package_source_sha256"]
    summary=json.loads((output/"synthetic-report/hindcast-summary.json").read_text())
    assert summary["overview"]["forcing_interval_seconds"] is None
    assert summary["domains"]["d01"]["file_count"]==2
    assert summary["domains"]["d01"]["sample_count"]==32
    assert summary["overview"]["history_interval_minutes"]==pytest.approx(1/6)


def test_real_observation_example_with_explicit_synthetic_fixture(tmp_path):
    pytest.importorskip("netCDF4"); pytest.importorskip("matplotlib")
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root/"examples"))
    try:
        from showcase.data import synthetic_wrf
        from compare_observations import main
        ds=synthetic_wrf(); run=tmp_path/"wrf"; run.mkdir()
        ds.to_netcdf(run/"wrfout_d01_2025-01-01_00_00_00")
        csv=tmp_path/"station.csv"
        # Intentionally shifted times remain within the explicit 15 s tolerance.
        csv.write_text("time,speed\n2025-01-01T00:00:01,6.5\n2025-01-01T00:00:11,7.0\n2025-01-01T01:00:00,8.0\n")
        out=tmp_path/"comparison"
        assert main([str(run),str(csv),"--latitude","52","--longitude","5",
            "--observation-units","m s-1","--tolerance-minutes","0.25","--output",str(out)])==0
        report=json.loads((out/"comparison.json").read_text())
        assert report["matched_pairs"]==2 and report["unmatched_or_nonfinite"]==1
        assert (out/"comparison.png").is_file() and (out/"matched-pairs.nc").is_file()
        import xarray as xr
        with xr.open_dataset(out/"matched-pairs.nc") as pairs:
            assert pairs.model.attrs["units"]==pairs.observed.attrs["units"]=="m s-1"
            assert pairs.attrs["height_metres"]==10 and pairs.attrs["time_reference"]=="UTC"
            assert pairs.attrs["tolerance_minutes"]==.25
    finally:
        sys.path.remove(str(root/"examples"))
