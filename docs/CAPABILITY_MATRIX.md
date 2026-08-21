# WRF Tools capability migration matrix

This matrix tracks the deduplicated capabilities found in `source_collections`.
Repeated source implementations count as one capability. COAWST and ROSCO tuning
are excluded. The FAST MATLAB GUI, NCToolbox, and shell build/compile workflows
are deferred or excluded. Sequential files from one WRF domain are supported;
concatenating different domains into one dataset is not. See
`PACKAGE_EXPANSION.md` for the consolidated module-level plan.

## WRF data and workflow

| Capability | Original source | Target namespace | Status |
|---|---|---|---|
| Discover/open/validate WRF output | Python | `wrf_tools.io` | Implemented |
| Sequential same-domain multi-file datasets | Python | `wrf_tools.io` | Implemented |
| Variable extraction and derived WRF fields | Python/MATLAB | `wrf_tools.extract` | Implemented |
| Pressure/height interpolation | Python/MATLAB | `wrf_tools.grid` | Implemented |
| Station and profile extraction | Python/MATLAB | `wrf_tools.timeseries` | Implemented |
| GRIB-to-NetCDF conversion | Python | `wrf_tools.workflow` | Implemented |
| NetCDF subset/shrink/edit | Python | `wrf_tools.io` | Implemented |
| Automatic output aggregation/archival | Python | `wrf_tools.workflow` | Implemented |
| Eta-level generation | Python | `wrf_tools.wps` | Implemented |

## LES, filtering, and spectra

| Capability | Original source | Target namespace | Status |
|---|---|---|---|
| Destaggered velocity and basic flux/TKE | Python | `wrf_tools.les` | Implemented |
| Spatial Butterworth low-pass filtering | Python | `wrf_tools.filters` | Implemented |
| Honnert/top-hat coarse graining | Python | `wrf_tools.filters` | Implemented |
| Spectral box/downsampling filters | MATLAB | `wrf_tools.filters` | Implemented |
| FFT/wavenumber spectra | Python/MATLAB | `wrf_tools.spectra` | Implemented |
| Welch PSD and spectral binning | Python/MATLAB | `wrf_tools.spectra` | Implemented |
| SGS stress tensor diagnostics | Python | `wrf_tools.les` | Implemented |
| Resolved/SGS/total TKE partitioning | Python | `wrf_tools.les` | Implemented |
| Profile comparison, RMSE, and clustering | Python | `wrf_tools.validation` | Implemented |

## Meteorology, domains, and visualization

| Capability | Original source | Target namespace | Status |
|---|---|---|---|
| Wind speed/direction and component rotation | Python/MATLAB | `wrf_tools.diagnostics` | Implemented |
| Potential/virtual temperature and pressure | MATLAB/Python | `wrf_tools.diagnostics` | Implemented |
| Richardson number, friction velocity, stability | MATLAB | `wrf_tools.diagnostics` | Implemented |
| Precipitation and reflectivity conversion | Python | `wrf_tools.diagnostics` | Implemented |
| WPS nested-domain geometry/projections | Python | `wrf_tools.wps` | Implemented |
| Horizontal maps and wind barbs | Python | `wrf_tools.plotting` | Implemented |
| Pressure/model-level and vertical cross-sections | Python | `wrf_tools.plotting` | Implemented |
| Time series, time-height, and LES-plane plots | Python | `wrf_tools.plotting` | Implemented |
| Domain, terrain, and MODIS land-use plots | Python | `wrf_tools.plotting` | Implemented |
| Plot sequences and animations | Python | `wrf_tools.plotting` | Implemented |

## Observational validation

| Capability | Original source | Target namespace | Status |
|---|---|---|---|
| RADAR ingestion, interpolation, and comparison | Python/MATLAB | `wrf_tools.validation` | Implemented |
| LiDAR/SCADA/FINO/XPIA profile comparison | MATLAB | `wrf_tools.validation` | Implemented |
| RMSE, MAE, circular errors, and statistics | Python/MATLAB | `wrf_tools.validation` | Implemented |
| Kantorovich/transport distance | Python/MATLAB | `wrf_tools.validation` | Implemented |
| Wind shear/power-law regression | MATLAB | `wrf_tools.diagnostics` | Implemented |
| Wind roses and directional statistics | MATLAB | `wrf_tools.plotting` | Implemented |

## TurbSim and OpenFAST coupling/post-processing

| Capability | Original source | Target namespace | Status |
|---|---|---|---|
| WRF-LES plane to BTS conversion | Python/MATLAB | `wrf_tools.coupling.openfast` | Implemented |
| BTS read/write/round-trip validation | Python/MATLAB | `wrf_tools.coupling.openfast` | Implemented |
| TurbSim field concatenation and point/plane/profile extraction | Python/MATLAB | `wrf_tools.coupling.openfast` | Implemented |
| BL-grid, full-field text, HH, WND, and CTS formats | MATLAB | `wrf_tools.coupling.openfast` | Implemented |
| Kaimal, IEC Kaimal, Cheynet, and von Karman spectra | MATLAB/Python | `wrf_tools.wind_models` | Implemented |
| Coherent synthetic wind-field generation | MATLAB/Python | `wrf_tools.wind_models` | Implemented |
| FAST text/binary output readers | MATLAB/Python | `wrf_tools.openfast` | Implemented |
| PSD, rainflow, zero crossing, loads, and stress | MATLAB/Python | `wrf_tools.openfast` | Implemented |
| FAST input parsing/editing helpers | MATLAB/Python | `wrf_tools.openfast_input` | Implemented |

## Shell-only operational capabilities (deferred)

- Build zlib, HDF5, NetCDF-C/Fortran, MPI, libpng, and JasPer dependencies.
- Configure and compile WRF and WPS and verify their executables.
- Generate hourly/daily `namelist.input` files, run `real.exe` and `wrf.exe`
  under MPI, inspect logs, and archive outputs.
- Build COAWST (excluded from this package).

These are inventoried but are not part of the current post-processing migration.

## Bundled third-party material

The collection also contains upstream NCToolbox, FAST MATLAB Toolbox, FAST v8
GUI, format-conversion utilities, and demonstration files. NCToolbox and GUI
code are excluded. Useful post-processing file formats and analysis behavior
will be exposed through Python APIs where relevant; vendored source, GUI code,
and historical conversion internals will not be copied wholesale.
