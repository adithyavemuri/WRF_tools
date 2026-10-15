# Calculation changes and release boundary

Baseline: committed Python revision `244c252`. This record describes this package's
changes, including earlier audits, included in the v0.5.0 beta update.

## Spectra: exact changes

For von Karman, let `x=f L/U` and `A=sigma² L/U`:

| Component | Committed Python baseline | Current declared equation |
|---|---|---|
| u | `4 A/(1+70.8 x²)^(5/6)` | `4 A/(1+71 x²)^(5/6)` |
| v/w | `4 A (1+188.4 x²)/(1+70.8 x²)^(11/6)` | `2 A (1+189 x²)/(1+71 x²)^(11/6)` |

The current equation is transcribed from the **visually inspected**
[TurbSim v2 guide, printed p.41, Eqs.27–28](https://openfast.readthedocs.io/en/main/_downloads/cb14d3e2d3533d76e405d730fea19846/TurbSim_v2.00.pdf).
It is a legacy IECVKM equation, not a claim about the 2019 IEC standard. The
longitudinal length parameter is common to the component equations; `sigma`
is the selected component's nominal standard deviation. Frequency is Hz and
the PSD is one-sided. No implicit angular-frequency conversion is applied.

The immediately preceding audit corrected the transverse prefactor but retained
70.8/188.4. This pass uses the literal 71/189 printed in the selected reference
instead of presenting a mixed coefficient convention as a faithful transcription.
Closed beta-function integrals give `0.9984504024 sigma²` (u) and
`0.9970441343 sigma²` (v/w). These differences are explicit, not silently forced
to one. Tests check point values, exact versus numerical integrals, amplitude
scaling, frequency units and asymptotic slope. This model is not used to compute
the wind/resource statistics in the real-data hindcast PDF.

For the separate near-neutral Kaimal helper, the previous Python w component
was `2/(1+5.3 n)^(5/3)`. The declared
[Risø-R-1506 Eq.4.5](https://backend.orbit.dtu.dk/ws/files/7702984/ris_r_1506.pdf)
variant is `2.1/(1+5.3 n^(5/3))`; that was a calculation change, not just a label.
Published Kaimal variants are not asserted interchangeable. Cheynet's coefficient
table/composite equations and IEC longitudinal Kaimal equation were **not**
changed by this audit; their input validation was tightened.

## Other computational changes

| Area | What changed and why | Evidence / remaining limit |
|---|---|---|
| Periodogram/Welch | Standard estimator retained; invalid rates/segments rejected. | SciPy for odd/even/short records and multiple axes; Parseval identity. |
| Cross-spectrum | Correct odd final-positive-bin doubling; preserve even Nyquist. | SciPy CSD oracle with opposite phase convention explicitly conjugated. |
| Coherence/bins | Zero-power coherence becomes NaN; include highest log/radial bin. | Same-window Welch/coherence oracles. Exponential model is root, not squared, coherence. |
| Fourier downsampling | Replace FFT crop/parity handling with normalized resampling/Nyquist merging. | SciPy resample, mean conservation and retained-mode amplitude. Periodic assumption remains. |
| Butterworth/top hat | Core transfer/block-mean formulas retained; settings validated. | Half-power cutoff, low/high energy complement and complete-block mean conservation. |
| Q | Correct gradient tensor column order to x,y,z. | General affine tensor, solid rotation, pure strain. Uniform Cartesian coordinates only. |
| Vertical derivatives | Nonuniform physical-height differences replace index-gradient ratios in N/N², inversions and partial-budget shear. | Uneven-grid polynomial and analytical budget tests. No moving-coordinate budget. |
| Surface-flux report | Convert sensible temperature flux to potential-temperature flux with theta/T before virtual correction. | Independent dry energy-flux equation at several pressures. Condensate/higher-order terms omitted. |
| Integral scale | Include interpolated first-zero-crossing triangle. | Analytical crossing; biased ACF and finite-record truncation explicit. |
| WRF height | WRF gravity 9.81 replaces generic standard gravity in reconstruction. | Known geopotential, face averaging and AGL/MSL tests. Generic physics retains 9.80665. |
| Dew point | Make inverse coefficients consistent with liquid-water saturation fit. | Saturation inversion; not an ice formula. Simplified theta-e remains approximate. |
| Rain | Retain resets, prevent unsigned wrapping, reject missing totals and detect each counter's resets. Report uses the same function. | Known differences, reset/missing masks and coverage. No bucket reconstruction. |
| Resolved/SGS energy | Reject shape broadcasting; SGS must already be averaged consistently. | Reynolds identities, horizontal rotation invariance. No implicit SGS/sign inference. |
| Rotor mean | Incomplete rotor coverage cannot supply a partial mean. | No-extrapolation regression. Existing 41-height cube mean retained, **not** disk-area REWS. |
| Paired scores | Common finite-pair mask/shape checks; exact empirical Wasserstein replaces quantile approximation. | SciPy Wasserstein and analytical scores. No uncertainty/QC inferred. |
| Circular scores | Opposed/zero-weight resultant becomes NaN; direction-error shapes checked. | Weighted/wrapped tests. Missing values are not measurements. |
| Other statistics | Handle constant Weibull limit, final k-means labels, undefined ranks and plateau rainflow. | Explicit edge cases; thresholds/fits remain screening estimators. |
| Interpolation | No missing-value bridging or folded-profile sorting; monotonic pressure reversal allowed. No silent clipping/extrapolation. | Analytical interpolation and rejection tests. Not conservative remapping. |
| Spatial summaries | Correct finite land-use counts; use supplied temporal spacing for rates. | Count/rate/constant tests; thresholds remain heuristic. |
| WPS corners | Use declared spherical WRF Earth rather than implicit ellipsoid. | Independent projection calculation. Centred Lambert assumptions remain. |
| Inflow formats | All eight uniform-wind columns; strengthen BTS metadata checks. | Format/round-trip tests, not real turbine execution or universal interoperability. |

Reader ownership, namelist parsing, plotting, metadata and output-format changes
are recorded in [the audit](AUDIT.md), not presented as new physical theory.
The [catalog](API_CATALOG.md) includes every public function. Runtime-entry
accounting is separate from numerical verification.

## What passing means

Tests verify selected equations, conventions and identities. Producing a PDF is
an integration test, **not** proof of atmospheric realism. Remaining limitations
include nominal-metric Q/terrain derivatives, approximate thermodynamics, partial
dry budgets, height-weighted rotor screening and no completed observation
validation. No zero-bug guarantee is claimed.
