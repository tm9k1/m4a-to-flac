from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TrackRecord:
    """One audio file under the source library root, plus parsed tags."""

    source_path: Path
    relative_path: Path
    artist: str | None
    album: str | None
    title: str | None
    tracknumber: str | None
    discnumber: str | None
    codec: str | None = None
    errors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class ScanResult:
    root: Path
    tracks: list[TrackRecord]
