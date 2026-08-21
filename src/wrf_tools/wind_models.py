"""Atmospheric wind spectra migrated from the MATLAB coupling workflows."""
from __future__ import annotations
import numpy as np

def kaimal_spectrum(frequency, *, mean_speed, height, friction_velocity, component="u"):
    """Return the neutral surface-layer Kaimal component spectrum.

    Constants follow Kaimal et al. (1972), *QJRMS*,
    doi:10.1002/qj.49709841707. Frequency is in Hz and the result is a
    one-sided velocity PSD in m2 s-2 Hz-1 when SI inputs are used.
    """
    f = np.asarray(frequency, float)
    n = f*height/mean_speed
    constants = {"u": (102.0, 33.0), "v": (17.0, 9.5), "w": (2.0, 5.3)}
    if component not in constants:
        raise ValueError("component must be u, v, or w")
    a, b = constants[component]
    return friction_velocity**2 * a*height/mean_speed / np.maximum((1+b*n)**(5/3), np.finfo(float).eps)

def von_karman_spectrum(frequency, *, mean_speed, sigma, length_scale, component="u"):
    """Return a one-dimensional von Karman velocity spectrum.

    The engineering form and component constants follow IEC 61400-1:2019,
    Annex C (IEC webstore publication 61400-1:2019).
    """
    f = np.asarray(frequency, float)
    x = f*length_scale/mean_speed
    if component == "u":
        return 4*sigma**2*length_scale/mean_speed/(1+70.8*x*x)**(5/6)
    if component in {"v", "w"}:
        return 4*sigma**2*length_scale/mean_speed*(1+188.4*x*x)/(1+70.8*x*x)**(11/6)
    raise ValueError("component must be u, v, or w")

def exponential_coherence(frequency, separation, *, mean_speed, decay=12.0):
    """Return Davenport's exponential coherence model.

    Reference: Davenport (1961), *Quarterly Journal of the Royal
    Meteorological Society*, doi:10.1002/qj.49708737208.
    """
    return np.exp(-decay*np.asarray(frequency)*np.asarray(separation)/mean_speed)

def iec_kaimal_spectrum(frequency, *, mean_speed, sigma, length_scale):
    """Return the IEC Kaimal longitudinal spectrum (IEC 61400-1:2019)."""
    f = np.asarray(frequency, float)
    return 4*sigma**2*length_scale/mean_speed/(1+6*f*length_scale/mean_speed)**(5/3)

def cheynet_spectrum(frequency, *, mean_speed, height, friction_velocity, stability=0.0, component="u"):
    """Return a legacy, heuristic stability adjustment to Kaimal spectra.

    Warning: despite the historical function name, this multiplier is not a
    published Cheynet spectral model and should not be cited as one. It is
    retained for reproducibility of migrated scripts; use ``kaimal_spectrum``
    or ``iec_kaimal_spectrum`` for reference-backed work.
    """
    neutral = kaimal_spectrum(frequency, mean_speed=mean_speed, height=height, friction_velocity=friction_velocity, component=component)
    correction = (1+5*max(stability, 0.0))**-0.5 if stability >= 0 else (1-16*stability)**0.25
    return neutral*correction

def synthetic_wind_field(mean_speed, *, nt, ny, nz, dt, dy, dz, sigma=1.0, length_scale=100.0, seed=None):
    """Generate a reproducible *demonstration* Gaussian wind field.

    This spatially filtered random field is not a TurbSim replacement and does
    not enforce a target spectrum, coherence model, or frozen turbulence.
    """
    rng = np.random.default_rng(seed)
    shape = (nt, nz, ny, 3)
    noise = rng.normal(size=shape)
    fy = np.fft.fftfreq(ny, dy); fz = np.fft.fftfreq(nz, dz)
    transfer = np.exp(-0.5*length_scale*np.sqrt(fz[:, None]**2+fy[None, :]**2))
    for time in range(nt):
        for component in range(3):
            noise[time, :, :, component] = np.fft.ifft2(np.fft.fft2(noise[time, :, :, component])*transfer).real
    std = noise.std(axis=(0, 1, 2), keepdims=True)
    noise = noise/np.where(std == 0, 1, std)*sigma
    mean = np.asarray(mean_speed)
    noise[..., 0] += mean.reshape(-1, 1, 1) if mean.ndim else mean
    return noise
