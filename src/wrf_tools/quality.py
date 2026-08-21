"""Transparent quality control for WRF datasets."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable
import numpy as np
import xarray as xr


@dataclass(frozen=True)
class QCIssue:
    severity: str
    variable: str
    check: str
    message: str
    count: int = 0
    first_index: tuple[int, ...] | None = None
    first_value: float | None = None

    def to_dict(self):
        return asdict(self)


DEFAULT_LIMITS = {
    "T2": (180.0, 340.0, "K"), "PSFC": (45000.0, 110000.0, "Pa"),
    "Q2": (0.0, 0.05, "kg kg-1"), "QVAPOR": (0.0, 0.05, "kg kg-1"),
    "U10": (-100.0, 100.0, "m s-1"), "V10": (-100.0, 100.0, "m s-1"),
    "RAINC": (0.0, 100000.0, "mm"), "RAINNC": (0.0, 100000.0, "mm"),
    "PBLH": (0.0, 10000.0, "m"),
}


def _first(values, mask):
    location = np.argwhere(mask)
    if not location.size:
        return None, None
    index = tuple(int(item) for item in location[0])
    return index, float(values[index])


def quality_control(dataset: xr.Dataset, *, limits=None, jump_sigma=12.0) -> list[QCIssue]:
    """Return explicit QC issues; an empty list means no configured issue was found."""
    configured = dict(DEFAULT_LIMITS); configured.update(limits or {})
    issues: list[QCIssue] = []
    for name, data in dataset.data_vars.items():
        if not np.issubdtype(data.dtype, np.number):
            continue
        values = np.asarray(data)
        bad = ~np.isfinite(values)
        if np.any(bad):
            index, value = _first(values, bad)
            issues.append(QCIssue("ERROR", name, "non-finite", f"{bad.sum()} NaN or infinite values; first at {index}", int(bad.sum()), index, value))
        fill = data.attrs.get("_FillValue", data.encoding.get("_FillValue"))
        if fill is not None:
            mask = values == fill
            if np.any(mask):
                index, value = _first(values, mask)
                issues.append(QCIssue("ERROR", name, "fill-value", f"{mask.sum()} values equal _FillValue {fill}; first at {index}", int(mask.sum()), index, value))
        if name in configured:
            low, high, units = configured[name]
            tolerance = max(1e-12, abs(high-low)*1e-12)
            mask = np.isfinite(values) & ((values < low-tolerance) | (values > high+tolerance))
            if np.any(mask):
                index, value = _first(values, mask)
                issues.append(QCIssue("ERROR", name, "physical-range", f"{mask.sum()} values outside [{low}, {high}] {units}; first value {value:g} at {index}", int(mask.sum()), index, value))
        if "Time" in data.dims and data.sizes.get("Time", 0) > 2:
            axis = data.get_axis_num("Time")
            series = np.nanmean(values, axis=tuple(i for i in range(values.ndim) if i != axis))
            increments = np.diff(series)
            scale = np.nanmedian(np.abs(increments-np.nanmedian(increments))) * 1.4826
            if np.isfinite(scale) and scale > 0:
                mask = np.abs(increments-np.nanmedian(increments)) > jump_sigma*scale
                if np.any(mask):
                    first = int(np.flatnonzero(mask)[0] + 1)
                    issues.append(QCIssue("WARNING", name, "temporal-jump", f"{mask.sum()} domain-mean jumps exceed {jump_sigma:g} robust standard deviations; first at Time={first}", int(mask.sum()), (first,), float(increments[first-1])))
    for name in ("QCLOUD", "QRAIN", "QICE", "QSNOW", "QGRAUP"):
        if name in dataset:
            values=np.asarray(dataset[name]); mask=np.isfinite(values)&(values < -1e-12)
            if np.any(mask):
                index,value=_first(values,mask); issues.append(QCIssue("ERROR",name,"negative-water",f"{mask.sum()} negative hydrometeor values; first {value:g} at {index}",int(mask.sum()),index,value))
    if "Time" in dataset.dims and "XTIME" in dataset:
        time=np.asarray(dataset.XTIME); delta=np.diff(time)
        numeric=delta/np.timedelta64(1,"s") if np.issubdtype(time.dtype,np.datetime64) else delta.astype(float)
        if numeric.size and (np.any(numeric <= 0) or not np.allclose(numeric,numeric[0])):
            issues.append(QCIssue("ERROR","XTIME","time-coordinate","timestamps are duplicated, reversed, or irregular"))
    return issues


def print_qc_report(issues: Iterable[QCIssue]) -> None:
    issues=list(issues)
    if not issues:
        print("WRF QC: PASS - no configured quality-control errors or warnings found.")
        return
    errors=sum(item.severity=="ERROR" for item in issues); warnings=sum(item.severity=="WARNING" for item in issues)
    print(f"WRF QC: {errors} error(s), {warnings} warning(s)")
    for number,item in enumerate(issues,1):
        print(f"  {number}. [{item.severity}] {item.variable} / {item.check}: {item.message}")
