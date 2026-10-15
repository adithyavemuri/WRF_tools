# WRF Tools capability migration matrix

This matrix describes the current package's supported capabilities. COAWST and ROSCO tuning
are excluded. The FAST MATLAB GUI, NCToolbox, and shell build/compile workflows
are deferred or excluded. Sequential files from one WRF domain are supported;
concatenating different domains into one dataset is not. See
the [API catalog](API_CATALOG.md) and [runtime audit](AUDIT.md) for verified scope.

## WRF data and workflow

| Capability | Original source | Target namespace | Status |
|---|---|---|---|
| Discover/open/validate WRF output | Python | `wrf_tools.io` | Implemented |
| Sequential same-domain multi-file datasets | Python | `wrf_tools.io` | Implemented |
| Variable extraction and derived WRF fields | Python/MATLAB | `wrf_tools.extract` | Implemented |
| Pressure/height interpolation | Python/MATLAB | `wrf_tools.grid` | Implemented |
| Station and profile extraction | Python/MATLAB | `wrf_tools.timeseries` | Implemented |
| GRIB-to-NetCDF conversion | Python | `wrf_tools.workflow` | Implemented |
| NetCDF variable selection/export | Python | `wrf_tools.io` | xarray selections/export; no dedicated shrink/editor engine |
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
| Model-level/vertical cross-sections | Python | `wrf_tools.plotting` | Plot supplied arrays; generic coordinate interpolation, not an automatic pressure-diagnostic engine |
| Time series, time-height, and LES-plane plots | Python | `wrf_tools.plotting` | Implemented |
| Domain, terrain and land-use-code plots | Python | `wrf_tools.plotting`, `diagnostic_groups` | Implemented; categorical codes, not a full MODIS legend/reader |
| Plot sequences and animations | Python | `wrf_tools.plotting` | Implemented |
| Reference-documented four-panel wind overview, PNG/PDF/SVG and methods JSON | New | `wrf_tools.visualization` | Implemented; required WRF fields only |
| Fixed-scale geographic 10 m wind GIF/MP4 and actual-time PNG frames | New | `wrf_tools.animations` | Implemented; stationary grids; MP4 needs FFmpeg |
| Optional actual-field 3-D contour stack | New | `wrf_tools.contours3d`, `examples/manim_wrf_contours.py` | Rendered with real d02 wind; not volumetric isosurfaces |
| Model TKE conversion, maps, profiles, time-height and level maxima | New | `wrf_tools.turbulence` | Conditional report integration; analytical/synthetic tests; real demo has no TKE |
| Named time-series/profile overlays and baseline differences | New | `wrf_tools.comparison` | Implemented; matched 1-D coordinates, no regridding or PDF |
| Explicit uniform/area/layer means and common physical heights | New | `wrf_tools.averaging` | Implemented; user supplies selections/weights, eager interpolation |
| Managed reduction caches and parallel multi-file reductions | Proposed | Not yet added | Future milestone |

## Observational validation

| Capability | Original source | Target namespace | Status |
|---|---|---|---|
| RADAR ingestion, interpolation, and comparison | Python/MATLAB | `wrf_tools.observations`, `wrf_tools.validation` | Generic CSV/NetCDF and array helpers only; no dedicated radar-format reader |
| LiDAR/SCADA/FINO/XPIA profile comparison | MATLAB | `wrf_tools.validation` | Generic profile/statistics helpers; instrument-specific loaders are not supplied |
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
| Supported full-field text, HH, Bladed WND and coherent-point layouts | MATLAB | `wrf_tools.coupling.openfast` | Limited migrated layouts; synthetic fixtures/round trips, not every legacy variant or external interoperability |
| Kaimal, IEC Kaimal, Cheynet, and von Karman spectra | MATLAB/Python | `wrf_tools.wind_models` | Implemented |
| Synthetic demonstration wind field | MATLAB/Python | `wrf_tools.wind_models` | Filtered Gaussian test data; NOT prescribed coherence, IEC or TurbSim generation |
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
