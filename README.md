# WRF Tools

Current release: **v0.5.0** (beta)

See the [release notes](CHANGELOG.md) for new workflows, calculation corrections,
compatibility notes and verification limits.

[![Tests](https://github.com/adithyavemuri/WRF_tools/actions/workflows/ci.yml/badge.svg)](https://github.com/adithyavemuri/WRF_tools/actions/workflows/ci.yml)
[![Python 3.10 | 3.12](https://img.shields.io/badge/python-3.10%20%7C%203.12-blue)](https://www.python.org/)
[![MIT License](https://img.shields.io/github/license/adithyavemuri/WRF_tools)](LICENSE)
[![Latest release](https://img.shields.io/github/v/release/adithyavemuri/WRF_tools?include_prereleases)](https://github.com/adithyavemuri/WRF_tools/releases)

> **Scientific basis:** equations, assumptions, applicability limits, and
> primary references are documented in
> [Scientific methods and references](docs/SCIENTIFIC_METHODS.md).

WRF Tools is a cross-platform Python toolkit for reproducible post-processing
of Weather Research and Forecasting (WRF) model output. It brings WRF I/O,
meteorological diagnostics, WRF-LES turbulence analysis, spectral methods,
wind-energy workflows, visualization, quality control, and OpenFAST/TurbSim
coupling into one tested package.

> **Flagship workflow:** convert an extracted WRF-LES velocity plane into a
> TurbSim full-field (`.bts`) inflow file for OpenFAST, then validate the binary
> round trip before using it in a load simulation.

The project is designed for researchers and engineers who want reusable APIs
instead of one-off scripts. Functions accept general WRF datasets or
NumPy-compatible arrays wherever practical and avoid hard-coded domains,
locations, or machine paths.

> Status: beta. Users should independently validate diagnostics against the
> conventions of their WRF configuration before publication or operational use.

## Flagship: WRF-LES to TurbSim/OpenFAST

WRF Tools bridges atmospheric LES output and wind-turbine aeroelastic
simulation. It accepts the three WRF-LES velocity components in any declared
3-D axis order, maps them to OpenFAST's longitudinal/lateral/vertical
convention, writes the signed-16-bit TurbSim full-field format, reads the file
back, and checks its metadata and quantization error.

```bash
python examples/wrf_les_to_openfast.py \
  --u u_plane.npy --v v_plane.npy --w w_plane.npy \
  --output inflow.bts --dt 0.10 --dy 10 --dz 10 \
  --hub-height 120 --bottom-height 10

wrf-tools bts-info inflow.bts
```

The arrays in this example are `(time, vertical, lateral)`. Other layouts are
supported through explicit axis arguments. The workflow deliberately requires
the user to confirm plane orientation, wind rotation, component signs, spatial
spacing, time step, and rotor coverage; those choices cannot be inferred safely
from arbitrary WRF extraction products. See the
[complete flagship example](examples/wrf_les_to_openfast.py) and the
[scientific-methods ledger](docs/SCIENTIFIC_METHODS.md).

The binary convention is checked against the official
[OpenFAST Toolbox implementation](https://github.com/OpenFAST/openfast_toolbox/blob/main/openfast_toolbox/io/turbsim_file.py)
and the [TurbSim v2 User's Guide](https://openfast.readthedocs.io/en/v4.0.5/_downloads/cb14d3e2d3533d76e405d730fea19846/TurbSim_v2.00.pdf).

## Why use it?

- Analyze ordinary WRF and turbulence-resolving WRF-LES output.
- Process one file or a time-ordered sequence from the same WRF domain.
- Extract sites, profiles, planes, cross-sections, and interpolated levels.
- Run data-quality checks that report variables, values, and error locations.
- Calculate boundary-layer, thermodynamic, precipitation, terrain,
  turbulence, wind-resource, spectral, coherence, and temporal diagnostics.
- Convert WRF-LES velocity fields to TurbSim/OpenFAST inflow formats.
- Produce consistent publication-oriented plots and HTML/PDF reports.
- Use the same Python API and command line on Linux and Windows.

## Example output

The repository includes a report generated from a real two-domain WRF run:

- [Final real-data hindcast PDF](example_results/final-report/hindcast-report.pdf)
- [Complete capability showcase](examples/showcase_all_capabilities.py) — labelled synthetic inputs and a coverage ledger
- [Beginner tutorial: inspect variables, make a custom map, and create a report](examples/README.md)
- [Complete readable example script](examples/create_hindcast_report.py)
- [Audit findings and verification boundary](docs/AUDIT.md)
- [Per-capability execution ledger](docs/validation/capability-coverage.md)

The old one-file demonstration and its short-record spectrum images were removed:
they overstated completeness and mixed sampling interpretations. The new showcase
separates synthetic numerical examples from real WRF analysis.

![Real d02 wind overview: map, section, height-time evolution and profiles](docs/demo/d02-wind-overview.png)

## Capabilities

**Use the whole package:** [connected workflows](docs/CONNECTED_WORKFLOWS.md)
explains selectable report groups and editable TOML recipes.
`wrf-tools capabilities` lists every public top-level algorithm; the
[complete API index](docs/API_CATALOG.md) includes its inputs and source.
Q criterion, Stull stability diagnostics and the conditional partial TKE budget
are connected to the report. Missing prerequisites are reported, not hidden.

```bash
wrf-tools hindcast-report /data/wrf/run reports/my-case --diagnostics all
wrf-tools capabilities diagnostics.advanced.q_criterion
wrf-tools run-recipe examples/recipes/coupling-demo.toml --output reports/inflow-demo
```

| Area | Included functionality |
|---|---|
| WRF I/O | Discovery, inspection, validation, safe same-domain concatenation, variable access, provenance |
| Extraction | Geographic points/subsets, profiles, planes, cross-sections, requested-height interpolation |
| Grid and WPS | Destaggering, nearest cells, coordinate operations, eta levels, nested-domain validation |
| Meteorology | Wind, potential temperature, density, humidity, stability, precipitation, radar-rain conversion |
| Boundary layer | WRF PBLH analysis, threshold PBL diagnosis, stability classes, inversions, low-level jets |
| WRF-LES | Resolved fluxes, SGS stresses, resolved/SGS/total TKE, filtering, budget terms |
| Wind energy | Rotor-equivalent speed, shear, veer, turbulence intensity, Weibull fit, power density |
| Spectra | Periodogram, Welch PSD, cross-spectrum, coherence, radial spectra, slope fitting |
| Spatial analysis | Butterworth/top-hat filters, terrain metrics, regridding and conservation checks |
| Validation | Bias, MAE, RMSE, correlation, circular and normalized errors, Kantorovich distance |
| Plotting/reporting | Maps, barbs, profiles, sections, time-height plots, wind roses, JSON, HTML, PDF |
| OpenFAST/TurbSim | BTS/Bladed WND I/O, field operations, WRF-LES mapping, output/input processing |
| Observations | Generic mast, LiDAR, RADAR and SCADA tables; alignment and collocation |

See the [capability matrix](docs/CAPABILITY_MATRIX.md) and
[complete API catalog](docs/API_CATALOG.md) for detailed coverage.
Equations, methodological limits, and primary references are catalogued in
[Scientific methods and references](docs/SCIENTIFIC_METHODS.md).

### Reference-documented figures and animation

Hindcast reports include a four-panel wind overview per supported domain: a
geographic wind map, matching grid-row section, physical-height time evolution
and site profiles. PNG/SVG figures and JSON methods sidecars accompany the
report; the PDF contains a scientific-methods appendix with primary references.

```bash
wrf-tools animate-wind /data/wrf/run reports/wind_movie \
  --domain d02 --fps 1 --maximum-frames 7
```

This creates a fixed-scale GIF using actual WRF times, plus reusable PNG frames.
An optional Manim Community example renders actual physical-height contours in
3-D instead of composing presentation slides. See the [visualization guide](docs/VISUALIZATION.md) and
[beginner animation example](examples/animate_wrf_wind.py).

### Simple simulation comparisons

Overlay named time series or common-height profiles, optionally subtracting a
baseline. Select variables and averaging yourself; no comparison PDF or automatic
regridding. Uniform, cell-area and layer-thickness weighting are explicit options.
Try the synthetic plot example without running a simulation:

```bash
.venv/bin/python examples/compare_simulations.py --demo
```

See the [comparison and averaging guide](docs/COMPARISON.md) for real-run commands
and editable Python examples.

Model TKE plots are included when supported fields are present; missing TKE is
reported explicitly, not inferred from hourly wind variability. See
[TKE diagnostics](docs/TURBULENCE.md) and the
[capability exposure audit](docs/CAPABILITY_EXPOSURE.md) for what the report does
and does not use from the wider library.

For horizontal, selected-area, vertical-layer and time means, use the separate
[averaging example](examples/average_wrf_fields.py). It writes PNG/SVG plots and
reduced NetCDF with explicit coordinate/weight settings:

```bash
.venv/bin/python examples/average_wrf_fields.py --demo
```

## Installation

Python 3.10-3.12 is recommended. Python 3.13 may not yet be supported by every
optional compiled dependency, particularly `wrf-python`.

### Linux or macOS

```bash
git clone https://github.com/adithyavemuri/WRF_tools.git
cd WRF_tools
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[netcdf,science,plot,report]"
wrf-tools doctor
wrf-tools setup-maps --resolution 50m
```

Reports automatically download Natural Earth coastlines, borders, land, ocean
and lakes into Cartopy's local cache the first time they are needed. Later runs
are offline. `setup-maps` remains available for an explicit pre-download; if
the network is unavailable before the cache exists, reporting falls back to
Cartopy's bundled raster rather than failing the complete analysis.

### Hindcast report

`wrf-tools hindcast-report` discovers every `wrfout_d??_*` sequence in a run,
validates its timeline and grid consistency, and produces JSON, HTML and PDF.
For each domain it includes mapped surface fields, wind-resource diagnostics,
accumulated precipitation, model-level wind and temperature profiles, a wind
time-height section, and a diagnostic shear exponent. TKE is included only when
`TKE_PBL`, `QKE` or dynamics `TKE` is present in the files. This is a model-output report, not
observational validation or a turbine-energy assessment.

### Windows PowerShell

```powershell
git clone https://github.com/adithyavemuri/WRF_tools.git
cd WRF_tools
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[netcdf,science,plot,report]"
wrf-tools doctor
```

For dependency-file installation:

```bash
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

Normal reports, contours and the full showcase do not require `wrf-python`,
WRF compilation or administrator access. The separate compatibility dependency
file is only for users who also want external `wrf-python` integration:

```bash
python -m pip install -r requirements-wrf.txt
```

Installation and optional native-dependency notes are in
[docs/PREREQUISITES.md](docs/PREREQUISITES.md).

## Quick start

### Inspect, validate, and open WRF output

```bash
wrf-tools inspect /data/wrf/wrfout_d01_2024-01-01_00_00_00
wrf-tools validate /data/wrf/wrfout_d01_2024-01-01_00_00_00
```

```python
from wrf_tools.io import discover_wrfout, open_wrf_sequence

files = discover_wrfout("/data/wrf/run", domain="d01")
with open_wrf_sequence(files) as ds:
    print(ds.sizes["Time"])
```

Create a scientific multi-domain mesoscale hindcast report without running the
LES/OpenFAST example workflow:

```bash
wrf-tools hindcast-report /data/wrf/run reports/my_case \
  --domain d01 --latitude 52.0 --longitude 5.0
```

This discovers every WRF domain in the run, analyses each separately, and uses
`--domain` to identify the primary analysis domain. It produces JSON and HTML
summaries plus a paginated PDF with a nested-domain map, separate domain
sections, physics and grid metadata, meteorological statistics, QC findings,
10 m wind-resource screening, wind roses, maps and point time series. The wind
screening is explicitly not a hub-height or bankable resource assessment.

Add optional reproducibility metadata when it is available:

```bash
wrf-tools hindcast-report /data/wrf/run reports/my_case \
  --domain d02 \
  --configuration case.toml \
  --case-manifest case-manifest.json \
  --build-manifest build-manifest.txt \
  --workflow-state workflow-state.json
```

The compact PDF compares all discovered domains, normally placing two figures
per row. It includes accumulated precipitation, model-level wind and
temperature profiles, conditional model TKE maps/profiles/evolution, time-height wind and
a configurable shear-exponent diagnostic.

The sequence reader checks domain ID, grid dimensions, spacing, projection,
and time order. Mixed domains raise an error instead of being combined.

### Extract a site

```python
from wrf_tools.extract import point
from wrf_tools.io import open_wrf

with open_wrf("wrfout_d01_2024-01-01_00_00_00") as ds:
    site = point(ds, latitude=52.0, longitude=4.3,
                 variables=["T2", "U10", "V10"],
                 destagger_native=True)
    site.to_netcdf("site_timeseries.nc")
```

Generic extraction preserves the native WRF grid by default. For staggered
variables such as `U`, `V`, or `W`, request mass-grid values explicitly:

```python
from wrf_tools.io import get_variable

u_native = get_variable(ds, "U")
u_mass = get_variable(ds, "U", destagger_native=True)
```

The same `destagger_native` option is available on `point`,
`vertical_profile`, and `horizontal_plane`. Returned variables carry a
`wrf_tools_grid_processing` attribute, and destaggered output also records the
original dimensions in `wrf_tools_destaggered_dimensions`.

### Filtering and spectra

```python
from wrf_tools.filters import butterworth_spatial
from wrf_tools.spectra import radial_wavenumber_spectrum, welch_spectrum
from wrf_tools.wind_models import cheynet_spectrum

filtered = butterworth_spatial(
    u_plane, dx=50.0, dy=50.0,
    cutoff_wavelength=300.0, order=2,
)
frequency, psd = welch_spectrum(wind_series, sample_rate=2.0, nperseg=1200)
wavenumber, energy = radial_wavenumber_spectrum(u_plane, dx=50.0)
marine_psd = cheynet_spectrum(
    frequency, mean_speed=12.0, height=81.5,
    friction_velocity=0.45, stability=-0.2, component="u",
)
```

`cheynet_spectrum` implements the stability-dependent pointed-blunt marine
boundary-layer model of [Cheynet, Jakobsen and Reuder (2018)](https://doi.org/10.1007/s10546-018-0382-2),
using the author-supplied coefficient table at 81.5 m.

### Quality control and boundary-layer diagnostics

```python
from wrf_tools.quality import print_qc_report, quality_control
from wrf_tools.diagnostics import diagnose_pbl_height, low_level_jet

issues = quality_control(ds)
print_qc_report(issues)
pbl_height = diagnose_pbl_height(theta_v, height_agl, axis=1)
jet = low_level_jet(speed_profile, height_profile)
```

### WRF-LES to TurbSim/OpenFAST API

```python
from wrf_tools.coupling.openfast import (
    validate_bts, wind_field_from_components, write_bts,
)

field = wind_field_from_components(
    u_plane, v_plane, w_plane,
    time_axis=0, vertical_axis=1, lateral_axis=2,
    dy=10.0, dz=10.0, dt=0.1,
    hub_height=120.0, bottom_height=10.0,
)
write_bts("inflow.bts", field)
validate_bts("inflow.bts", expected=field)
```

`validate_bts` raises a descriptive error if dimensions, spacing, metadata, or
quantized velocities fail the round-trip tolerance. Successful serialization
does not establish that the LES inflow is physically suitable; consult the
coupling checklist in [Scientific methods](docs/SCIENTIFIC_METHODS.md).

## Run the complete capability showcase

For 3-D wind/TKE isosurfaces above WRF terrain and ocean, follow the
[model-cutout walkthrough](docs/ISOSURFACES.md). Its Manim renderer is optional
and separate from the PDF report and existing contour-stack example.
For manual orbit/zoom, actual saved times, a wind/W/vorticity/Q/model-TKE
selector and movable vertical sections, use the standalone offline
[interactive browser example](examples/interactive_isosurfaces.py). Missing
fields are disabled with reasons; methods and derivative assumptions are explicit.

No WRF download or real observations are required for this explicitly synthetic
demonstration. Read/edit the four chapters under `examples/showcase/`:

```bash
python -m pip install -e ".[isosurface,interactive]"
python examples/showcase_all_capabilities.py --output example_results/my_showcase
```

It exercises equations, data selection, statistics, filters/spectra, file formats,
plots, animations and reports. `capability-coverage.json`/`.md` accounts for every
public function. The current showcase exercises 208 of 211 and explicitly
documented three external prerequisites: map download, `wgrib2`, and OpenFAST.
New unaccounted functions or execution failures make the showcase fail. This is
entry-point coverage, NOT exhaustive branch coverage or atmospheric validation.

For real WRF output use `examples/create_hindcast_report.py`; for actual station
data use [compare_observations.py](examples/compare_observations.py). See the
[showcase guide](examples/showcase/README.md) for inputs, outputs and limitations.

## Command line

```text
wrf-tools doctor [--core-only] [--json]
wrf-tools capabilities [FUNCTION_ID] [--markdown PATH]
wrf-tools run-recipe RECIPE.toml --output DIRECTORY [--force]
wrf-tools discover DIRECTORY [--domain d01] [--recursive]
wrf-tools inspect WRFOUT
wrf-tools validate WRFOUT
wrf-tools concat OUTPUT INPUT [INPUT ...]
wrf-tools extract WRFOUT OUTPUT LATITUDE LONGITUDE VARIABLE [VARIABLE ...] [--destagger]
wrf-tools filter INPUT.npy OUTPUT.npy --dx DX --cutoff WAVELENGTH
wrf-tools spectra INPUT.npy OUTPUT.npz --spacing DT
wrf-tools report WRFOUT report.json
wrf-tools hindcast-report RUN_DIRECTORY OUTPUT_DIRECTORY [--domain d01]
wrf-tools setup-maps [--resolution 10m|50m|110m]
wrf-tools bts-info inflow.bts
wrf-tools bts-compare first.bts second.bts
wrf-tools openfast-info simulation.outb
```

## Scope and limitations

- This is a post-processing package; it does not compile or configure WRF.
- Multi-file concatenation handles sequential files from one domain, not
  mixed-domain mosaics.
- WRF output files are not distributed with the repository.

## Development

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -e . --no-deps
python -m pytest
python -m build
python -m twine check dist/*
```

Continuous integration tests Linux and Windows with Python 3.10 and 3.12. See
[CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

WRF Tools is available under the [MIT License](LICENSE). WRF, OpenFAST,
TurbSim, and other named projects retain their respective licenses and
trademarks.
