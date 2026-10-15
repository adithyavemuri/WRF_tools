"""Atmospheric wind spectra migrated from the MATLAB coupling workflows."""
from __future__ import annotations
import numpy as np

def _check_parameters(frequency, *parameters):
    """Require finite nonnegative frequency and declared scalar/array domains."""
    f=np.asarray(frequency,float)
    if not np.isfinite(f).all() or np.any(f<0):
        raise ValueError("Frequencies must be finite and nonnegative")
    for name,value,allow_zero in parameters:
        value=np.asarray(value,float)
        if not np.isfinite(value).all() or np.any(value<0 if allow_zero else value<=0):
            raise ValueError(f"{name} must be finite and {'nonnegative' if allow_zero else 'positive'}")
    return f

def kaimal_spectrum(frequency, *, mean_speed, height, friction_velocity, component="u"):
    """Return the neutral surface-layer Kaimal component spectrum.

    Near-neutral component variant documented in Risø-R-1506(EN), Eq. (4.5),
    https://backend.orbit.dtu.dk/ws/files/7702984/ris_r_1506.pdf (p.35).
    It uses u:102/(1+33n)^(5/3), v:17/(1+9.5n)^(5/3), and
    w:2.1/(1+5.3n^(5/3)), all multiplied by u*² z/U; n=fz/U.
    Kaimal et al. (1972), doi:10.1002/qj.49709841707, is the underlying
    family, not a claim that every published coefficient variant is identical.
    Frequency is Hz, result is one-sided m2 s-2 Hz-1. This is not IEC Kaimal.
    """
    f = _check_parameters(frequency,("mean_speed",mean_speed,False),("height",height,False),
        ("friction_velocity",friction_velocity,True))
    n = f*height/mean_speed
    constants = {"u": (102.0, 33.0), "v": (17.0, 9.5), "w": (2.1, 5.3)}
    if component not in constants:
        raise ValueError("component must be u, v, or w")
    a, b = constants[component]
    denominator=1+b*n**(5/3) if component=="w" else (1+b*n)**(5/3)
    return friction_velocity**2 * a*height/mean_speed / denominator

def von_karman_spectrum(frequency, *, mean_speed, sigma, length_scale, component="u"):
    """Return a one-dimensional von Karman velocity spectrum.

    Common longitudinal scale L for all components; sigma is the selected
    component's standard deviation. Coefficients 71/189 are transcribed directly
    from the TurbSim v2 guide Eqs. 27-28, printed p.41. The transverse prefactor
    is 2, not the longitudinal 4. Infinite-frequency integrals are approximately
    sigma squared (small coefficient-rounding error). This is the legacy
    IECVKM family described against IEC 61400-1 edition 2, NOT a claim that
    von Karman is specified by IEC 61400-1:2019. SI input; PSD per Hz.
    """
    f = _check_parameters(frequency,("mean_speed",mean_speed,False),("sigma",sigma,True),
        ("length_scale",length_scale,False))
    x = f*length_scale/mean_speed
    if component == "u":
        return 4*sigma**2*length_scale/mean_speed/(1+71*x*x)**(5/6)
    if component in {"v", "w"}:
        return 2*sigma**2*length_scale/mean_speed*(1+189*x*x)/(1+71*x*x)**(11/6)
    raise ValueError("component must be u, v, or w")

def exponential_coherence(frequency, separation, *, mean_speed, decay=12.0):
    """Return Davenport-style exponential ROOT coherence, not squared coherence.

    Square this amplitude before comparing with spectra.coherence, which returns
    magnitude-squared coherence. This simple model has no IEC length-scale term.

    Reference: Davenport (1961), *Quarterly Journal of the Royal
    Meteorological Society*, doi:10.1002/qj.49708737208.
    """
    f=_check_parameters(frequency,("separation",separation,True),("mean_speed",mean_speed,False),
        ("decay",decay,False))
    return np.exp(-decay*f*np.asarray(separation)/mean_speed)

def iec_kaimal_spectrum(frequency, *, mean_speed, sigma, length_scale):
    """Return the IEC Kaimal longitudinal spectrum (IEC 61400-1:2019)."""
    f = _check_parameters(frequency,("mean_speed",mean_speed,False),("sigma",sigma,True),
        ("length_scale",length_scale,False))
    return 4*sigma**2*length_scale/mean_speed/(1+6*f*length_scale/mean_speed)**(5/3)

_CHEYNET_COEFFICIENTS = (
    # zeta lower, upper, then u/v/w model and coefficients. Coefficients are
    # the 81.5 m values supplied with the original MATLAB implementation.
    (-2.0, -1.0, {"u": (26, 206, 73, 4.2, 14), "v": (26, 374, 144, 2.8, 9.5), "w": (26, 21, 10, 0.5, 2.3)}),
    (-1.0, -0.5, {"u": (26, 122, 51, 1.5, 6.8), "v": (26, 286, 149, 1.9, 8), "w": (26, 16, 13, 0.9, 3)}),
    (-0.5, -0.3, {"u": (26, 141, 64, 1.6, 8.9), "v": (26, 306, 185, 1.9, 8.5), "w": (26, 14, 18, 1, 3.3)}),
    (-0.3, -0.1, {"u": (26, 170, 78, 2.2, 14), "v": (26, 432, 362, 3.1, 13), "w": (26, 9.4, 22, 1.1, 3.7)}),
    (-0.1, 0.1, {"u": (26, 189, 111, 9.6, 40), "v": (28, 0.007, 5.2, 12, 0.05e-5), "w": (26, 2.9, 16, 1.4, 3.7)}),
    (0.1, 0.3, {"u": (28, 0.008, 16, 33, 0), "v": (28, 0.001, 4.3, 6, 0.3e-5), "w": (26, 0.03, 1.2, 1.5, 2.6)}),
    (0.3, 0.5, {"u": (28, 0.010, 9.8, 14, 0.3e-5), "v": (28, 0.001, 3.2, 3.2, 0.9e-5), "w": (26, 0, 0, 1.2, 1.4)}),
    (0.5, 1.0, {"u": (28, 0.01, 7.6, 8.8, 0.8e-5), "v": (28, 0.006, 2.8, 2.1, 1.3e-5), "w": (26, 0.02, 0.3, 1, 1)}),
    (1.0, 2.0, {"u": (28, 0.03, 5, 4.4, 1.5e-5), "v": (28, 0.02, 2.1, 1.2, 3.3e-5), "w": (26, 1.2, 18, 0.6, 0.5)}),
)


def cheynet_spectrum(frequency, *, mean_speed, height, friction_velocity, stability=0.0, component="u"):
    """Return the Cheynet marine-boundary-layer velocity spectrum.

    Implements the pointed-blunt composite model (Eq. 26) and stable-regime
    approximation (Eq. 28) from Cheynet, Jakobsen, and Reuder (2018),
    doi:10.1007/s10546-018-0382-2. ``stability`` is the local similarity
    parameter zeta. The tabulated coefficients are the 81.5 m values from the
    author-supplied open MATLAB implementation migrated into this project.

    Frequencies must be positive and are in Hz. With SI inputs, the returned
    one-sided PSD is in m2 s-2 Hz-1. The validated coefficient range is
    ``-2 <= zeta < 2``; no extrapolation is performed.
    """
    if component not in {"u", "v", "w"}:
        raise ValueError("component must be u, v, or w")
    if not -2.0 <= stability < 2.0:
        raise ValueError("stability must satisfy -2 <= zeta < 2")
    f = np.asarray(frequency, dtype=float)
    speed = np.asarray(mean_speed, dtype=float)
    z = np.asarray(height, dtype=float)
    _check_parameters(f,("mean_speed",speed,False),("height",z,False),("friction_velocity",friction_velocity,True))
    if np.any(f <= 0):
        raise ValueError("frequency, mean_speed, and height must be positive")
    coefficients = next(values[component] for lower, upper, values in _CHEYNET_COEFFICIENTS if lower <= stability < upper)
    reduced = np.expand_dims(z / speed, -1) * f
    if coefficients[0] == 26:
        _, a1, b1, a2, b2 = coefficients
        normalized = a1*reduced/(1+b1*reduced)**(5/3) + a2*reduced/(1+b2*reduced**(5/3))
    else:
        _, c1, a2, b2, a3 = coefficients
        normalized = c1*reduced**(-2/3) + a2*reduced/(1+b2*reduced**(5/3)) + a3*reduced**-2
    result = normalized*np.expand_dims(np.asarray(friction_velocity, dtype=float)**2, -1)/f
    return result.item() if result.ndim == 0 else result

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
