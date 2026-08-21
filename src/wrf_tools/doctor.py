"""Environment and optional-dependency diagnostics for WRF Tools."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
import platform
import sys


@dataclass(frozen=True)
class DependencyStatus:
    capability: str
    package: str
    required: bool
    installed: bool
    version: str | None
    detail: str


DEPENDENCIES = (
    ("Core arrays", "numpy", "numpy", True),
    ("Labelled datasets", "xarray", "xarray", True),
    ("NetCDF I/O", "netCDF4", "netCDF4", False),
    ("Scientific diagnostics and filtering", "scipy", "scipy", False),
    ("Plotting", "matplotlib", "matplotlib", False),
    ("Map projections", "cartopy", "Cartopy", False),
    ("Coordinate transforms", "pyproj", "pyproj", False),
    ("PDF reports", "reportlab", "reportlab", False),
    ("Native WRF diagnostics", "wrf", "wrf-python", False),
)


def dependency_status() -> list[DependencyStatus]:
    """Return import and version status for core and optional dependencies."""
    statuses: list[DependencyStatus] = []
    for capability, module_name, distribution, required in DEPENDENCIES:
        try:
            import_module(module_name)
            try:
                installed_version = version(distribution)
            except PackageNotFoundError:
                installed_version = "unknown"
            statuses.append(DependencyStatus(
                capability, distribution, required, True, installed_version, "available"
            ))
        except Exception as exc:  # Import errors can include missing native libraries.
            statuses.append(DependencyStatus(
                capability, distribution, required, False, None,
                f"{type(exc).__name__}: {exc}",
            ))
    return statuses


def environment_report() -> dict[str, object]:
    """Return a serializable platform and dependency report."""
    return {
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "dependencies": [asdict(item) for item in dependency_status()],
    }


def print_environment_report(*, include_optional: bool = True) -> bool:
    """Print a readable report and return whether all checked requirements pass."""
    report = environment_report()
    print(f"Python:   {report['python']}")
    print(f"Platform: {report['platform']}")
    print("Dependencies:")
    checked = []
    for item in report["dependencies"]:
        if not include_optional and not item["required"]:
            continue
        checked.append(item)
        state = "PASS" if item["installed"] else ("FAIL" if item["required"] else "OPTIONAL")
        installed_version = f" {item['version']}" if item["version"] else ""
        print(f"  [{state:8}] {item['capability']}: {item['package']}{installed_version}")
        if not item["installed"]:
            print(f"             {item['detail']}")
    return all(item["installed"] or not item["required"] for item in checked)
