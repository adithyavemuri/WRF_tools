# Scientific methods and references

This page is the methodology ledger for `wrf-tools`. Equations use SI units
unless a function docstring says otherwise. References are attached to the
implementation docstrings as well as collected here so that analyses can cite
the original method, not merely this software.

## WRF state reconstruction and atmospheric diagnostics

| Capability | Method | Primary reference |
|---|---|---|
| Potential temperature, pressure, geopotential height, destaggering | WRF perturbation variables and Arakawa C-grid conventions | [WRF-ARW Technical Note v4](https://www2.mmm.ucar.edu/wrf/users/docs/technote/v4_technote.pdf), doi:10.5065/1dfh-6p97 |
| Virtual temperature and density | Moist ideal-gas relations | [Stull (1988)](https://doi.org/10.1007/978-94-009-3027-8) |
| Bulk Richardson number, friction velocity, Monin-Obukhov length, logarithmic wind profile | Surface-layer similarity relations | [Foken (2006)](https://doi.org/10.1007/s10546-006-9048-6) |
| Convective velocity scale | `w* = [(g/theta_v) (w'theta_v')_0 z_i]^(1/3)`; the heat flux input is kinematic (K m s-1) | [Deardorff (1970)](https://doi.org/10.1175/1520-0469(1970)027%3C1211:CCOTLL%3E2.0.CO;2) |
| Brunt-Vaisala frequency | `N2 = (g/theta) dtheta/dz` | [Stull (1988)](https://doi.org/10.1007/978-94-009-3027-8) |
| Equivalent potential temperature | Simplified screening approximation `theta exp(Lv r/(cp T))`, not the full Bolton parcel formulation | [Bolton (1980)](https://doi.org/10.1175/1520-0493(1980)108%3C1046:TCOEPT%3E2.0.CO;2) |
| Reflectivity-rain rate | Default `Z = 200 R^1.6` | [Marshall, Hitschfeld and Gunn (1955)](https://doi.org/10.1175/1520-0469(1955)012%3C0322:AOTDOP%3E2.0.CO;2) |

## Turbulence, spectra, and wind energy

| Capability | Method | Primary reference |
|---|---|---|
| Resolved TKE and Reynolds fluxes | Reynolds decomposition; `TKE = 0.5 (u'u' + v'v' + w'w')` | [Pope (2000)](https://doi.org/10.1017/CBO9780511840531) |
| Q criterion | Positive second invariant of the velocity-gradient tensor | [Hunt, Wray and Moin (1988)](https://ntrs.nasa.gov/citations/19890015167) |
| Periodogram and Welch PSD | One-sided Fourier density; Hann-windowed segment averaging | [Welch (1967)](https://doi.org/10.1109/TAU.1967.1161901) |
| Magnitude-squared coherence and cross-spectrum | `|Pxy|2/(Pxx Pyy)` and `X conj(Y)` | [Bendat and Piersol (2010)](https://doi.org/10.1002/9781118032428) |
| `-5/3` reference slope | Inertial-subrange similarity law; plotted only as a slope guide, never as proof of an inertial range | [Kolmogorov (1941), English translation](https://doi.org/10.1098/rspa.1991.0075) |
| Kaimal component spectra | Neutral atmospheric surface-layer spectra | [Kaimal et al. (1972)](https://doi.org/10.1002/qj.49709841707) |
| Cheynet marine spectra | Pointed-blunt composite model (Eq. 26) and stable approximation (Eq. 28), using the author-supplied 81.5 m coefficient table for `-2 <= zeta < 2` | [Cheynet, Jakobsen and Reuder (2018)](https://doi.org/10.1007/s10546-018-0382-2) |
| IEC Kaimal/von Karman models | Engineering turbulence models | IEC 61400-1:2019, Annex C |
| Weibull fit | Method-of-moments approximation using the sample coefficient of variation | [Justus et al. (1978)](https://doi.org/10.1175/1520-0450(1978)017%3C0350:MFEWSF%3E2.0.CO;2) |
| Rotor-equivalent wind speed | Cubic mean across sampled rotor heights; currently a uniform-height approximation | [Clifton et al. (2014)](https://doi.org/10.1088/1742-6596/524/1/012108) |
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
