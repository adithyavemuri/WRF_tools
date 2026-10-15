# Scientific methods and references

This page is the methodology ledger for `wrf-tools`. Equations use SI units
unless a function docstring says otherwise. References are attached to the
implementation docstrings as well as collected here so that analyses can cite
the original method, not merely this software.

## Report figures and their verification

The report's wind overview records the selected source filenames, times, site,
section, units, coordinate conventions, colour limits and references in a JSON
sidecar. The same definitions appear in the PDF methods appendix. See
[Scientific figures and animations](VISUALIZATION.md) for the processing and
verification contract.

The overview and report profile reconstruction use WRF `g=9.81 m/s²` and dry
`Rd/cp=2/7`, following
[WRF module_model_constants.F](https://github.com/wrf-model/WRF/blob/v4.7.1/share/module_model_constants.F).
References document the method; analytical numerical checks and output checks
verify its implementation. They do not validate the input meteorology.

## Explicit averaging

The [averaging example](../examples/average_wrf_fields.py) exposes uniform-cell,
cell-area, layer-thickness and equal-time-sample reductions. A weighted mean is
`sum(w*f)/sum(w)` over finite selected samples, with the same validity mask in
both sums. Cell areas are `DX*DY/MAPFAC_M**2` on supported conformal grids.
Layer weights are the thickness overlapping the requested physical bounds;
partially intersected layers are not assigned their entire thickness. Field
values are assumed layer representative, not an exact continuous integral.
Columns only partially covering a requested layer contribute their available
overlap; inspect coverage for your study.

Native-level and physical-height means are different operations. Common-height
profiles interpolate each column before averaging; native-level profiles retain
index labels. Time means are explicitly equal-sample, with a warning for irregular
timestamps. They do not infer duration weights or fill gaps. Maps and profiles
can result from multiple successive means; their order is recorded in the
example and [guide](COMPARISON.md). Saved means are not sufficient to reconstruct
variance, covariance or resolved TKE from fluctuating fields.

## WRF state reconstruction and atmospheric diagnostics

Model TKE now has explicit QKE/2, TKE_PBL and dynamics-TKE handling, interface
collocation, missing-output status and negative-value reporting. See
[TKE guidance](TURBULENCE.md) before interpreting plots as evidence of energy
injection. The existing partial `tke_budget` helper is not a closed budget.
Each callable also has a method category, primary/reference documentation and
applicability warning in the generated [API catalog](API_CATALOG.md). Numerical
and file utilities cite their numerical/format contracts; they are not given
invented atmospheric citations. Empirical thresholds are labelled heuristics.
See [the audit](AUDIT.md) and the complete runtime showcase ledger for evidence.

The Cartesian Q-criterion gradient-order defect was corrected and tested on
solid rotation/pure strain; native terrain-following metrics remain outside
that helper's assumptions. The [exposure audit](CAPABILITY_EXPOSURE.md) records
which existing functions do not have a tested report workflow.

| Capability | Method | Primary reference |
|---|---|---|
| Potential temperature, pressure, geopotential height, destaggering | WRF perturbation variables and Arakawa C-grid conventions | [WRF-ARW Technical Note v4](https://www2.mmm.ucar.edu/wrf/users/docs/technote/v4_technote.pdf), doi:10.5065/1dfh-6p97 |
| Virtual temperature and density | Moist ideal-gas relations | [Stull (1988)](https://doi.org/10.1007/978-94-009-3027-8) |
| Bulk Richardson number, friction velocity, Monin-Obukhov length, logarithmic wind profile | Surface-layer similarity relations | [Foken (2006)](https://doi.org/10.1007/s10546-006-9048-6) |
| Convective velocity scale | `w* = [(g/theta_v) (w'theta_v')_0 z_i]^(1/3)`; the heat flux input is kinematic (K m s-1) | [Deardorff (1970)](https://doi.org/10.1175/1520-0469(1970)027%3C1211:CVATSF%3E2.0.CO;2) |
| Brunt-Vaisala frequency | `N2 = (g/theta) dtheta/dz` | [Stull (1988)](https://doi.org/10.1007/978-94-009-3027-8) |
| Equivalent potential temperature | Simplified screening approximation `theta exp(Lv r/(cp T))`, not the full Bolton parcel formulation | [Bolton (1980)](https://doi.org/10.1175/1520-0493(1980)108%3C1046:TCOEPT%3E2.0.CO;2) |
| Reflectivity-rain rate | Default `Z = 200 R^1.6` | [Marshall, Hitschfeld and Gunn (1955)](https://doi.org/10.1175/1520-0469(1955)012%3C0322:AOTDOP%3E2.0.CO;2) |

Vertical gradients use each column's physical spacing, including uneven WRF
levels: three-point nonuniform interior differences and first-order edges,
following [NumPy's documented finite-difference weights](https://numpy.org/doc/stable/reference/generated/numpy.gradient.html).
This is not `gradient(field)/gradient(height)`, which is inaccurate for curved
profiles on uneven levels. Shared 1-D and co-located increasing heights are
supported. The partial TKE budget differentiates time-mean columns; it does
not supply moving-coordinate budget corrections.

Rainfall period totals are unavailable at cells with any reset or nonfinite
counter sample, even when the final counter exceeds its initial value. Reports
show the valid-cell fraction and affected counts; remaining-cell averages are
not claimed as full-domain totals. Bucket/restart reconstruction is not supplied.

## Turbulence, spectra, and wind energy

| Capability | Method | Primary reference |
|---|---|---|
| Resolved TKE and Reynolds fluxes | Reynolds decomposition; `TKE = 0.5 (u'u' + v'v' + w'w')` | [Pope (2000)](https://doi.org/10.1017/CBO9780511840531) |
| Q criterion | `0.5 (||Omega||² - ||S||²)` on a uniform Cartesian grid; positive rotation-dominated regions | [Hunt, Wray and Moin (1988)](https://ntrs.nasa.gov/citations/19890015184) |
| Periodogram and Welch PSD | One-sided Fourier density; Hann-windowed segment averaging | [Welch (1967)](https://doi.org/10.1109/TAU.1967.1161901) |
| Magnitude-squared coherence and cross-spectrum | `|Pxy|2/(Pxx Pyy)` and `X conj(Y)` | [Bendat and Piersol (2010)](https://doi.org/10.1002/9781118032428) |
| `-5/3` reference slope | Inertial-subrange similarity law; plotted only as a slope guide, never as proof of an inertial range | [Kolmogorov (1941), English translation](https://doi.org/10.1098/rspa.1991.0075) |
| Kaimal component spectra | Explicit near-neutral variant: u=102, v=17, w=2.1; vertical denominator `1+5.3 n^(5/3)` differs from u/v | [Risø-R-1506(EN), Eq.4.5](https://backend.orbit.dtu.dk/ws/files/7702984/ris_r_1506.pdf); underlying [Kaimal et al. (1972)](https://doi.org/10.1002/qj.49709841707) |
| Cheynet marine spectra | Pointed-blunt composite model (Eq. 26) and stable approximation (Eq. 28), using the author-supplied 81.5 m coefficient table for `-2 <= zeta < 2` | [Cheynet, Jakobsen and Reuder (2018)](https://doi.org/10.1007/s10546-018-0382-2) |
| IEC Kaimal longitudinal model | Engineering spectrum, not coherent-field generation or certification | [IEC 61400-1:2019](https://webstore.iec.ch/en/publication/26423); [TurbSim guide Eq.23](https://openfast.readthedocs.io/en/main/_downloads/cb14d3e2d3533d76e405d730fea19846/TurbSim_v2.00.pdf) |
| von Karman components | Literal printed IECVKM equations: longitudinal prefactor 4, transverse prefactor 2; coefficients 71/189 and common longitudinal length scale | [TurbSim guide printed p.41, Eqs.27-28](https://openfast.readthedocs.io/en/main/_downloads/cb14d3e2d3533d76e405d730fea19846/TurbSim_v2.00.pdf); not a 2019-standard claim |
| Exponential root coherence | `exp(-decay*f*separation/U)`; square before comparing with magnitude-squared coherence | [Davenport (1961)](https://doi.org/10.1002/qj.49708737208); decay is user-selected, no IEC length-scale term |
| Weibull fit | Method-of-moments approximation using the sample coefficient of variation | [Justus et al. (1978)](https://doi.org/10.1175/1520-0450(1978)017%3C0350:MFEWSF%3E2.0.CO;2) |
| Rotor-equivalent wind speed | Cubic mean across sampled rotor heights; currently a uniform-height approximation, NOT the paper's area-weighted REWS | [Wagner et al. (2014)](https://doi.org/10.1088/1742-6596/524/1/012108) |
| Wind power density | `0.5 rho mean(U3)` | [IEC 61400-12-1:2022](https://webstore.iec.ch/en/publication/64682) |

## WRF-LES to TurbSim/OpenFAST coupling

`wind_field_from_components` maps a sampled WRF-LES plane to the TurbSim
full-field component convention. `write_bts` applies one signed-16-bit linear
scale per velocity component and writes component-fast, lateral-next,
vertical-next samples for every time step. `validate_bts` reads the file back
and checks dimensions, spacing, metadata, and quantization error.

References:

- [TurbSim v2 User's Guide](https://openfast.readthedocs.io/en/v4.0.5/_downloads/cb14d3e2d3533d76e405d730fea19846/TurbSim_v2.00.pdf), NREL.
- [OpenFAST Toolbox `TurbSimFile` implementation](https://github.com/OpenFAST/openfast_toolbox/blob/main/openfast_toolbox/io/turbsim_file.py), used as the binary-layout interoperability reference.
- [OpenFAST InflowWind documentation](https://openfast.readthedocs.io/en/main/source/user/inflowwind/index.html).
- [InflowWind User's Guide, Table 1](https://openfast.readthedocs.io/en/main/_downloads/a231262e7763b4d61759ebe4e0fc30b2/InflowWind_Manual.pdf):
  the uniform WindType=2 writer outputs all eight columns, including the three
  shear parameters and gust. Direction is clockwise from the OpenFAST reference,
  not WRF meteorological wind-FROM. Reference height/length must be configured
  separately. This text `.wnd` is not the binary full-field Bladed `.wnd`.

The conversion cannot by itself guarantee physical suitability. Before using a
BTS file in an engineering load case, check coordinate rotation, component
signs, plane orientation, temporal sampling, lateral/vertical spacing, rotor
coverage, terrain treatment, stationarity, resolved spectral bandwidth, and
whether the LES domain and forcing represent the intended inflow.

## Empirical flags and legacy compatibility

PBL threshold detection, low-level-jet thresholds, ramp-event thresholds, and
stability classes are configurable screening diagnostics rather than universal
physical laws. Their thresholds must be reported with results. The
`synthetic_wind_field` helper creates test data only; it is not an IEC or
TurbSim turbulence generator.

## Observations and undefined statistics

Actual observation comparisons require user-supplied QC'd measurements,
compatible units/heights/averaging periods and explicit nearest-time tolerance.
ISO timestamps with offsets normalize to UTC; naive times use a fixed offset.
Missing/duplicate times must be resolved explicitly; numeric time offsets need
an origin before normalization. No synthetic measurement is substituted.

Circular means use the resultant vector, as in the
[circular-mean definition](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.circmean.html).
This package deliberately returns NaN for a zero/near-zero resultant, rather
than selecting an arbitrary prevailing direction. Zero-mean component turbulence
intensity and unavailable case-ranking scores are likewise not invented.

## Numerical verification

[Calculation changes](CALCULATION_CHANGES.md) records which computations changed
relative to the committed Python baseline and why. A successful example run
does not establish numerical correctness. Release-gate tests add equation checks,
closed-form spectral integrals, energy identities, rotation invariance and SciPy
comparisons with matched sampling/window/phase conventions.

The printed TurbSim constants give integrals of `0.9984504 sigma²` (u) and
`0.9970441 sigma²` (v/w), not exactly sigma². These differences are retained and
tested against the closed beta-function integral; no undocumented normalization
is applied. The old prefactor 4 doubled the transverse variance.

In connected surface similarity, `HFX/(rho cp)` is temperature flux, multiplied
by `theta/T` to obtain potential-temperature flux before the linearized virtual
correction. Mean and flux use the same convention. In the dry limit those
factors cancel: `L = -rho cp T u*³/(kappa g HFX)`; tests cover several pressures.
Condensate and higher-order covariances are omitted. The partial resolved budget
uses dry buoyancy and does not silently include moisture contributions.
