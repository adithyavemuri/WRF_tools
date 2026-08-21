import numpy as np
import xarray as xr

from wrf_tools.filters import butterworth_band, butterworth_spatial, spectral_downsample, top_hat_coarsen
from wrf_tools.spectra import coherence, cross_spectrum, log_bin, power_spectrum, radial_wavenumber_spectrum, welch_spectrum


def test_butterworth_suppresses_short_waves_and_preserves_metadata():
    x = np.arange(128)
    field = np.sin(2*np.pi*x/32)[None, :] + 0.5*np.sin(2*np.pi*x/2)[None, :]
    data = xr.DataArray(np.repeat(field, 8, axis=0), dims=("y", "x"), name="u", attrs={"units": "m s-1"})
    filtered = butterworth_spatial(data, dx=1, cutoff_wavelength=8, order=4)
    assert filtered.dims == data.dims
    assert filtered.attrs == data.attrs
    assert np.std(filtered - np.sin(2*np.pi*x/32)[None, :]) < 0.08


def test_top_hat_coarsen():
    data = np.arange(16).reshape(4, 4)
    np.testing.assert_allclose(top_hat_coarsen(data, factor_y=2), [[2.5, 4.5], [10.5, 12.5]])


def test_spectral_helpers_locate_signal_and_coherence():
    fs = 20.0
    t = np.arange(400) / fs
    signal = np.sin(2*np.pi*2*t)
    f, psd = power_spectrum(signal, spacing=1/fs)
    assert f[np.argmax(psd)] == 2.0
    fw, pw = welch_spectrum(signal, sample_rate=fs, nperseg=200, overlap=100)
    assert fw[np.argmax(pw)] == 2.0
    fc, coh = coherence(signal, signal, sample_rate=fs, nperseg=200, overlap=100)
    assert fc.shape == coh.shape
    assert np.nanmin(coh) > 0.99
    k, radial = radial_wavenumber_spectrum(np.outer(signal[:20], signal[:20]), dx=1)
    assert k.shape == radial.shape

def test_band_downsample_cross_and_log_bin():
    field=np.arange(64,dtype=float).reshape(8,8)
    assert spectral_downsample(field,factor_y=2).shape==(4,4)
    assert butterworth_band(field,dx=1,low_wavelength=2,high_wavelength=6).shape==field.shape
    frequency,cross=cross_spectrum(np.arange(16),np.arange(16))
    centers,binned=log_bin(frequency,cross,bins=4)
    assert centers.shape==binned.shape==(4,)
