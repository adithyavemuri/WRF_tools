from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class WRFSource:
    paths: tuple[Path, ...]
    domain: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    chunks: dict[str, int] | None = field(default=None, compare=False)

    @classmethod
    def from_paths(cls, *paths: str | Path, **kwargs: object) -> "WRFSource":
        return cls(paths=tuple(Path(path) for path in paths), **kwargs)


@dataclass(frozen=True)
class ExecutableConfig:
    executable: Path
    working_directory: Path
    environment: dict[str, str] = field(default_factory=dict, compare=False)
