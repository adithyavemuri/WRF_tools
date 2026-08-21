# Package expansion

This package structure consolidates the migratable Python and MATLAB post-processing found
in `source_collections`. Duplicate scripts and case-specific variants become
one configurable API. The FAST MATLAB GUI, NCToolbox, ROSCO tuning, COAWST, and
shell build/compile workflows are out of scope.

## `wrf_tools.io`

- Discover and inspect WRF output files.
- Open one file or concatenate chronological files from the same domain.
- Reject incompatible domain IDs, projections, horizontal grids, vertical
  grids, or overlapping/non-monotonic time coordinates.
- Decode WRF `Times` and normalize coordinates and metadata.
- Validate required variables, dimensions, grid staggering, units, and missing
  values.
- Select, subset, shrink, and export NetCDF datasets without modifying sources.
- Aggregate selected variables from completed output files.

## `wrf_tools.extract`

- Extract native and derived variables by time, grid point, geographic point,
  station, bounding box, model level, pressure level, or physical height.
- Extract horizontal planes, vertical columns, transects, and turbine-centred
  wind planes.
- Interpolate wind, temperature, pressure, moisture, TKE, stress, cloud, and
  precipitation fields to requested levels.
- Calculate height MSL and AGL and account for terrain elevation.
- Assemble aligned station/profile datasets from multiple WRF files.

## `wrf_tools.grid`

- Destagger arbitrary NumPy and xarray dimensions.
- Convert all native WRF wind components to the mass grid.
- Find nearest cells using great-circle distance.
- Geographic and index-based subsetting with padding.
- Horizontal regridding and grid-resolution matching.
- Vertical interpolation to height, pressure, theta, or model levels.
- Cross-section coordinate generation and terrain-following gap filling.
- Great-circle distance and grid-index conversion helpers.

## `wrf_tools.filters`

- Generalized 1-D and 2-D Butterworth low/high/band-pass filters.
- Spatial FFT Butterworth filtering using explicit `dx`, `dy`, cutoff
  wavelength, order, and axes.
- Honnert/top-hat block filtering and coarse graining.
- Spectral box filtering and filtered downsampling.
- Optional Hamming/Hann windowing and mean preservation/removal.
- Filter transfer functions and resolved/subfilter decomposition.
- NumPy and metadata-preserving xarray support.

## `wrf_tools.spectra`

- FFT frequency and horizontal wavenumber spectra.
- One-dimensional, two-dimensional, and radial spectra.
- Welch PSD and cross-spectral density.
- Coherence, co-coherence, quadrature spectrum, and phase.
- Spectral binning and logarithmic averaging.
- Sampling-time/frequency construction and Nyquist checks.
- Normalized atmospheric spectra and height-dependent spectral profiles.
- Resolution/filter comparison and spectral error metrics.

## `wrf_tools.diagnostics`

- Wind speed, meteorological direction, vector conversion, and rotations.
- Air density, pressure, perturbation/absolute potential temperature, virtual
  temperature, and temperature conversion.
- Height MSL/AGL and geopotential conversion.
- Wind shear, power-law exponent, and profile fitting/interpolation.
- Friction velocity, roughness length, Monin-Obukhov length/`RMOL`, stability
  parameter, and bulk/gradient Richardson number.
- Sensible heat flux and planetary-boundary-layer profile quantities.
- Accumulated and interval precipitation.
- Radar reflectivity-to-rain-rate conversion.
- Moisture/cloud condensate diagnostics for `QVAPOR`, `QRAIN`, `QICE`, and
  `QCLOUD`.
- Circular means and directional statistics.

## `wrf_tools.les`

- Configurable U/V/W loading and native destaggering.
- Mean fields, perturbations, resolved variances, covariances, and Reynolds
  fluxes.
- Turbulence intensity by component and resultant velocity.
- Resolved TKE, SGS TKE, and total TKE.
- SGS stress-tensor loading and analysis for `m11`, `m12`, `m13`, `m22`,
  `m23`, and `m33`.
- Resolved/subfilter TKE partitioning after Butterworth or top-hat filtering.
- Horizontal/time averaging and vertical turbulence profiles.
- Momentum and heat-flux profiles, including future scalar-flux extension.
- Multi-resolution LES comparison.

## `wrf_tools.timeseries`

- Read and write WRF `tslist` definitions.
- Discover and read WRF station output families (`TS`, `UU`, `VV`, `WW`,
  `PH`, `TH`, moisture, pressure, and stress files).
- Combine station variables into labelled xarray datasets.
- Convert WRF epoch/timestamps and align multiple stations.
- Extract station time series and time-height sections.
- Resample, average, interpolate, and export station data.

## `wrf_tools.wps`

- Read namelist sections and update simulation dates.
- Read and validate `namelist.wps` domain parameters.
- Generate eta-level distributions.
- Calculate parent/child grid spacing, centres, corners, and extents.
- Lambert conformal and geographic projection helpers.
- Validate nesting ratios, parent starts, and domain containment.

## `wrf_tools.plotting`

- Horizontal scalar maps, contours, vectors, quivers, and wind barbs.
- Sea-level/model-level/pressure-level maps.
- Wind speed/direction, precipitation, reflectivity, cloud, power, terrain,
  MODIS land-use, and roughness maps.
- Vertical cross-sections of wind, reflectivity, cloud-top temperature, and
  other fields with terrain filling.
- Time series, time-height diagrams, profiles, and high-frequency LES planes.
- Nested WRF/WPS domain maps with Lambert projection labels.
- Wind roses, Taylor diagrams, spectral plots, and validation scatterplots.
- Reusable color maps, plot styling, image sequences, and animations.
- Every plotting function returns figure/axes objects and never calls `show()`
  unless requested.

## `wrf_tools.observations`

- Load generic tabular and NetCDF observations with configurable column names.
- RADAR grids and precipitation products.
- LiDAR profiles and time series.
- SCADA turbine/farm observations.
- FINO mast wind speed, direction, and temperature profiles.
- XPIA profile datasets.
- Coordinate, height, time-zone, temporal-resolution, and unit normalization.
- Collocate observations with WRF points, profiles, and grids.

## `wrf_tools.validation`

- Bias, MAE, RMSE, standard error, correlation, and normalized error.
- Circular wind-direction error and direction-aware averaging.
- Earth mover/Kantorovich transport distance.
- Distribution and spatial-field comparisons.
- Taylor-diagram statistics.
- WRF-versus-RADAR precipitation verification.
- WRF-versus-LiDAR/SCADA/FINO/XPIA profile and time-series verification.
- Resolution/case comparison, clustering, and ranking.
- Alignment reports describing dropped times, missing values, and interpolation.

## `wrf_tools.coupling.openfast`

- Map arbitrary WRF-LES plane layouts and component conventions.
- Read, write, inspect, and validate BTS full-field files.
- Read/write BL-grid and coherent-turbulence point formats.
- Read full-field text, hub-height binary, and WND inflow formats.
- Concatenate compatible TurbSim fields in time.
- Extract point time series, horizontal planes, and vertical profiles.
- Rotate horizontal and vertical velocity components.
- Compare inflow files with numerical tolerance and metadata reports.
- Generate constant, uniform, and step wind files.

## `wrf_tools.wind_models`

- Kaimal spectra, including the IEC form.
- Cheynet stability-dependent spectra.
- Von Karman spectra.
- Cross-component spectra where provided by the original models.
- IEC/exponential spatial coherence models.
- Correlated synthetic wind-field generation on arbitrary lateral/vertical
  grids.
- Deterministic random seeds and reproducible realizations.

## `wrf_tools.openfast`

- Read OpenFAST ASCII and binary channel outputs into labelled datasets.
- Resolve channel names/units and selected historical channel aliases.
- Select, compare, and plot output channels.
- PSD and spectral comparison of structural responses.
- Rainflow cycle counting and fatigue-ready cycle tables.
- Zero-crossing frequency and basic event statistics.
- Convert moments to stress using supplied section properties.
- Load/time statistics and run-to-run comparisons.
- Parse and edit relevant text input parameters where needed for
  post-processing workflows.
- Direct OpenFAST execution may be offered as an explicit helper; ROSCO tuning
  is excluded.

## `wrf_tools.reporting`

- Reproducible summaries of datasets, grids, variables, time coverage, and
  validation results.
- Export tables to CSV/NetCDF and plots to standard image formats.
- Batch case-comparison reports with provenance and configuration capture.

## CLI

- `wrf-tools discover`, `inspect`, and `validate`
- `wrf-tools extract`, `subset`, and `concat`
- `wrf-tools filter` and `spectra`
- `wrf-tools profile`, `cross-section`, and `plot`
- `wrf-tools compare` and `report`
- `wrf-tools wrf-les-to-bts`, `bts-info`, and `bts-compare`
- `wrf-tools openfast-info` and `openfast-compare`

All commands will accept configuration files as an alternative to long command
lines and will default to non-destructive outputs.

## Explicitly deferred or excluded

- COAWST functionality.
- ROSCO controller tuning.
- Concatenating different WRF domains as one time sequence.
- FAST MATLAB GUI and turbine-design GUI callbacks.
- NCToolbox and its Java/remote-catalog implementation.
- Historical FAST-version conversion internals unless required to read a
  post-processing input supplied by a user.
- Shell-based WRF/WPS/COAWST compilation and installation for this phase.
