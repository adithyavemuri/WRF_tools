# All capabilities, with honest inputs

From the WRF_tools repository root after installing the plotting, report,
NetCDF, science, animation, isosurface and interactive extras:

```bash
python -m pip install -e ".[netcdf,science,plot,report,animation,isosurface,interactive]"
python examples/showcase_all_capabilities.py --output example_results/my_showcase
```

Use a **new/empty** output directory each time; nothing is silently deleted.
The showcase uses small, clearly labelled **synthetic** inputs and never starts
WRF, OpenFAST, a converter, or a network download.

## Read the chapters in this order

1. [arrays.py](arrays.py): physical formulas, finite-pair statistics, spectra,
   filters, wind models and explicit averaging. Change inputs beside each call.
2. [files.py](files.py): synthetic observations, station/WPS files, turbine
   output and inflow-format round trips. No real instrument validation is implied.
3. [wrf.py](wrf.py): create/read WRF-shaped files, select/destagger variables,
   calculate physical coordinates, exercise LES/model-TKE paths, render report,
   animation, contour geometry, terrain-aware isosurfaces and offline HTML.
   [data.py](data.py) declares all input fields.
4. [plots.py](plots.py): basic plots, Taylor/scatter diagrams, named simulation
   comparisons, reports and environment checks.

`c.call("module.function", ...)` uses the same resolver as editable recipes.
Runtime instrumentation records which **actual public functions were entered**,
including calls made inside a report. It is not a fabricated tick list. Any
chapter failure invalidates the run; an unaccounted capability makes it fail.
The first successful audit exercised 204 of 207 functions and listed three
external operations separately. The count is derived, not assumed.

## Outputs to open

- `capability-coverage.md`: readable per-function status/chapter table.
- `capability-coverage.json`: same evidence plus method references, actual call
  counts, failure list and a hash of the package source snapshot.
- `synthetic-report/hindcast-report.pdf`: report-writer demonstration, NOT an
  atmospheric simulation. The real Netherlands PDF is under `docs/demo/`.
- `groups/`: every diagnostic group, including the synthetic partial Stull budget.
- `synthetic-animation/`, `synthetic-fields.gif`, `synthetic-contours.json`:
  actual outputs of the demo APIs; these do not replace the retained real-WRF
  Manim example or assert physically realistic turbulence.
- `formats/`, `archive/`, `aggregated.nc`: parser, writer and aggregation outputs.
- Other PNG/PDF/SVG/JSON files: editable plot and provenance examples.

## Three operations with real prerequisites

The ledger records `REQUIRES_EXTERNAL_INPUT`, never a false successful execution:

| Capability | What you must supply | How to run it |
|---|---|---|
| `maps.setup_map_data` | Network permission and Cartopy cache space | `wrf-tools setup-maps --resolution 50m` |
| `workflow.convert_grib_to_netcdf` | Real GRIB and installed `wgrib2` | Import the function and provide source/output paths and optional executable |
| `openfast.run_openfast` | OpenFAST executable and complete reviewed turbine configuration | Import the function and pass the `.fst` path and optional executable |

The generic recipe runner can call these too. Do not substitute fake executables
and call that an engineering or interoperability test.

## Real observations

The observation recipe and this showcase use fabricated measurements only to
test wiring. For actual user data:

```bash
python examples/compare_observations.py /path/to/wrf/run station.csv \
  --domain d02 --latitude 52 --longitude 5 --variable wind_speed \
  --time-column time --value-column speed --observation-units 'm s-1' \
  --tolerance-minutes 15 --output reports/station-check
```

This writes matched-pair NetCDF, JSON scores/counts and a scatter plot. Unmatched
or non-finite pairs do not enter scores. You must provide QC/calibration,
matching height, units, averaging interval and UTC interpretation. Wind here is
10 m speed; T2 is 2 m temperature in Kelvin. No native SCADA/radar/LiDAR format,
height correction, uncertainty model or claimed real-world validation is supplied.

## What the showcase does not prove

Function-entry coverage is not branch coverage. Successful execution is not
proof that all input configurations, missing-data patterns or external formats
work. References state equations/conventions; analytical and independent-oracle
tests verify selected numerical cases. Real-WRF reports test data handling.
Atmospheric/engineering accuracy needs appropriate external validation.

The repeat audit also checks uneven-level derivatives, missing rainfall,
zero-resultant directions, spectral variance normalization and UTC matching.
Those assertions live in `tests/test_repeat_audit.py`; entering a function here
does not replace them. The old `scripts/audit_all_capabilities.py` was removed
because it depended on retired classes and an old hard-coded version. This
chaptered showcase is the maintained replacement.
