from __future__ import annotations

import logging
import tempfile
from collections import defaultdict
from pathlib import Path

from music_flac.api.base import FlacSource
from music_flac.models import ScanResult, TrackRecord
from music_flac.naming import destination_relative_flac, resolve_stems_in_folder
from music_flac.paths import posix_display

log = logging.getLogger(__name__)


def mirror_plan(result: ScanResult, flac_root: Path) -> list[tuple[TrackRecord, Path]]:
    """
    Pairs each track with its output path under ``flac_root``.

    Preserves parent folders from the source tree; leaf names are disambiguated
    ``Title`` / ``Title - Artist`` / ``Title - Artist - Album`` (see ``naming``).
    """
    flac_root = flac_root.resolve()
    by_parent: dict[Path, list[TrackRecord]] = defaultdict(list)
    for t in result.tracks:
        by_parent[t.relative_path.parent].append(t)

    stems: dict[TrackRecord, str] = {}
    for group in by_parent.values():
        stems.update(resolve_stems_in_folder(group))

    out: list[tuple[TrackRecord, Path]] = []
    for t in result.tracks:
        rel = destination_relative_flac(t, stems[t])
        out.append((t, flac_root / rel))
    return out


def _atomic_write(target: Path, data: bytes) -> None:
    import os

    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".flac-", suffix=".tmp", dir=target.parent)
    tmp_path = Path(tmp)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        if target.exists():
            target.unlink()
        tmp_path.replace(target)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def sync_tracks(
    pairs: list[tuple[TrackRecord, Path]],
    source: FlacSource,
    *,
    dry_run: bool = False,
    skip_existing: bool = True,
) -> tuple[int, int, list[str]]:
    """
    For each (track, dest), fetch FLAC bytes and write to dest.

    Returns (written, skipped, errors).
    """
    written = 0
    skipped = 0
    errors: list[str] = []

    for track, dest in pairs:
        if skip_existing and dest.is_file() and dest.stat().st_size > 0:
            skipped += 1
            log.info("Skip existing: %s", posix_display(dest))
            continue
        if dry_run:
            log.info("Would write: %s", posix_display(dest))
            written += 1
            continue
        try:
            data = source.fetch_flac(track)
            _atomic_write(dest, data)
            written += 1
            log.info("Wrote %s (%s bytes)", posix_display(dest), len(data))
        except Exception as exc:
            msg = f"{track.relative_path}: {exc}"
            errors.append(msg)
            log.error("%s", msg)

    return written, skipped, errors
