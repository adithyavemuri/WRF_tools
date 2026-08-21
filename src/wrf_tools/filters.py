"""Spatial filters used by WRF and WRF-LES post-processing."""
from __future__ import annotations

from typing import Any

import numpy as np
import xarray as xr


def _wrap(original: Any, values: np.ndarray, dims: tuple[str, ...] | None = None) -> Any:
    if isinstance(original, xr.DataArray):
        out_dims = dims or original.dims
        coords = {d: original.coords[d] for d in out_dims if d in original.coords and original.sizes[d] == values.shape[out_dims.index(d)]}
        return xr.DataArray(values, dims=out_dims, coords=coords, attrs=original.attrs, name=original.name)
    return values


def butterworth_spatial(
    data: Any,
    *,
    dx: float,
    dy: float | None = None,
    cutoff_wavelength: float,
    order: int = 2,
    axes: tuple[int, int] = (-2, -1),
    kind: str = "lowpass",
) -> Any:
    """Apply an isotropic 2-D FFT Butterworth filter.

    ``cutoff_wavelength`` is the half-power wavelength in the same units as
    ``dx`` and ``dy``. Leading dimensions are processed independently.
    """
    array = np.asarray(data, dtype=float)
    if dx <= 0 or (dy is not None and dy <= 0) or cutoff_wavelength <= 0 or order < 1:
        raise ValueError("spacing, cutoff wavelength, and order must be positive")
    if kind not in {"lowpass", "highpass"}:
        raise ValueError("kind must be 'lowpass' or 'highpass'")
    ay, ax = (a % array.ndim for a in axes)
    if ay == ax:
        raise ValueError("filter axes must differ")
    spacing_y = dx if dy is None else dy
    ky = np.fft.fftfreq(array.shape[ay], d=spacing_y)
    kx = np.fft.fftfreq(array.shape[ax], d=dx)
    shape_y = [1] * array.ndim
    shape_x = [1] * array.ndim
    shape_y[ay] = ky.size
    shape_x[ax] = kx.size
    radial = np.sqrt(ky.reshape(shape_y) ** 2 + kx.reshape(shape_x) ** 2)
    cutoff = 1.0 / cutoff_wavelength
    low = 1.0 / np.sqrt(1.0 + (radial / cutoff) ** (2 * order))
    transfer = low if kind == "lowpass" else np.sqrt(np.maximum(0.0, 1.0 - low**2))
    transformed = np.fft.fftn(array, axes=(ay, ax))
    result = np.fft.ifftn(transformed * transfer, axes=(ay, ax)).real
    return _wrap(data, result)


def top_hat_coarsen(
    data: Any,
    *,
    factor_y: int,
    factor_x: int | None = None,
    axes: tuple[int, int] = (-2, -1),
    trim: bool = False,
) -> Any:
    """Block-average a horizontal field (the Honnert-style top-hat filter)."""
    array = np.asarray(data)
    factor_x = factor_y if factor_x is None else factor_x
    if factor_y < 1 or factor_x < 1:
        raise ValueError("coarsening factors must be positive integers")
    ay, ax = (a % array.ndim for a in axes)
    moved = np.moveaxis(array, (ay, ax), (-2, -1))
    ny, nx = moved.shape[-2:]
    usable_y, usable_x = ny - ny % factor_y, nx - nx % factor_x
    if (usable_y != ny or usable_x != nx) and not trim:
        raise ValueError("horizontal sizes must be divisible by factors unless trim=True")
    moved = moved[..., :usable_y, :usable_x]
    coarse = moved.reshape(*moved.shape[:-2], usable_y // factor_y, factor_y, usable_x // factor_x, factor_x).mean(axis=(-3, -1))
    result = np.moveaxis(coarse, (-2, -1), (ay, ax))
    dims = None
    if isinstance(data, xr.DataArray):
        dims = data.dims
    return _wrap(data, result, dims)


def resolved_subfilter(data: Any, filtered: Any) -> tuple[Any, Any]:
    """Return the resolved field and residual/subfilter field."""
    residual = data - filtered
    return filtered, residual

def butterworth_band(data: Any, *, dx: float, low_wavelength: float, high_wavelength: float, dy: float | None = None, order: int = 2, axes=(-2,-1)) -> Any:
    """Retain spatial wavelengths between two limits."""
    if low_wavelength >= high_wavelength:
        raise ValueError("low_wavelength must be smaller than high_wavelength")
    remove_short = butterworth_spatial(data, dx=dx, dy=dy, cutoff_wavelength=low_wavelength, order=order, axes=axes, kind="lowpass")
    remove_long = butterworth_spatial(remove_short, dx=dx, dy=dy, cutoff_wavelength=high_wavelength, order=order, axes=axes, kind="highpass")
    return remove_long

def spectral_downsample(data: Any, *, factor_y: int, factor_x: int | None = None, axes=(-2,-1)) -> Any:
    """Fourier crop a 2-D field to a coarser grid without aliasing."""
    array=np.asarray(data,float); factor_x=factor_y if factor_x is None else factor_x; ay,ax=(a%array.ndim for a in axes)
    moved=np.moveaxis(array,(ay,ax),(-2,-1)); ny,nx=moved.shape[-2:]; new_y,new_x=ny//factor_y,nx//factor_x
    if new_y<1 or new_x<1: raise ValueError("downsampling factor exceeds grid")
    transformed=np.fft.fftshift(np.fft.fft2(moved,axes=(-2,-1)),axes=(-2,-1)); sy=(ny-new_y)//2; sx=(nx-new_x)//2
    cropped=transformed[...,sy:sy+new_y,sx:sx+new_x]; result=np.fft.ifft2(np.fft.ifftshift(cropped,axes=(-2,-1)),axes=(-2,-1)).real*(new_y*new_x)/(ny*nx)
    return _wrap(data,np.moveaxis(result,(-2,-1),(ay,ax)),data.dims if isinstance(data,xr.DataArray) else None)
