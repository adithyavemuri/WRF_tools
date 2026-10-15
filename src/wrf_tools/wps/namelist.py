from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Any

_GROUP = re.compile(r"^\s*&(?P<name>\w+)", re.MULTILINE)
_QUOTED = re.compile(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"")
_ASSIGNMENT = re.compile(r"\b(?P<name>[A-Za-z]\w*)\s*=")


def _parse_value(value: str) -> Any:
    masked=_QUOTED.sub(lambda m:" "*len(m.group()),value)
    boundaries=[-1]+[m.start() for m in re.finditer(",",masked)]+[len(value)]
    parts=[value[a+1:b].strip() for a,b in zip(boundaries,boundaries[1:]) if value[a+1:b].strip()]
    parsed: list[Any] = []
    for part in parts:
        if (part.startswith("'") and part.endswith("'")) or (part.startswith('"') and part.endswith('"')):
            parsed.append(part[1:-1])
        elif part.lower() in (".true.", ".false."):
            parsed.append(part.lower() == ".true.")
        else:
            try:
                parsed.append(float(part.lower().replace("d","e")) if any(char in part.lower() for char in (".", "e", "d")) else int(part))
            except ValueError:
                parsed.append(part)
    return parsed[0] if len(parsed) == 1 else parsed


def read_namelist(path: str | Path) -> dict[str, dict[str, Any]]:
    """Parse simple scalar/list WPS namelists (quoted paths/comments supported).

    Not a complete Fortran grammar: indexed assignments, derived types and
    repetition syntax are rejected; use f90nml for those constructs.
    """
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    text=re.sub(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|![^\n]*",lambda m:"" if m.group().startswith("!") else m.group(),text)
    result: dict[str, dict[str, Any]] = {}
    groups = list(_GROUP.finditer(text))
    for index, match in enumerate(groups):
        end = groups[index + 1].start() if index + 1 < len(groups) else len(text)
        block = text[match.end():end]
        masked=_QUOTED.sub(lambda m:" "*len(m.group()),block)
        slash = masked.find("/")
        if slash >= 0:
            block = block[:slash]; masked=masked[:slash]
        if re.search(r"\w+\s*\([^)]*\)\s*=|\b\d+\s*\*",masked):
            raise ValueError("Indexed/repetition namelist syntax requires f90nml")
        assignments=list(_ASSIGNMENT.finditer(masked)); values={}
        for i,item in enumerate(assignments):
            stop=assignments[i+1].start() if i+1<len(assignments) else len(block)
            values[item.group("name").lower()]=_parse_value(block[item.end():stop].strip().rstrip(","))
        result[match.group("name").lower()] = values
    return result


def update_namelist_dates(
    path: str | Path,
    start: datetime,
    end: datetime,
    *,
    domains: int,
    output: str | Path | None = None,
) -> Path:
    """Replace simple start_date/end_date assignment lines for all selected domains.

    output=None updates the source. Intended for conventional WPS files with
    one date assignment per line, not a general lossless Fortran namelist editor.
    """
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
