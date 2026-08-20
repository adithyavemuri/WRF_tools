from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

_WRFOUT_PATTERN = re.compile(
    r"^wrfout_(?P<domain>d\d{2})_(?P<date>\d{4}-\d{2}-\d{2})_(?P<time>\d{2}[:_]\d{2}[:_]\d{2})"
)


def _timestamp(path: Path) -> datetime | None:
    match = _WRFOUT_PATTERN.match(path.name)
    if not match:
        return None
    value = f"{match.group('date')} {match.group('time').replace('_', ':')}"
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def discover_wrfout(
    directory: str | Path,
    *,
    domain: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    recursive: bool = False,
) -> list[Path]:
    """Discover WRF output files without assuming a particular case layout."""
    root = Path(directory).expanduser()
    if not root.is_dir():
        raise NotADirectoryError(root)
    normalized_domain = None
    if domain:
        normalized_domain = domain if domain.startswith("d") else f"d{int(domain):02d}"
    iterator = root.rglob("wrfout_*") if recursive else root.glob("wrfout_*")
    result: list[Path] = []
    for path in iterator:
        if not path.is_file():
            continue
        match = _WRFOUT_PATTERN.match(path.name)
        if not match:
            continue
        if normalized_domain and match.group("domain") != normalized_domain:
            continue
        timestamp = _timestamp(path)
        if start and timestamp and timestamp < start:
            continue
        if end and timestamp and timestamp > end:
            continue
        result.append(path)
    return sorted(result, key=lambda item: (_timestamp(item) or datetime.min, item.name))
