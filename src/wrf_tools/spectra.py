"""Frequency and wavenumber spectral diagnostics."""
from __future__ import annotations

from typing import Any

import numpy as np


def power_spectrum(data: Any, *, spacing: float = 1.0, axis: int = -1, detrend: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """Return a one-sided periodogram with density units per frequency.

    Uses the standard discrete-Fourier periodogram normalization. See
    Percival and Walden (1993), *Spectral Analysis for Physical
    Applications*, Cambridge University Press, doi:10.1017/CBO9780511622762.
    """
    values = np.asarray(data, dtype=float)
    if spacing <= 0:
        raise ValueError("spacing must be positive")
    if detrend:
        values = values - np.mean(values, axis=axis, keepdims=True)
    n = values.shape[axis]
    transform = np.fft.rfft(values, axis=axis)
    psd = (spacing / n) * np.abs(transform) ** 2
    slicer = [slice(None)] * psd.ndim
    if n > 2:
        slicer[axis] = slice(1, -1 if n % 2 == 0 else None)
        psd[tuple(slicer)] *= 2.0
    return np.fft.rfftfreq(n, spacing), psd


def welch_spectrum(data: Any, *, sample_rate: float, nperseg: int, overlap: int = 0, axis: int = -1) -> tuple[np.ndarray, np.ndarray]:
    """Welch PSD using Hann-windowed overlapping segments.

    Reference: Welch (1967), IEEE Transactions on Audio and
    Electroacoustics, doi:10.1109/TAU.1967.1161901.
    """
    values = np.asarray(data, dtype=float)
    if not 0 <= overlap < nperseg <= values.shape[axis]:
        raise ValueError("require 0 <= overlap < nperseg <= axis length")
    step = nperseg - overlap
    starts = range(0, values.shape[axis] - nperseg + 1, step)
    window = np.hanning(nperseg)
    scale = sample_rate * np.sum(window**2)
    spectra = []
    for start in starts:
        sl = [slice(None)] * values.ndim
        sl[axis] = slice(start, start + nperseg)
        segment = values[tuple(sl)] - np.mean(values[tuple(sl)], axis=axis, keepdims=True)
        wshape = [1] * values.ndim
        wshape[axis] = nperseg
        fft = np.fft.rfft(segment * window.reshape(wshape), axis=axis)
        spectra.append(np.abs(fft) ** 2 / scale)
    psd = np.mean(spectra, axis=0)
    interior = [slice(None)] * psd.ndim
    interior[axis] = slice(1, -1 if nperseg % 2 == 0 else None)
    psd[tuple(interior)] *= 2.0
    return np.fft.rfftfreq(nperseg, d=1.0 / sample_rate), psd


def radial_wavenumber_spectrum(data: Any, *, dx: float, dy: float | None = None, bins: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Azimuthally average a 2-D field's FFT power in radial bins.

    This is a shell-mean spectrum, not a shell-integrated energy spectrum.
    The returned wavenumber is in cycles per unit distance.
    """
    field = np.asarray(data, dtype=float)
    if field.ndim != 2:
        raise ValueError("data must be two-dimensional")
    dy = dx if dy is None else dy
    field = field - np.mean(field)
    power = np.abs(np.fft.fft2(field)) ** 2 / field.size
    ky = np.fft.fftfreq(field.shape[0], dy)
    kx = np.fft.fftfreq(field.shape[1], dx)
    radial = np.sqrt(ky[:, None] ** 2 + kx[None, :] ** 2)
    bins = min(field.shape) // 2 if bins is None else bins
    edges = np.linspace(0.0, radial.max(), bins + 1)
    index = np.digitize(radial.ravel(), edges) - 1
    summed = np.bincount(index, weights=power.ravel(), minlength=bins + 1)[:bins]
    count = np.bincount(index, minlength=bins + 1)[:bins]
    return 0.5 * (edges[:-1] + edges[1:]), np.divide(summed, count, out=np.zeros_like(summed), where=count > 0)


def coherence(first: Any, second: Any, *, sample_rate: float, nperseg: int, overlap: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Return Welch-estimated magnitude-squared coherence.

    The estimator is ``|Pxy|^2 / (Pxx Pyy)`` using common Hann-windowed
    segments; see Bendat and Piersol (2010), *Random Data*, 4th ed.,
    doi:10.1002/9781118032428.
    """
    x, y = np.asarray(first, float), np.asarray(second, float)
    if x.shape != y.shape or x.ndim != 1:
        raise ValueError("signals must be equally shaped one-dimensional arrays")
    step = nperseg - overlap
    window = np.hanning(nperseg)
    pxx = pyy = pxy = None
    count = 0
    for start in range(0, x.size - nperseg + 1, step):
        fx = np.fft.rfft((x[start:start+nperseg] - x[start:start+nperseg].mean()) * window)
        fy = np.fft.rfft((y[start:start+nperseg] - y[start:start+nperseg].mean()) * window)
        pxx = np.abs(fx)**2 if pxx is None else pxx + np.abs(fx)**2
        pyy = np.abs(fy)**2 if pyy is None else pyy + np.abs(fy)**2
        pxy = fx * np.conj(fy) if pxy is None else pxy + fx * np.conj(fy)
        count += 1
    if count == 0:
        raise ValueError("nperseg exceeds signal length")
    coh = np.abs(pxy / count) ** 2 / ((pxx / count) * (pyy / count))
    return np.fft.rfftfreq(nperseg, 1.0 / sample_rate), np.clip(coh.real, 0.0, 1.0)

def cross_spectrum(first, second, *, spacing=1.0, detrend=True):
    """Return the one-sided cross-periodogram ``X(f) conj(Y(f))``.

    Reference: Bendat and Piersol (2010), doi:10.1002/9781118032428.
    """
    x,y=np.asarray(first,float),np.asarray(second,float)
    if x.shape!=y.shape or x.ndim!=1: raise ValueError("signals must be equally shaped one-dimensional arrays")
    if detrend: x=x-x.mean(); y=y-y.mean()
    cross=spacing/x.size*np.fft.rfft(x)*np.conj(np.fft.rfft(y)); cross[1:-1]*=2
    return np.fft.rfftfreq(x.size,spacing),cross

def log_bin(frequency, spectrum, *, bins=30):
    """Average spectral values in geometrically spaced frequency bins."""
    f,s=np.asarray(frequency,float),np.asarray(spectrum); mask=f>0
    edges=np.geomspace(f[mask].min(),f[mask].max(),bins+1); index=np.digitize(f[mask],edges)-1
    count=np.bincount(index,minlength=bins+1)[:bins]; centers=np.sqrt(edges[:-1]*edges[1:]); summed=np.bincount(index,weights=np.real(s[mask]),minlength=bins+1)[:bins]
    return centers,np.divide(summed,count,out=np.full(bins,np.nan),where=count>0)
