from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Any

_GROUP = re.compile(r"^\s*&(?P<name>\w+)", re.MULTILINE)
_ASSIGNMENT = re.compile(r"(?P<name>\w+)\s*=\s*(?P<value>.*?)(?=\n\s*\w+\s*=|\n\s*/)", re.DOTALL)


def _parse_value(value: str) -> Any:
    parts = [part.strip() for part in value.replace("\n", " ").split(",") if part.strip()]
    parsed: list[Any] = []
    for part in parts:
        if (part.startswith("'") and part.endswith("'")) or (part.startswith('"') and part.endswith('"')):
            parsed.append(part[1:-1])
        elif part.lower() in (".true.", ".false."):
            parsed.append(part.lower() == ".true.")
        else:
            try:
                parsed.append(float(part) if any(char in part.lower() for char in (".", "e", "d")) else int(part))
            except ValueError:
                parsed.append(part)
    return parsed[0] if len(parsed) == 1 else parsed


def read_namelist(path: str | Path) -> dict[str, dict[str, Any]]:
    """Parse common WPS/WRF namelist values without requiring f90nml."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    result: dict[str, dict[str, Any]] = {}
    groups = list(_GROUP.finditer(text))
    for index, match in enumerate(groups):
        end = groups[index + 1].start() if index + 1 < len(groups) else len(text)
        block = text[match.end():end]
        slash = block.find("/")
        if slash >= 0:
            block = block[:slash + 1]
        result[match.group("name")] = {
            item.group("name"): _parse_value(item.group("value"))
            for item in _ASSIGNMENT.finditer(block)
        }
    return result


def update_namelist_dates(
    path: str | Path,
    start: datetime,
    end: datetime,
    *,
    domains: int,
    output: str | Path | None = None,
) -> Path:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    replacements = {
        "start_date": start.strftime("%Y-%m-%d_%H:%M:%S"),
        "end_date": end.strftime("%Y-%m-%d_%H:%M:%S"),
    }
    for name, value in replacements.items():
        repeated = ", ".join(f"'{value}'" for _ in range(domains))
        text, count = re.subn(rf"(?m)^(\s*{name}\s*=).*?$", rf"\1 {repeated},", text)
        if count == 0:
            raise KeyError(f"{name} was not found in {source}")
    destination = Path(output) if output else source
    destination.write_text(text, encoding="utf-8")
    return destination
