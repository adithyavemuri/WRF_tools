# Pre-publication audit — 15 October 2026

## Current development: terrain/ocean isosurfaces and offline interaction

The post-release geometry and browser additions bring the catalog to 211 entries.
All four new functions have an execution route in the chaptered showcase, with
analytical mesh-coordinate and viewer-contract tests. See [the model-cutout guide](ISOSURFACES.md)
for dependencies, methods, terrain/ocean semantics and rendering limitations.
Initial mesh-only verification covered 201 unique tests: 200 passed in the main run with the
ledger-consistency case deferred until the new showcase ledger was copied;
all five release-consistency checks then passed, including that deferred case.
That initial showcase exercised 206 of 209 callable entries and recorded the three
external prerequisites separately, with no unaccounted entries. The seven-state
real-data Manim movie rendered at 1600x900/12 fps; the final exporter reproduced
its geometry exactly. [Render acceptance record](validation/isosurface-acceptance.json)
stores portable artifact paths and hashes. New renderer validation was local
Linux/Cairo only; it is not a claim of a completed Windows rendering test.
The report PDF and its historical acceptance record are unchanged. The figures
and counts below describe the v0.5.0 pre-release audit snapshot, not a fresh PDF
generation or a claim that every new branch has atmospheric validation.

The subsequent browser example is a separate, self-contained offline HTML file.
It uses all saved mass levels by default and records model-top interfaces and
pressure separately from a selected display ceiling. Terrain is a static,
opaque, ambient-lit mesh; only wind/TKE meshes appear in animation frames.
Real offline Chrome checks passed mouse rotation, wheel zoom, time selection,
camera and opacity persistence, terrain-only selection and unchanged physical
coordinates under aspect-ratio changes, with no external HTTP requests or
JavaScript page errors. The HTML commits the live WebGL camera before control
updates because wheel zoom can precede Plotly's stored-layout camera update.
Earlier browser/launcher verification covered 217 unique tests: 216 passed in the main run,
then the deferred ledger check passed with the five release-consistency tests.
The refreshed showcase exercised 208 of 211 public functions with the same
three explicit external prerequisites. [Browser acceptance record](validation/interactive-acceptance.json)
stores final geometry/HTML hashes, actual vertical extent and interaction checks.
The updated viewer was also tested with WebGL explicitly disabled: it displayed
actionable graphics instructions, skipped Plotly initialization, and produced
no JavaScript page errors. Launcher tests verify a separate temporary profile,
explicit software opt-in, local-file validation, and no sandbox-disabling flags.
No real browser preferences or system graphics settings are modified by these
package changes; software rendering is not automatically enabled.

### Diagnostic selector and native vertical sections

The subsequent diagnostic-viewer update keeps 211 public functions, extending
the existing exporter with an optional schema-v2 bundle. The original scalar
schema-v1 exporter and Manim workflow are retained. Wind speed, W, radial
relative vorticity, Q and supported model TKE have explicit definitions, units,
fixed per-field thresholds and fixed section colour limits across exported
times. Missing variables disable individual selections with reasons; bad data
and resource limits fail visibly. Sections follow actual sampled mass heights.

Q/vorticity reconstruction uses a full native-grid physical-coordinate Jacobian
on a spherical Earth and rotates the local wind basis before differentiating.
This is not the existing nominal-Cartesian report helper, not WRF's exact
discrete operator, and not a turbulent-flux or energy budget. Independent tests
recover general affine tensors on sloping grids and through the complete
spherical/wind-rotation chain, and distinguish solid rotation, strain, shear
and uniform translation. See [methods and limits](ISOSURFACES.md).

Local verification now covers **238 unique tests**: 237 passed in the main run
and the deferred checked-ledger test then passed with all five release
consistency checks. The updated showcase executes both geometry schemas and
accounts for 208 of 211 public functions plus the same three external actions.
The real seven-state d02 export was checked in offline, isolated Chrome with
explicit software WebGL: all four available fields at all seven times,
mouse orbit/zoom, fixed terrain/camera/opacity, invariant physical heights,
both section orientations and the section-only view passed. No external HTTP
requests or JavaScript page errors occurred. TKE was explicitly unavailable
in this real run. The [acceptance record](validation/diagnostic-viewer-acceptance.json)
stores hashes and scope. Browser/platform coverage remains local Linux/Chrome,
not a cross-platform graphics certification. The retained PDF is unchanged.

The layout follow-up separates controls, plot and footer into normal-flow rows
instead of overlaying fixed bars on Plotly's paper-relative legend. An offline
browser regression passed at 1600x1000, 1280x720, 900x700, 1920x1080 and
2560x1440, with methods expanded and collapsed: controls/plot/footer and
legend/tools bounding boxes did not overlap. All prior diagnostic interaction
checks passed again. The full 237-test run and subsequent deferred ledger check
passed again (238 unique tests). Only presentation changed; saved geometry,
field calculations and the report PDF are unchanged.

The View selector also offers **Terrain + surfaces only**. The browser
regression verifies that this keeps terrain/coastline and diagnostic meshes
visible while hiding the section, including after a time redraw. This is a
visibility-only option; no geometry or diagnostic values are recalculated.

The browser height-window follow-up adds lower/upper MSL limits, full-export
restoration and optional vertical auto-fit that reports the actual exaggeration.
Existing triangles and coastline segments are geometrically clipped without
adding caps; section values are interpolated only within saved column brackets
at the bounds. Saved geometry/volumes and diagnostic calculations are unchanged.
Offline Chrome checks passed independent triangle, line and section oracles,
clipping across all four available fields at first/last times, camera retention,
invalid-range rejection and exact terrain restoration. All prior interaction
and five-size layout checks passed again. The 237-test main run and subsequent
checked-ledger release checks passed again (238 unique tests). These are display
and numerical-contract checks, not validation of unresolved turbine wakes or
parameterized turbulence.

Pre-push verification reran the complete suite in one pass: **238 tests passed**,
including the checked source/capability ledger, followed by a successful core
dependency check. Generated HTML, geometry, videos and browser screenshots
remain ignored local artifacts; reusable examples and acceptance records are
included in the source update.

## v0.5.0 pre-release audit snapshot

This is a source, documentation, numerical-regression and runnable-example
audit. It is **not** certification, exhaustive branch coverage, validation of
every possible WRF configuration, or proof of atmospheric/engineering accuracy.
The package remains beta. This audit is included in the v0.5.0 update.

Verification snapshot: **177 tests passed locally** on Linux/Python 3.10, including
the complete showcase and observation-file workflow. A wheel was built, installed
under a temporary user-space target, and its 207-capability catalog imported
separately from the editable checkout. CI is configured for Linux/Windows and
Python 3.10/3.12; those remote matrix runs have not been performed here.

## Capability accounting

The audited release catalog contained **207 public top-level functions** (not 207
independent physical models). Facade re-exports do not count twice. Every entry
has an execution route, method category, references/format contracts and caveat.
Private helpers, data classes/methods and orchestration infrastructure are not
part of that number; the remaining data classes are used by executable examples.

The [complete showcase](../examples/showcase_all_capabilities.py) has four
readable chapters and records actual runtime function entries. The checked
[ledger](validation/capability-coverage.md) accounts for all entries:

| Status | Count | Meaning |
|---|---:|---|
| `EXERCISED_SYNTHETIC` | 204 | Entered during successfully completed labelled synthetic chapters |
| `REQUIRES_EXTERNAL_INPUT` | 3 | Explicitly not run without real prerequisites |
| `UNACCOUNTED` | 0 | A future unaccounted entry fails the showcase/test |

The three external operations are Natural Earth download, actual `wgrib2`
conversion and a real OpenFAST turbine-model execution. The showcase does not
replace them with fake executables. Their runnable API/command and prerequisites
are included in the ledger. The JSON ledger includes a package-source hash.

Runtime entry counts are not assertions for every input/branch. Independent
analytical/oracle tests provide separate numerical evidence. Synthetic parser
fixtures and read/write self-round trips do not establish interoperability with
every external application/version.

## Corrections made

| Area | Finding and correction | Regression evidence |
|---|---|---|
| Comparisons | Pearson/normalization used inconsistent missing-value sets; silent broadcasting could pair the wrong samples. All deterministic pair scores now share finite pairs and enforce equal shapes. | Pairwise/axis/missing-value tests |
| Distribution distance | Quantile-grid approximation was labelled empirical Wasserstein-1. Replaced by exact empirical CDF integration, including unequal lengths. | Compared with SciPy `wasserstein_distance` |
| Fourier coarsening | FFT crop origin/parity mishandled odd/even grids and Nyquist merging. Replaced by correctly normalized separable Fourier resampling. | Odd/even/factor cases against SciPy `resample`; mean preservation |
| Spectra | Odd-length cross-periodogram, final log/radial bin inclusion and invalid segment settings needed correction. Zero-power coherence is undefined (NaN), not an invented value. | Cross/auto equality, Parseval, Welch/coherence against SciPy with identical windows |
| Kaimal components | Vertical component used the u/v denominator form. Corrected to the explicit Risø-R-1506 Eq.4.5 variant, with the distinct vertical denominator and coefficient. | Explicit published-equation checks; variant/reference documented |
| Humidity/stability | Dew-point inverse and RH coefficients differed; missing stability became neutral, and zero-flux limits were inconsistent. Inverse Bolton fit is now consistent; missing/neutral are distinct. | Saturation inversion and neutral/missing-limit tests |
| Stull partial budget | Negative axis indexes and vertical-height broadcasting were not handled robustly. Normalized axes, validated shapes/heights and added known sign/value tests. | Analytical shear/buoyancy/TKE example |
| Rotor approximation | Missing rotor coverage could silently contribute a partial average. Incomplete profiles now return NaN. Uniform-height approximation remains explicitly labelled. | Incomplete-coverage regression |
| WRF constants/timing | Geopotential reconstruction used generic rather than WRF gravity; standalone reports could imply ERA5 forcing without evidence, and counts conflated files/timestamps. Corrected gravity, provenance/timing and separate counts. | WRF-constant, sequence and multi-time showcase tests |
| I/O/resources | One-dimensional/Unicode Times escaped sequence validation; vertical-grid mismatch was not rejected; some failed opens/subsets could leak datasets. Unified timestamp validation and explicit close ownership. | Duplicate/vertical-grid and selected-data tests |
| Namelist/grid selection | Quoted paths containing `/`, inline assignments/comments and D exponents were mishandled. Parser now handles its declared simple subset, rejects unsupported indexed/repeat syntax. Regridding/transects no longer silently extrapolate/clip. | Quoted-path/comments/exponent and bounds tests |
| Inflow files | BTS validation checked velocities but not all advertised metadata. Now checks metadata too; invalid dimensions/scales and short payloads fail. WindField rejects empty/nonfinite grids. | Metadata/round-trip tests and format chapter |
| Other edge cases | Single-row CSV/OpenFAST ASCII, plateau/empty rainflow and constant Weibull cases needed handling. Rainfall-counter resets are retained and flagged rather than clipped into invented totals. | Edge-case, parser and reset tests |
| Numerical settings/counts | A temporal spacing argument was unused; it now supplies explicit increment rates. Constant-series ramps and finite land-use counts are corrected. WPS Lambert geometry now uses the declared WRF sphere rather than an implicit WGS84 ellipsoid. | Rate/constant/missing-count and spherical-corner regressions |
| Maps | Every plot could re-read/export whole-world geometries. Cached geometry is clipped to map extent before rendering; map limits are set first. Cache-only policy is available. | Existing geographic plot tests, regenerated real report and visual inspection |
| Packaging | The dependency-file route omitted Cartopy/Pillow/Python-3.10 TOML support. Requirements and environment diagnostics now match the advertised examples. | Editable/package-install checks; CI targets Linux/Windows, Python 3.10/3.12 |

## Scientific traceability

See [SCIENTIFIC_METHODS.md](SCIENTIFIC_METHODS.md) and every entry in
[API_CATALOG.md](API_CATALOG.md). Important primary checks include:

- [Hunt, Wray and Moin (1988)](https://ntrs.nasa.gov/citations/19890015184)
  for the Q definition; direct chapter citation replaces the broader volume ID.
- [Deardorff (1970)](https://journals.ametsoc.org/view/journals/atsc/27/8/1520-0469_1970_027_1211_cvatsf_2_0_co_2.xml)
  for the corrected convective-scale DOI (`CVATSF`, not `CCOTLL`).
- [Wagner et al. (2014), publisher-version copy](https://backend.orbit.dtu.dk/ws/portalfiles/portal/93592493/Rotor_equivalent_wind_speed.pdf)
  for rotor-equivalent speed; correct author order and explicit difference
  between the paper's area weights and this package's height-weighted approximation.
- [Risø-R-1506(EN), Eq.4.5](https://backend.orbit.dtu.dk/ws/files/7702984/ris_r_1506.pdf)
  for the declared near-neutral Kaimal coefficient/denominator variant.
- Official SciPy references for [resampling](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.resample.html),
  [coherence](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.coherence.html)
  and [empirical Wasserstein distance](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wasserstein_distance.html).

Heuristic PBL, jet, stability, ramp and QC thresholds are not claimed as universal
laws. Simplified theta-e is not Bolton's full formulation. Q uses a labelled
nominal Cartesian approximation, not a full metric-aware WRF operator. Partial
Stull budgets omit transport, pressure, dissipation and SGS closure terms.

## Real WRF verification

The existing Netherlands `full-test-001` output was reused: seven hourly states
for each of d01 (9 km) and d02 (3 km). No new WRF simulation was needed.
Five connected groups complete for each domain. Time-averaged turbulence is
explicitly unavailable because the hourly data are unsuitable; model TKE is
absent. The synthetic showcase separately exercises those conditional paths.
The [PDF](../example_results/final-report/hindcast-report.pdf) and preview are regenerated,
not the superseded September report. Technical success is not atmospheric validation.

## Observations: what is and is not supplied

- Generic CSV/NetCDF loading, fixed-offset UTC normalization, nearest spatial
  selection, explicit time-tolerance matching, finite-pair scores and plots.
- [compare_observations.py](../examples/compare_observations.py) accepts actual
  user CSV, writes matched data/counts/JSON/scatter, and has a synthetic regression
  test with an unmatched timestamp. It never manufactures real observations.
- No native instrument decoder, calibration/QC, footprint/height conversion,
  uncertainty model or completed real-observation validation is supplied.
  The researcher must establish matching units, height and averaging conventions.

## Cleanup and compatibility

Removed the obsolete one-file “all capabilities” script, its five older
PDF/PNG products and the overstated expansion-plan document. Replaced their
README links with the chaptered showcase/current evidence. These tracked files
remain recoverable from existing Git history; no destructive Git reset was used.
Removed unreferenced `WRFSource`/`ExecutableConfig` placeholders and an unused
exception subclass. Their unsupported import paths are intentionally retired.

The old slideshow remains removed; the newer actual-WRF 3-D contour exporter,
Manim scene and rendered movie are retained. Other repositories, installed WRF
binaries, source model, ERA5/geodata and simulations were not changed.

The public callable count remains 207. Some numeric results/edge-case behavior
intentionally change where bugs were corrected. Run the examples/regressions
again before reusing old numerical outputs. Source changes have not been pushed.

Every public function now has its own docstring as well as its catalog method
basis; a regression rejects undocumented entries. Readers/writers use format
contracts and numerical utilities use documented algorithms rather than invented
scientific-paper claims. The generated API catalog is refreshed from this source.

## Repeat audit: additional findings and corrections

The earlier 111-test baseline passed before this pass. A passing baseline did
not establish correctness for the following previously uncovered cases. Twenty-two
additional regressions/hygiene checks now cover them; the complete suite passes
133 tests. The public function count remains 207 (new shared helpers are private).

| Finding | Correction and evidence |
|---|---|
| Uneven vertical levels | Replaced ratios of index gradients with nonuniform three-point physical-height derivatives in N/N², inversion flags and partial TKE shear production. Quadratic profiles match analytical interior derivatives and NumPy's independent implementation. Shared 1-D and co-located height arrays are supported. |
| Integral time scale | Include the linearly interpolated first zero crossing in the integral instead of dropping the last positive interval. An analytical two-sample triangle verifies the result. |
| Missing rainfall and report bypass | Missing/nonfinite counters cannot produce partial period totals. Reports now use the same reset-aware function as the API, mask affected map cells, label raw affected site traces, and show coverage/reset/missing counts in the PDF. RAINC/RAINNC resets are checked separately, so growth in one cannot hide a reset in the other. Unsigned counters are converted before differencing to avoid integer wraparound. |
| Turbulence shape/averaging | Resolved components/covariances reject silent broadcasting; optional SGS energy must already be averaged on the same window/axes and match the reduced shape. Zero-mean TI is NaN. Invalid budget axes and one-time budgets are rejected. |
| Undefined/invalid statistics | Opposing/zero-weight circular means return NaN; negative circular weights and shape-mismatched direction errors fail. Unavailable scores cannot be ranked. K-means rejects invalid inputs/iteration counts and returns labels consistent with its final centers. |
| Observation times and metadata | Explicit ISO timezone offsets normalize to UTC; combining aware times with another fixed offset fails. NaT, undecoded numeric offsets and duplicate/unordered matching indexes fail visibly. The real-observation example now records units, height and matching policy in its paired NetCDF. |
| Uniform OpenFAST wind | Corrected the four-column writer to all eight documented WindType=2 columns; added editable shear/gust inputs and finite/increasing-time checks. Direction convention is explicit. This is a format-contract regression, not an OpenFAST execution test. |
| von Karman transverse energy | Corrected transverse prefactor 4 to 2: numerical integration previously returned about twice the specified variance. Integrals now match sigma² within documented coefficient rounding. Removed the incorrect blanket 2019-IEC reference; TurbSim describes this legacy family against edition 2. |
| Coherence convention | The exponential model is explicitly root coherence, unlike the magnitude-squared estimator. Spectral models now reject nonfinite/nonphysical parameters. |
| Stale scripts and future drift | Removed `scripts/audit_all_capabilities.py`, which imported deleted classes and asserted version 0.2.0. The maintained chaptered showcase replaces it. Single-file smoke checks no longer advertise one-timestamp variance as LES evidence; placeholder BTS metadata is explicit. Added automated package-import, local-document-link, generated-catalog and checked-ledger consistency checks. |

The new regressions are in [test_repeat_audit.py](../tests/test_repeat_audit.py)
and [test_release_consistency.py](../tests/test_release_consistency.py).
Updated primary/algorithm references are in [the methodology ledger](SCIENTIFIC_METHODS.md)
and the generated API guide. The real Netherlands report and all four showcase
chapters were rerun. Five real-data groups complete per domain; temporal
turbulence remains unavailable for hourly output. The newer contour/Manim
example remains retained; only an unused import was removed from its scene.

The obsolete tracked audit script is recoverable from Git history. The previous
generated showcase was temporarily retained during that earlier pass. Those
temporary copies and superseded PDFs are now deleted, not shipped as archives.
No model binaries, simulation inputs/outputs, external tool
installations, other repositories, commits or remote repositories were changed.
This remains a bounded audit, not an assurance that no unknown defects exist.

## Scientific release gate and clean report

The [calculation change record](CALCULATION_CHANGES.md) compares the committed
Python baseline with this working version. The printed TurbSim page
was visually checked; the function now follows Eqs.27–28 literally (71/189,
transverse prefactor 2), with closed-integral rounding differences documented.
Independent release-gate tests check Parseval, short/odd/even/DC/Nyquist PSDs,
complex cross-spectrum phase, Welch on multiple axes, known Butterworth gains,
mean/mode conservation, Reynolds identities, rotation invariance, a general
affine Q tensor, physical units and pressure-consistent surface heat flux.

The reference to an absent migration-input folder was removed from public
documentation. A test rejects machine-specific home paths in publication text;
catalog paths and source hashes use portable slash conventions.

Only one current real-data report PDF is retained. Full reports request PNG/SVG
companion figures, not per-figure PDFs. Standalone figure APIs still offer PDF
export when explicitly requested. Superseded reports, generated showcase data,
temporary backup trees and stale build products are deleted, not archived into
the release. No simulation inputs or outputs are deleted.

The documented report example is executed in a fresh output directory as the
final integration gate. Its final PDF is not manually assembled or repaired.
The result passed: 175 pre-render tests and two post-render source/documentation
checks, 177 total. The example exited successfully on its first clean run,
without code changes or PDF repairs. Both domains contain seven actual output
states; five diagnostic groups complete and hourly temporal turbulence remains
explicitly unavailable. [Acceptance record](validation/final-report-acceptance.json)
stores the portable command, package-source and final-PDF checksums from that
pre-release run. The retained PDF was generated with v0.4.0 metadata before the
release version update; it is not relabelled as a v0.5.0-generated artifact.
The capability ledger is refreshed against the v0.5.0 package source.

Deleted outputs: the old generated showcase (including its copy-operation demo
folder), visualization-upgrade report tree, earlier demo PDF/preview and both
temporary showcase backups. Old wheel/install copies and stale build products
were removed. A fresh preview was copied from the final run; no PDF copy or
old-code archive is retained. The newer Manim contour movie remains local.

Environment note: an isolated warning-as-error diagnostic reproduces the known
netCDF4 1.7.4 NumPy-array-size import warning. Normal numerical/I/O tests pass;
this is recorded rather than globally suppressed. The upstream discussion and
fix are [Unidata #1354](https://github.com/Unidata/netcdf4-python/issues/1354)
and [#1471](https://github.com/Unidata/netcdf4-python/pull/1471). Dependency
availability and runtime-entry coverage remain distinct from scientific evidence.
