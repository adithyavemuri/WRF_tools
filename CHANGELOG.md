# Release notes

## Unreleased

- Add an editable MSL height window with geometric surface/terrain/coastline
  clipping, bracketed section interpolation at the bounds, full-export reset
  and optional vertical auto-fit with explicitly updated exaggeration.
- Add a **Terrain + surfaces only** view that hides the vertical section while
  retaining the terrain, coastline and selected diagnostic isosurfaces.
- Fix diagnostic-viewer text overlap by giving controls, plot and footer
  separate responsive layout rows. Browser checks cover five window sizes,
  with the methods panel both expanded and collapsed; calculations are unchanged.
- Extend the offline viewer with a per-field diagnostic dropdown (wind speed,
  W, vertical relative vorticity, Q and available model TKE) and movable native
  x-z/y-z sections. Derivatives use full-grid spherical-coordinate Jacobians
  and rotated wind, with analytical tensor tests and explicit reconstruction
  limits. Schema v1 and existing Manim exports remain supported. Missing fields
  are disabled; thresholds and section colour ranges stay fixed across time.
- Explain unavailable WebGL before the browser plot initializes, and add a
  local-file launcher with an explicit isolated-profile software-rendering
  option. Normal browser settings and scientific calculations are unchanged.
- Add terrain-aware wind/TKE isosurface geometry, a separate Manim model-cutout
  scene with WRF terrain and ocean, editable examples and analytical mesh tests.
  The optional `isosurface` extra supplies mesh extraction dependencies; the
  offline interactive HTML viewer adds manual camera, actual-time, opacity and
  vertical-scale controls with an invariant terrain layer. Full-column exports
  distinguish the display height from the actual model top. The complete
  showcase now accounts for 211 public functions.
- Fix Windows test failures by explicitly reading UTF-8 source and API
  documentation. The discovery test now also simulates the Windows legacy
  CP1252 default on Linux to catch this regression before publication.
- The Windows encoding correction itself does not change package calculations,
  report artifacts or released tags.

## 0.5.0 — 2026-10-15

Beta update focused on connected workflows, explicit scientific conventions,
and reproducible examples. This is not scientific certification.

### New and connected workflows

- A catalog of 207 public top-level functions, executable TOML recipes and a
  chaptered showcase that records which functions actually run.
- Selectable diagnostic groups in hindcast reports, with separate domain
  results, maps, wind profiles, precipitation, model TKE when available, and
  explicit messages when sampling or variables are unsuitable.
- Editable examples for weighted horizontal, selected-area, vertical and time
  means; model-level versus common-height averaging is an explicit choice.
- Multi-simulation alignment, scores and comparison plots; observation-file
  loading, time matching and comparison examples.
- Wind animations and actual-data 3-D contour export with a Manim scene.
  Manim remains an optional installation; it is not required for core analysis.
- A single real-data example PDF, API catalog, scientific-method references
  and per-capability execution ledger.

### Numerical corrections

Some results intentionally differ from 0.4.0. The
[calculation change record](docs/CALCULATION_CHANGES.md) gives equations,
references, regression evidence and remaining approximations. Changes include:

- Transverse von Karman spectrum normalization and literal TurbSim constants;
  the declared near-neutral vertical Kaimal variant.
- Odd-length cross-spectra, Fourier resampling/Nyquist handling, spectral bins,
  undefined coherence and invalid sampling settings.
- Q gradient ordering, nonuniform-height derivatives, pressure-consistent
  surface heat-flux conversion and consistent saturation/dew-point inversion.
- Missing-value handling, paired statistical scores, empirical Wasserstein
  distance, precipitation resets and incomplete rotor/interpolation coverage.

These spectrum helpers are not used to calculate the wind/resource statistics
in the retained real-data hindcast PDF. Scientific corrections should not be
interpreted as measured atmospheric improvements.

### Compatibility and cleanup

- Superseded demonstration scripts, unused internal configuration code and old
  generated reports are removed, not retained in an archive.
- Use [the example guide](examples/README.md) and
  [connected workflows](docs/CONNECTED_WORKFLOWS.md) instead of the removed
  `single_wrf_all_capabilities.py` and audit script.
- Invalid inputs that previously produced misleading results may now raise an
  error or return explicitly undefined values. Check the declared convention
  when comparing results with earlier versions.
- Reports read the package version for new provenance instead of a fixed label.

### Verification and limits

- Pre-release checks: 177 tests passed locally, including the runnable showcase
  and numerical identities/library comparisons. Linux/Windows CI is configured
  separately; local results do not certify the remote platform matrix.
- Showcase: 204 functions exercised with labelled synthetic inputs; three
  operations require external prerequisites (map download, wgrib2, OpenFAST).
- The real-data two-domain example ran from a clean output directory without
  manual PDF repair. Its PDF and acceptance record retain their original
  v0.4.0 generation metadata; they are not regenerated for the release label.
- No real-observation validation or complete external turbine-model execution
  is claimed. Hourly model output does not support temporal turbulence
  statistics. See [the audit](docs/AUDIT.md) for the full verification boundary.
