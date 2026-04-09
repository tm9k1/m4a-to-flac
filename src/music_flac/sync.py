from __future__ import annotations

import logging
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from mutagen.flac import FLAC

from music_flac.api.base import FlacSource
from music_flac.metadata import apply_flac_metadata, needs_flac_metadata_update
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


def _fetch_flac_and_metadata(
    source: FlacSource,
    track: TrackRecord,
) -> tuple[bytes, dict[str, object] | None]:
    if hasattr(source, "fetch_flac_with_metadata"):
        result = source.fetch_flac_with_metadata(track)
        if isinstance(result, tuple) and len(result) == 2:
            data, metadata = result
            if isinstance(metadata, dict):
                return data, metadata
            return data, None
    return source.fetch_flac(track), None


def _is_valid_flac_file(dest: Path) -> bool:
    try:
        FLAC(dest)
        return True
    except Exception:
        return False


def _fetch_metadata(source: FlacSource, track: TrackRecord) -> dict[str, object] | None:
    if hasattr(source, "fetch_metadata"):
        try:
            metadata = source.fetch_metadata(track)
            if isinstance(metadata, dict):
                return metadata
        except Exception as exc:
            log.warning("Could not fetch metadata for %s: %s", track.relative_path, exc)
            return None

    if hasattr(source, "fetch_flac_with_metadata"):
        try:
            result = source.fetch_flac_with_metadata(track)
            if isinstance(result, tuple) and len(result) == 2:
                _, metadata = result
                if isinstance(metadata, dict):
                    return metadata
        except Exception as exc:
            log.warning("Could not fetch metadata for %s: %s", track.relative_path, exc)
    return None


def _update_existing_metadata_if_needed(
    track: TrackRecord,
    dest: Path,
    source: FlacSource,
) -> bool:
    metadata = _fetch_metadata(source, track)
    if not metadata:
        return False

    try:
        if not needs_flac_metadata_update(dest, metadata):
            return False
    except Exception as exc:
        log.warning("Could not read existing FLAC for %s: %s", dest, exc)
        return False

    try:
        apply_flac_metadata(dest, metadata)
        return True
    except Exception as exc:
        log.warning("Failed to update metadata for %s: %s", dest, exc)
        return False


def _process_one_pair(
    track: TrackRecord,
    dest: Path,
    source: FlacSource,
) -> tuple[bool, str | None, Path, int]:
    """
    Fetch and write one track. Returns (ok, error_message_or_none, dest, byte_len).
    """
    try:
        data, metadata = _fetch_flac_and_metadata(source, track)
        _atomic_write(dest, data)
        if metadata:
            try:
                apply_flac_metadata(dest, metadata)
            except Exception as exc:
                log.warning("Failed to embed metadata for %s: %s", dest, exc)
        return (True, None, dest, len(data))
    except Exception as exc:
        return (False, f"{track.relative_path}: {exc}", dest, 0)


def sync_tracks(
    pairs: list[tuple[TrackRecord, Path]],
    source: FlacSource,
    *,
    dry_run: bool = False,
    skip_existing: bool = True,
    max_workers: int = 1,
) -> tuple[int, int, list[str]]:
    """
    For each (track, dest), fetch FLAC bytes and write to dest.

    When ``max_workers`` > 1 and not ``dry_run``, downloads run in a thread pool
    (I/O-bound network + disk). Skipped and dry-run paths stay deterministic.

    Returns (written, skipped, errors).
    """
    max_workers = max(1, int(max_workers))
    written = 0
    skipped = 0
    errors: list[str] = []
    pending: list[tuple[TrackRecord, Path]] = []

    for track, dest in pairs:
        if skip_existing and dest.is_file() and dest.stat().st_size > 0:
            if _is_valid_flac_file(dest) and _update_existing_metadata_if_needed(track, dest, source):
                written += 1
                log.info("Updated metadata for existing: %s", posix_display(dest))
                continue
            skipped += 1
            log.info("Skip existing: %s", posix_display(dest))
            continue
        pending.append((track, dest))

    if dry_run:
        for track, dest in pending:
            log.info("Would write: %s", posix_display(dest))
        written = len(pending)
        return written, skipped, errors

    if not pending:
        return written, skipped, errors

    if max_workers <= 1:
        for track, dest in pending:
            ok, msg, dest_path, sz = _process_one_pair(track, dest, source)
            if ok:
                written += 1
                log.info("Wrote %s (%s bytes)", posix_display(dest_path), sz)
            else:
                errors.append(msg or "")
                log.error("%s", msg)
        return written, skipped, errors

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {
            pool.submit(_process_one_pair, track, dest, source): (track, dest)
            for track, dest in pending
        }
        for fut in as_completed(future_map):
            ok, msg, dest_path, sz = fut.result()
            if ok:
                written += 1
                log.info("Wrote %s (%s bytes)", posix_display(dest_path), sz)
            else:
                if msg:
                    errors.append(msg)
                    log.error("%s", msg)

    return written, skipped, errors
