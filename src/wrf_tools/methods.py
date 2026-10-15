"""Method provenance for the capability catalog (not a validation certificate).

References justify equations/conventions, NOT atmospheric accuracy. Numerical
regression evidence and actual execution are recorded separately by the audit.
"""

REFERENCES = {
    "wrf": ("WRF-ARW v4 Technical Note", "https://doi.org/10.5065/1dfh-6p97"),
    "wrf_constants": ("WRF v4.7.1 constants", "https://github.com/wrf-model/WRF/blob/v4.7.1/share/module_model_constants.F"),
    "stull": ("Stull (1988), Boundary Layer Meteorology", "https://doi.org/10.1007/978-94-009-3027-8"),
    "pope": ("Pope (2000), Turbulent Flows", "https://doi.org/10.1017/CBO9780511840531"),
    "hunt": ("Hunt, Wray and Moin (1988), Q criterion", "https://ntrs.nasa.gov/citations/19890015184"),
    "deardorff": ("Deardorff (1970), convective velocity scale", "https://doi.org/10.1175/1520-0469(1970)027%3C1211:CVATSF%3E2.0.CO;2"),
    "bolton": ("Bolton (1980), thermodynamic approximations", "https://doi.org/10.1175/1520-0493(1980)108%3C1046:TCOEPT%3E2.0.CO;2"),
    "rotor": ("Wagner et al. (2014), rotor-equivalent speed", "https://doi.org/10.1088/1742-6596/524/1/012108"),
    "justus": ("Justus et al. (1978), wind-speed distributions", "https://doi.org/10.1175/1520-0450(1978)017%3C0350:MFEWSF%3E2.0.CO;2"),
    "welch": ("Welch (1967), modified periodograms", "https://doi.org/10.1109/TAU.1967.1161901"),
    "resample": ("SciPy Fourier resampling: periodicity/Nyquist conventions", "https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.resample.html"),
    "coherence": ("SciPy Welch coherence definition", "https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.coherence.html"),
    "butterworth": ("Butterworth (1930), filter response", "https://doi.org/10.1049/jiee-1.1930.0018"),
    "kaimal": ("Kaimal et al. (1972), surface-layer spectra", "https://doi.org/10.1002/qj.49709841707"),
    "kaimal_components": ("Risø-R-1506(EN), near-neutral component spectra Eq. 4.5", "https://backend.orbit.dtu.dk/ws/files/7702984/ris_r_1506.pdf"),
    "cheynet": ("Cheynet et al. (2018), marine spectra", "https://doi.org/10.1007/s10546-018-0382-2"),
    "davenport": ("Davenport (1961), gust spectra and spatial cross-correlation", "https://doi.org/10.1002/qj.49708737208"),
    "wasserstein": ("SciPy empirical Wasserstein-1 CDF identity", "https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wasserstein_distance.html"),
    "pearson": ("SciPy Pearson correlation definition", "https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html"),
    "taylor": ("Taylor (2001), diagram of model statistics", "https://doi.org/10.1029/2000JD900719"),
    "openfast": ("OpenFAST Toolbox format reference", "https://github.com/OpenFAST/openfast_toolbox/tree/main/openfast_toolbox/io"),
    "rainflow": ("OpenFAST Toolbox fatigue algorithms / ASTM E1049", "https://github.com/OpenFAST/openfast_toolbox/blob/main/openfast_toolbox/tools/fatigue.py"),
    "wps": ("WRF WPS user guide", "https://www2.mmm.ucar.edu/wrf/users/wps/namelist.wps_all_options.html"),
    "station": ("WRF station-output source and record conventions", "https://github.com/wrf-model/WRF/blob/v4.7.1/share/wrf_timeseries.F"),
    "xarray": ("xarray labelled-array conventions", "https://docs.xarray.dev/en/stable/user-guide/index.html"),
    "numpy": ("NumPy numerical operations", "https://numpy.org/doc/stable/reference/index.html"),
    "gradient": ("NumPy nonuniform finite-difference weights and boundary conventions", "https://numpy.org/doc/stable/reference/generated/numpy.gradient.html"),
    "circular": ("SciPy circular vector-mean definition and zero-resultant caveat", "https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.circmean.html"),
    "inflow_uniform": ("OpenFAST InflowWind User's Guide, Table 1: eight-column uniform wind", "https://openfast.readthedocs.io/en/main/_downloads/a231262e7763b4d61759ebe4e0fc30b2/InflowWind_Manual.pdf"),
    "iec": ("IEC 61400-1:2019 design requirements (specific edition, not certification)", "https://webstore.iec.ch/en/publication/26423"),
    "turbsim": ("TurbSim User's Guide: engineering spectral conventions", "https://openfast.readthedocs.io/en/main/_downloads/cb14d3e2d3533d76e405d730fea19846/TurbSim_v2.00.pdf"),
    "matplotlib": ("Matplotlib plotting/animation APIs", "https://matplotlib.org/stable/users/index.html"),
    "cartopy": ("Cartopy map projections and features", "https://cartopy.readthedocs.io/stable/"),
}

# Numerical utilities and I/O need an algorithm/format contract, not invented
# atmospheric-paper citations. Screening thresholds are explicitly empirical.
_MODULES = {
    "diagnostics": ("physical diagnostic", ["stull","pope"], "Check units, coordinates and averaging assumptions in the function docstring."),
    "les": ("turbulence diagnostic", ["pope","wrf"], "Resolved statistics need justified averaging; SGS inputs need confirmed units/sign conventions."),
    "averaging": ("numerical reduction", ["numpy","wrf"], "Explicit weights and validity masks; model-index and physical-height means differ."),
    "comparison": ("numerical comparison", ["xarray"], "Aligned coordinates/units do not establish experimental comparability."),
    "spectra": ("spectral estimator", ["welch","coherence"], "Regular sampling; one-sided normalization. Radial result is shell mean, not integrated energy density."),
    "filters": ("numerical filter", ["butterworth","resample"], "FFT methods assume periodicity; block filters are discrete averages, not a full Honnert scale-adaptivity model."),
    "wind_models": ("parametric wind model", ["kaimal","cheynet"], "Check model-specific stability/coefficient limits. Synthetic data are not TurbSim-quality inflow."),
    "spatial": ("numerical/screening diagnostic", ["numpy","wrf"], "Nominal-grid Cartesian operations; selected reference/thresholds are researcher choices."),
    "validation": ("statistical comparison", ["pearson","wasserstein"], "Paired finite samples for deterministic scores; no instrument QC, sampling independence or uncertainty model inferred."),
    "observations": ("generic observation I/O/alignment", ["xarray"], "No native radar/SCADA/LiDAR calibration or QC. Set time tolerance and match units/heights yourself."),
    "grid": ("grid/interpolation operation", ["wrf","numpy"], "Co-locate first. Linear interpolation is not conservative remapping or terrain-metric differentiation."),
    "extract": ("data selection/interpolation", ["wrf","xarray"], "Native staggered variables must be collocated explicitly; generic vertical coordinates are user-supplied."),
    "io": ("file/data contract", ["wrf","xarray"], "Minimum schema/grid/time checks, not full WRF physics/units validation."),
    "timeseries": ("station file contract", ["station"], "Supported standard text records only; station time offsets require a user-supplied origin."),
    "wps": ("configuration/geometry utility", ["wps"], "Simple namelist subset. Geographic-corner helper assumes centred Lambert geometry, not every WPS projection/reference option."),
    "coupling": ("inflow format/array operation", ["openfast"], "Format round trips alone do not prove external interoperability or physically suitable turbine inflow; legacy layouts are limited."),
    "openfast": ("loads I/O/statistics", ["openfast","rainflow"], "Supported binary IDs are 1/2. Rainflow outputs ranges/counts, not fatigue damage or certified life."),
    "openfast_input": ("text configuration operation", ["openfast"], "Labelled scalar text lines only; not a complete OpenFAST grammar."),
    "plotting": ("visualization", ["matplotlib","taylor"], "Plots do not validate physics; coordinates, units and interpretation are caller responsibilities."),
    "visualization": ("WRF diagnostic visualization", ["wrf","wrf_constants","cartopy"], "Physical-height interpolation, stationary grid, no extrapolation; verify dry-theta convention."),
    "turbulence": ("model-output diagnostic", ["wrf"], "QKE/2, TKE_PBL and dynamics TKE are distinct alternatives, not resolved/total energy or budget closure."),
    "hindcast": ("report orchestration", ["wrf"], "Technical hindcast screening, not observation validation, climatology or bankable resource assessment."),
    "diagnostic_groups": ("diagnostic orchestration", ["stull","pope","hunt"], "See each group method note and explicit unavailable status; no automatic scientific inference."),
    "reporting": ("report/serialization utility", ["xarray","matplotlib"], "Serializes supplied evidence, does not establish its scientific accuracy."),
    "animations": ("visualization", ["matplotlib","wrf"], "Actual history states with fixed scales; playback rate is not model time or extra resolved information."),
    "contours3d": ("contour geometry", ["matplotlib","wrf"], "Stacked horizontal isolines, not volumetric isosurfaces; vertical exaggeration is recorded."),
    "maps": ("cartographic infrastructure", ["cartopy"], "Natural Earth context is not model data; cache/download policy is explicit."),
    "workflow": ("I/O/process infrastructure", ["xarray"], "External conversion needs a real executable; copies do not run WRF or validate physics."),
    "doctor": ("environment infrastructure", ["numpy","xarray"], "Dependency availability is not a numerical or scientific validation result."),
    "quality": ("configurable screening", ["wrf","numpy"], "Default ranges and jump thresholds are heuristics, not a proof of valid meteorology. No automatic correction."),
}

_OVERRIDES = {
    "brunt_vaisala_frequency": ("physical diagnostic", ["stull","gradient"], "Dry N; negative N-squared clipped. Nonuniform column differences with first-order edges; no condensate/moist correction."),
    "inversion_layers": ("threshold screening", ["gradient"], "Nonuniform temperature gradients; threshold is user-selected. Missing derivatives are unclassified (False), not proof of no inversion."),
    "tke_budget": ("partial physical budget", ["stull","gradient"], "Nonuniform vertical gradients of time-mean columns; shear/buoyancy only. No transport, pressure, dissipation, SGS or moving-height budget terms."),
    "circular_mean": ("circular statistic", ["circular"], "Nonnegative weights; this package returns NaN for a near-zero resultant rather than an arbitrary direction."),
    "write_uniform_wind": ("inflow file contract", ["inflow_uniform"], "Eight-column WindType=2 file; direction is clockwise from the OpenFAST reference, not WRF meteorological wind-FROM. Configure reference height/length separately."),
    "von_karman_spectrum": ("parametric engineering spectrum", ["turbsim"], "TurbSim printed p.41, Eqs.27-28: coefficients 71/189 and transverse prefactor 2. Legacy edition-2 family, not a 2019-standard claim or synthetic field generator."),
    "iec_kaimal_spectrum": ("parametric engineering spectrum", ["iec","turbsim"], "Longitudinal component only; this formula alone does not generate coherent inflow or establish IEC compliance."),
    "exponential_coherence": ("parametric root-coherence model", ["davenport"], "Returns root coherence exp(-decay*f*separation/U), not the magnitude-squared estimator. Decay is user-selected; no IEC length-scale term."),
    "kaimal_spectrum": ("parametric near-neutral spectrum", ["kaimal_components","kaimal"], "Explicit Eq.4.5 coefficient variant, not IEC Kaimal. Vertical denominator differs from u/v; see docstring."),
    "q_criterion": ("physical diagnostic", ["hunt"], "Uniform Cartesian derivatives only; nominal-metric report approximation is labelled."),
    "convective_velocity_scale": ("physical diagnostic", ["deardorff"], "Kinematic virtual heat flux in K m/s; negative buoyancy clipped to zero."),
    "rotor_equivalent_wind_speed": ("approximate screening diagnostic", ["rotor"], "Uniform-height cube mean, NOT the paper's rotor-area-weighted REWS; no extrapolation."),
    "stability_class": ("legacy heuristic", ["stull"], "50/200 m thresholds are package heuristics, NOT standard/Pasquill classes or a method claimed by Stull."),
    "diagnose_pbl_height": ("threshold heuristic", ["stull"], "User-selected theta-v excess threshold; NOT the producing WRF scheme's PBL diagnosis."),
    "low_level_jet": ("threshold heuristic", ["stull"], "Package-specific speed/drop rule, not a universal jet definition."),
    "weibull_fit": ("empirical estimator", ["justus"], "Positive samples only; constant series gives the limiting infinite shape. Not a long-term resource estimate."),
    "equivalent_potential_temperature": ("screening approximation", ["stull"], "Simplified exponential formula, NOT Bolton's full parcel/pseudoadiabatic equation."),
    "dew_point": ("empirical approximation", ["bolton"], "Inverse liquid-water fit using 17.67/243.5 coefficients; Kelvin input/output and RH in percent. Not an ice-saturation formula."),
    "relative_humidity": ("empirical approximation", ["bolton"], "Liquid-water saturation fit; RH clipped to 0-100 percent, not an ice or supersaturation diagnostic."),
    "synthetic_wind_field": ("synthetic test-data generator", ["numpy"], "Filtered Gaussian demonstration; does not enforce IEC/Kaimal coherence or frozen turbulence."),
    "kantorovich_distance": ("exact empirical statistic", ["wasserstein"], "Independent empirical distributions, not paired scores; finite samples only."),
    "standard_error": ("IID approximation", ["numpy"], "s/sqrt(n), ddof=1; autocorrelation is NOT corrected."),
    "spectral_downsample": ("periodic numerical resampling", ["resample"], "Antialias Fourier truncation with Nyquist merging, not conservative area remapping."),
}


def _basis(module,name):
    category,ids,caveat=_OVERRIDES.get(name,_MODULES[module.split(".")[0]])
    return dict(category=category,caveat=caveat,references=[dict(id=key,title=REFERENCES[key][0],url=REFERENCES[key][1]) for key in ids])
