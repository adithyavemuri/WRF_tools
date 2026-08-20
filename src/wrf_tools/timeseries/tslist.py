from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable

from ..types import Station

_STATION = re.compile(
    r"^\s*(?P<name>.{1,25}?)\s+(?P<id>\S{1,7})\s+"
    r"(?P<lat>[+-]?\d+(?:\.\d+)?)\s+(?P<lon>[+-]?\d+(?:\.\d+)?)\s*$"
)


def read_tslist(path: str | Path) -> list[Station]:
    stations: list[Station] = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or line.lstrip().startswith(("#", "!")):
            continue
        match = _STATION.match(line)
        if match:
            stations.append(
                Station(
                    station_id=match.group("id"),
                    name=match.group("name").strip(),
                    latitude=float(match.group("lat")),
                    longitude=float(match.group("lon")),
                )
            )
    return stations


def write_tslist(stations: Iterable[Station], path: str | Path) -> Path:
    destination = Path(path)
    lines = ["#-----------------------------------------------#", "#  Name                     ID      LAT      LON  #"]
    for station in stations:
        name = (station.name or station.station_id)[:25]
        lines.append(
            f"{name:<25} {station.station_id:<7} {station.latitude:9.4f} {station.longitude:10.4f}"
        )
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return destination
