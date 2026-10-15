# Use the whole toolkit

Start with the [full chaptered showcase](../examples/showcase/README.md) for
every public callable and the [audit](AUDIT.md) for corrections and verification
boundaries. Its [recorded ledger](validation/capability-coverage.md) distinguishes
actual synthetic execution from external prerequisites.

**Reports** connect diagnostics using WRF history files directly. **Recipes**
chain any public top-level function, including ones requiring observations,
station output, SGS fields or turbine data. Existing Python APIs still work.

## Connected report

From the repository root, after installation:

```bash
wrf-tools hindcast-report /path/to/wrf/run reports/my-case \
  --diagnostics all --diagnostics-config examples/diagnostics.toml

# Or edit the settings near the top of this Python example:
python examples/create_hindcast_report.py /path/to/wrf/run --output reports/my-case
```

The default is `all`. Each group appears in PDF/JSON as `COMPLETE`, `UNAVAILABLE`
(reason supplied), or `NOT_SELECTED`. Numerical errors fail visibly.

| Group | What is connected | Important limitation |
|---|---|---|
| `thermodynamics` | Stull bulk Ri, signed N², humidity/density/dew point, simplified theta-e, inversions, threshold PBL height, Monin–Obukhov length, convective scale | Site column; approximate surface-flux conversion; extra arrays saved even when not all receive a panel. |
| `wind_resource` | Rotor-equivalent speed, shear/veer, low-level jet, Weibull screening | Set rotor bounds; uniform-height, not disk-area weighting; short periods are not climatologies. |
| `flow_structure` | Q criterion, horizontal vorticity/divergence/strain | Final snapshot on equally spaced **MSL** planes; no extrapolation. Nominal Cartesian gradients neglect projection metrics. |
| `spatial` | Terrain slope/aspect, land-use statistics, speed-up, edge/interior discontinuity | Domain-mean wind reference, not a paired control. |
| `spectral` | Periodogram/Welch/cross/coherence/log bins, radial spectra, filters/downsampling, conservation/regridding errors | Regular times, at least six for this group. Hourly spectra are weather, not LES; FFT filters assume periodicity. |
| `turbulence` | Resolved covariances/TKE, Stull shear/buoyancy production | Explicit time-average choice and sampling checks. Partial budget, not closed model-energy budget. |

Choose e.g. `--diagnostics thermodynamics,flow_structure`, or `none` for the
compact core. Edit [diagnostics.toml](../examples/diagnostics.toml) to control
rotor bounds, MSL heights and turbulence sampling. In the Python example edit
`DIAGNOSTIC_GROUPS` and `DIAGNOSTIC_OPTIONS` instead.

Each completed group saves `<domain>_analysis_<group>.png`, `.svg`, and `.npz`
beside `hindcast-report.pdf`, HTML and summary JSON. Read the actual arrays:

```python
import numpy as np
with np.load("reports/my-case/d02_analysis_flow_structure.npz") as data:
    q = data["q_criterion"]  # (MSL height, south_north, west_east)
```

Model-written QKE/2, TKE_PBL or dynamics TKE remains a separate report diagnostic.
Missing model TKE is not replaced by hourly wind variance.

## Discover and chain any public function

```bash
wrf-tools capabilities
wrf-tools capabilities diagnostics.advanced.q_criterion
wrf-tools capabilities diagnostics.advanced.tke_budget

# Synthetic demonstrations; no WRF files/OpenFAST executable needed:
wrf-tools run-recipe examples/recipes/coupling-demo.toml --output reports/inflow-demo
wrf-tools run-recipe examples/recipes/observations-demo.toml --output reports/obs-demo

# Edit paths and grid spacing first:
wrf-tools run-recipe examples/recipes/wrf-fields.toml --output reports/fields
wrf-tools run-recipe examples/recipes/external-files.toml --output reports/external
```

The [complete API index](API_CATALOG.md) shows signatures, docstrings and source.
Defining-module IDs avoid ambiguity from re-exports. A test ensures every public
top-level algorithm is cataloged and resolves to a callable. Private helpers,
class methods and CLI/recipe/catalog infrastructure are excluded. Discovery is
not proof of scientific validation.

The WRF recipe opens the sequence once, selects T2, filters it, and plots its
spatial spectrum. Add further steps using cataloged IDs:

```toml
[[steps]]
id = "temperature"
call = "io.datasets.get_variable"
args = [{ref = "wrf"}, "T2"]
kwargs = {time = -1}
save = "temperature.nc"
```

Recipe notation:

- `{ref="wrf"}` reuses a prior result. `path=[0]` selects a tuple member;
  `path=["velocity"]` selects a public attribute/dictionary key.
- `variable="T2"`, `isel={Time=-1}`, `sel={...}`, `array=true` select labelled
  data and optionally convert to NumPy. `{slice=[0,10,2]}` represents a slice.
- `{file="..."}` resolves relative to the TOML file; absolute paths also work.
- `{output="inflow.bts"}` confines a generated path under the output folder.
- `{type="GridPoint",kwargs={x=10,y=20}}` constructs a supported object;
  `GeoBounds`, `Station` and `WindField` are also supported.
- `save` writes arrays to `.npy`, flat array dictionaries to `.npz`, xarray data
  to NetCDF and figures to images. Scalar/metadata results use JSON. Tuple
  results are summarized: reference members in later steps for actual data.
  Matplotlib animations use their save method and need an appropriate writer.
- `optional=true` permits missing-input/dependency skips; descendants also skip.
  Typos/forward references fail preflight; calculation errors fail visibly.
- `enabled=false` records a disabled step. An existing manifest needs `--force`;
  prefer a new output folder for a new analysis.

`analysis-manifest.json` records calls, arguments, artifacts, statuses and errors.
Arrays in this manifest are shape/type summaries; use explicit save targets for
the data. Open datasets and figures are closed after the chain. This is a thin
runner, not a physics-selection engine or a substitute for input conventions.

**Review recipes before executing them.** Cataloged functions can write files,
invoke external converters or run OpenFAST when explicitly selected. Output
references are confined, but arbitrary function arguments are not sandboxed.
Recipes are not safe for untrusted-code execution.

## Existing focused workflows remain connected

| Task | Entry point |
|---|---|
| Horizontal/area/vertical/time means | [average_wrf_fields.py](../examples/average_wrf_fields.py), `averaging.*` |
| Multi-simulation overlays/differences | [compare_simulations.py](../examples/compare_simulations.py), `comparison.*` |
| Actual-time wind GIF/MP4 | `wrf-tools animate-wind`, [animate_wrf_wind.py](../examples/animate_wrf_wind.py) |
| Actual-data 3-D contours | [export_3d_contours.py](../examples/export_3d_contours.py) then [manim_wrf_contours.py](../examples/manim_wrf_contours.py); retained |
| WRF-LES plane → BTS | [wrf_les_to_openfast.py](../examples/wrf_les_to_openfast.py), coupling recipe/API |
| SGS energy, station TS/tslist, WPS, OpenFAST I/O | External-files recipe; own files and confirmed conventions required |
| Observations and statistics | Observation recipe, `observations.*`, `validation.*` |
| Wind models, plotting, QC, archive/converter helpers | Full catalog/recipe runner with researcher-supplied inputs |

Not every callable belongs in a PDF. Readers, writers and converters need their
own inputs or side effects; they remain executable through this documented path.

For real station data, [compare_observations.py](../examples/compare_observations.py)
writes matched-pair NetCDF, JSON statistics/counts and a scatter plot. Supply your
own calibrated/QC'd CSV, correct height/units and explicit time tolerance. The
included observation recipe uses synthetic data; it is not real validation.

## What was actually tested

Existing Netherlands d01/d02 hourly outputs exercise five ordinary report groups
and the WRF field recipe. The partial TKE-production path uses synthetic
fluctuating columns: this case has neither high-frequency LES output nor model
TKE. Inflow and observation recipes use synthetic data. External-file recipes
exercise visible missing-input skips, not a real turbine run or observation
validation. These checks do not establish atmospheric accuracy or validated
end-to-end operation of every public algorithm on one WRF case.
