from __future__ import annotations

from pathlib import Path
import struct

import numpy as np

from ...exceptions import DataValidationError
from ...types import WindField

_IDENTIFIER = 7
_INT16_MIN = -32767
_INT16_MAX = 32767


def _scaling(velocity: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    minimum = np.min(velocity, axis=(0, 1, 2))
    maximum = np.max(velocity, axis=(0, 1, 2))
    span = maximum - minimum
    slope = np.where(span > 0, (_INT16_MAX - _INT16_MIN) / span, 1.0)
    offset = _INT16_MIN - minimum * slope
    return slope.astype(np.float32), offset.astype(np.float32)


def write_bts(path: str | Path, field: WindField) -> Path:
    """Write a TurbSim/OpenFAST BTS full-field wind file.

    The input velocity order is ``(time, vertical, lateral, component)``.
    Scaling is derived independently for each component to retain int16
    precision. The function never assumes a fixed grid or record length.
    """
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    velocity = np.asarray(field.velocity, dtype=np.float64)
    nt, nz, ny, _ = velocity.shape
    slope, offset = _scaling(velocity)
    encoded = np.rint(velocity * slope + offset)
    encoded = np.clip(encoded, _INT16_MIN, _INT16_MAX).astype("<i2")
    description = field.description.encode("utf-8")

    with destination.open("wb") as stream:
        stream.write(struct.pack("<hiiii", _IDENTIFIER, nz, ny, 0, nt))
        stream.write(
            struct.pack(
                "<ffffff",
                field.dz,
                field.dy,
                field.dt,
                float(field.mean_speed),
                field.hub_height,
                field.bottom_height,
            )
        )
        stream.write(struct.pack("<ffffff", slope[0], offset[0], slope[1], offset[1], slope[2], offset[2]))
        stream.write(struct.pack("<i", len(description)))
        stream.write(description)
        stream.write(encoded.tobytes(order="C"))
    return destination


def read_bts(path: str | Path) -> WindField:
    """Read a BTS file written in the standard TurbSim full-field layout."""
    source = Path(path)
    with source.open("rb") as stream:
        identifier, nz, ny, tower_points, nt = struct.unpack("<hiiii", stream.read(18))
        if identifier not in (7, 8):
            raise DataValidationError(f"Unsupported BTS identifier {identifier}")
        dz, dy, dt, mean_speed, hub_height, bottom_height = struct.unpack("<ffffff", stream.read(24))
        values = struct.unpack("<ffffff", stream.read(24))
        slope = np.asarray(values[0::2], dtype=float)
        offset = np.asarray(values[1::2], dtype=float)
        (description_size,) = struct.unpack("<i", stream.read(4))
        if description_size < 0 or description_size > 1_000_000:
            raise DataValidationError("Invalid BTS description length")
        description = stream.read(description_size).decode("utf-8", errors="replace")
        count = nt * nz * ny * 3
        encoded = np.frombuffer(stream.read(count * 2), dtype="<i2", count=count)
        if encoded.size != count:
            raise DataValidationError("BTS file ended before the velocity field was complete")
        if tower_points:
            stream.read(nt * tower_points * 3 * 2)
    velocity = encoded.reshape(nt, nz, ny, 3).astype(float)
    velocity = (velocity - offset) / slope
    return WindField(
        velocity=velocity,
        dy=dy,
        dz=dz,
        dt=dt,
        hub_height=hub_height,
        bottom_height=bottom_height,
        description=description,
        mean_speed=mean_speed,
        source=source,
    )


def validate_bts(
    path: str | Path,
    expected: WindField | None = None,
    *,
    absolute_tolerance: float = 0.01,
) -> WindField:
    """Read a BTS file and optionally compare it with the source wind field."""
    actual = read_bts(path)
    if expected is not None:
        if actual.velocity.shape != expected.velocity.shape:
            raise DataValidationError(
                f"BTS shape {actual.velocity.shape} differs from expected {expected.velocity.shape}"
            )
        error = float(np.max(np.abs(actual.velocity - expected.velocity)))
        if error > absolute_tolerance:
            raise DataValidationError(
                f"BTS round-trip error {error:.6g} exceeds {absolute_tolerance}"
            )
    return actual
