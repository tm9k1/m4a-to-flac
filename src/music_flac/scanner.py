from __future__ import annotations

import logging
from pathlib import Path

from mutagen import File as MutagenFile

from music_flac.layout import is_audio_file, relative_under
from music_flac.models import ScanResult, TrackRecord

log = logging.getLogger(__name__)


def _first_tag(audio, *keys: str) -> str | None:
    if audio is None or not audio.tags:
        return None
    tags = audio.tags
    for key in keys:
        val = tags.get(key)
        if val is None:
            continue
        if isinstance(val, list) and val:
            return str(val[0])
        return str(val)
    return None


def _parse_track(path: Path, root: Path) -> TrackRecord:
    rel = relative_under(root, path.resolve())
    errors: list[str] = []
    artist = album = title = tracknumber = discnumber = codec = None
    try:
        audio = MutagenFile(path)
        if audio is not None:
            codec = type(audio).__name__
            artist = _first_tag(audio, "TPE1", "ARTIST", "\xa9ART")
            album = _first_tag(audio, "TALB", "ALBUM", "\xa9alb")
            title = _first_tag(audio, "TIT2", "TITLE", "\xa9nam")
            tracknumber = _first_tag(audio, "TRCK", "TRACKNUMBER", "TRACK")
            discnumber = _first_tag(audio, "TPOS", "DISCNUMBER", "DISC")
    except Exception as exc:  # mutagen can raise broadly for corrupt files
        errors.append(str(exc))
        log.warning("Could not read tags for %s: %s", path, exc)

    return TrackRecord(
        source_path=path,
        relative_path=rel,
        artist=artist,
        album=album,
        title=title,
        tracknumber=tracknumber,
        discnumber=discnumber,
        codec=codec,
        errors=tuple(errors),
    )


def scan_library(root: Path) -> ScanResult:
    """Walk `root` recursively; collect audio files and parse metadata."""
    root = root.resolve()
    tracks: list[TrackRecord] = []

    for path in sorted(root.rglob("*")):
        if path.is_file() and is_audio_file(path):
            tracks.append(_parse_track(path, root))

    return ScanResult(root=root, tracks=tracks)
