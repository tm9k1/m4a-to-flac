from __future__ import annotations

import hashlib
import json
import logging
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Optional

from mutagen.flac import FLAC

from music_flac.api.base import FlacSource
from music_flac.metadata import apply_flac_metadata, needs_flac_metadata_update
from music_flac.models import ScanResult, TrackRecord
from music_flac.naming import _add_numeric_suffixes, destination_relative_flac, resolve_stems_in_folder
from music_flac.paths import posix_display

log = logging.getLogger(__name__)


def _get_state_file_path(flac_root: Path) -> Path:
    """Get the path to the sync state file."""
    return flac_root / ".music-flac-state.json"


def _load_sync_state(flac_root: Path) -> Dict[str, Dict]:
    """Load the previous sync state from disk."""
    state_file = _get_state_file_path(flac_root)
    if not state_file.exists():
        return {}

    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Could not load sync state: {e}")
        return {}


def _save_sync_state(flac_root: Path, state: Dict[str, Dict]) -> None:
    """Save the current sync state to disk."""
    state_file = _get_state_file_path(flac_root)
    try:
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning(f"Could not save sync state: {e}")


def _get_file_hash(file_path: Path) -> Optional[str]:
    """Get SHA256 hash of a file."""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return None


def _has_file_changed(state: Dict[str, Dict], relative_path: str, file_path: Path) -> bool:
    """Check if a file has been modified since last sync."""
    if relative_path not in state:
        return False

    old_hash = state[relative_path].get('hash')
    new_hash = _get_file_hash(file_path)

    return old_hash != new_hash


def _get_copied_dest_path(dest_flac: Path, source_path: Path) -> Path:
    """
    Get the destination path for a copied file, preserving original extension.
    If source is already .flac, return the flac path as-is.
    Otherwise, replace .flac suffix with original extension.
    """
    original_ext = source_path.suffix.lower()
    if original_ext == '.flac':
        return dest_flac
    return dest_flac.with_suffix(original_ext)


def _is_flac_exists(dest_flac: Path) -> bool:
    """Check if the .flac file (backend-fetched) exists."""
    return dest_flac.is_file()


def _is_original_exists(dest_flac: Path, source_path: Path) -> bool:
    """Check if a copied file with original extension exists."""
    copied_dest = _get_copied_dest_path(dest_flac, source_path)
    if copied_dest != dest_flac:
        return copied_dest.is_file()
    return False


def _find_available_dest_path(base_path: Path, source_path: Path) -> Path:
    """
    Find an available destination path, handling name conflicts.
    Uses the same fallback logic as naming.py for disambiguation.
    """
    # For now, just return the base path - we'll implement fallback later if needed
    # TODO: Implement name conflict resolution using naming.py logic
    return base_path


def mirror_plan(result: ScanResult, flac_root: Path, name_template: str | None = None) -> list[tuple[TrackRecord, Path]]:
    """
    Pairs each track with its output path under ``flac_root``.

    Preserves parent folders from the source tree; leaf names are disambiguated
    ``Title`` / ``Title - Artist`` / ``Title - Artist - Album`` (see ``naming``).
    """
    from music_flac.naming import apply_name_template

    flac_root = flac_root.resolve()

    if name_template:
        # Use custom template for all tracks, preserving per-folder uniqueness.
        by_parent: dict[Path, list[TrackRecord]] = defaultdict(list)
        for t in result.tracks:
            by_parent[t.relative_path.parent].append(t)

        stems: dict[TrackRecord, str] = {}
        for group in by_parent.values():
            template_stems = {
                t: apply_name_template(t, name_template).removesuffix('.flac')
                for t in group
            }
            stems.update(_add_numeric_suffixes(template_stems))

        out: list[tuple[TrackRecord, Path]] = []
        for t in result.tracks:
            rel = t.relative_path.parent / f"{stems[t]}.flac"
            out.append((t, flac_root / rel))
        return out
    else:
        # Use default naming logic
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


def _copy_file(source_path: Path, dest: Path) -> int:
    """
    Copy a file from source to destination using atomic write.
    Returns the number of bytes copied.
    """
    try:
        data = source_path.read_bytes()
        _atomic_write(dest, data)
        return len(data)
    except Exception as exc:
        raise IOError(f"Failed to copy {source_path} to {dest}: {exc}") from exc


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


def _prompt_user_action(track: TrackRecord, dest: Path, source_path: Path, copy_missing_tracks: bool) -> bool:
    print("\nTrack:", track.title or track.relative_path.stem)
    print("Artist:", track.artist or "Unknown")
    print("Album:", track.album or "Unknown")
    print("Source:", posix_display(track.source_path))
    print("Destination:", posix_display(dest))
    if _is_flac_exists(dest):
        print("Action: FLAC already exists; it will be skipped unless user modifications are detected.")
    elif _is_original_exists(dest, source_path):
        print("Action: Original exists; it will be skipped to preserve the source track.")
    else:
        action = "Download from hifi"
        if copy_missing_tracks:
            action += " (or copy original if download fails)"
        print("Action:", action)

    while True:
        choice = input("Proceed? [y/N/q] ").strip().lower()
        if not choice or choice == "n":
            return False
        if choice == "y":
            return True
        if choice == "q":
            raise KeyboardInterrupt("User aborted interactive sync")
        print("Please answer y, n, or q.")


def _is_valid_flac_file(dest: Path) -> bool:
    try:
        FLAC(dest)
        return True
    except Exception as exc:
        log.debug("File is not a valid FLAC: %s (%s)", dest, exc)
        return False




def _process_one_pair(
    track: TrackRecord,
    dest: Path,
    source: FlacSource,
    state: Dict[str, Dict],
    flac_root: Path,
    copy_missing_tracks: bool = False,
    enhance_metadata: bool = False,
) -> tuple[str, str | None, Path, int]:
    """
    Process one track/destination pair following the three-case logic.

    Returns (status, error_message_or_none, actual_dest_path, bytes_written).
    Status values: "downloaded", "copied", "metadata_updated", "skipped", "error".
    """
    relative_path_flac = str(dest.relative_to(flac_root))
    relative_path_original = str(_get_copied_dest_path(dest, track.source_path).relative_to(flac_root))

    # Check if user modified files
    if _is_flac_exists(dest) and _has_file_changed(state, relative_path_flac, dest):
        log.info("User modified FLAC file, skipping: %s", posix_display(dest))
        return ("skipped", None, dest, 0)

    original_path = _get_copied_dest_path(dest, track.source_path)
    if _is_original_exists(dest, track.source_path) and _has_file_changed(state, relative_path_original, original_path):
        log.info("User modified original file, skipping: %s", posix_display(original_path))
        return ("skipped", None, original_path, 0)

    # CASE 1: Nothing exists in dest dir
    if not _is_flac_exists(dest) and not _is_original_exists(dest, track.source_path):
        # Try to fetch from backend
        try:
            data, metadata = _fetch_flac_and_metadata(source, track)
            _atomic_write(dest, data)
            if metadata:
                try:
                    apply_flac_metadata(dest, metadata)
                except Exception as exc:
                    log.warning("Failed to embed metadata for %s: %s", dest, exc)
            return ("downloaded", None, dest, len(data))
        except Exception as exc:
            # CASE 1.1: Could not find FLAC
            if copy_missing_tracks:
                try:
                    available_dest = _find_available_dest_path(original_path, track.source_path)
                    sz = _copy_file(track.source_path, available_dest)
                    return ("copied", None, available_dest, sz)
                except Exception as copy_exc:
                    return ("error", f"{track.relative_path}: Backend fetch failed: {exc}; copy failed: {copy_exc}", dest, 0)
            else:
                return ("error", f"{track.relative_path}: {exc}", dest, 0)

    # CASE 2: FLAC exists
    elif _is_flac_exists(dest):
        if enhance_metadata and not _has_file_changed(state, relative_path_flac, dest):
            metadata = _fetch_metadata(source, track)
            if metadata and needs_flac_metadata_update(dest, metadata):
                try:
                    apply_flac_metadata(dest, metadata)
                    return ("metadata_updated", None, dest, dest.stat().st_size)
                except Exception as exc:
                    log.warning("Failed to embed enhanced metadata for %s: %s", dest, exc)
        return ("skipped", None, dest, 0)

    # CASE 3: Original exists (but not FLAC)
    else:
        # Do nothing - respect the source track
        return ("skipped", None, original_path, 0)


def sync_tracks(
    pairs: list[tuple[TrackRecord, Path]],
    source: FlacSource,
    flac_root: Path,
    *,
    dry_run: bool = False,
    copy_missing_tracks: bool = False,
    max_workers: int = 1,
    interactive: bool = False,
    name_template: str | None = None,
    enhance_metadata: bool = False,
) -> tuple[int, int, list[str]]:
    """
    For each (track, dest), fetch FLAC bytes and write to dest following the three-case logic.

    Returns (written, skipped, errors).
    """
    # Load previous state
    state = _load_sync_state(flac_root)
    new_state: Dict[str, Dict] = {}

    max_workers = max(1, int(max_workers))
    written = 0
    skipped = 0
    errors: list[str] = []

    # Interactive mode requires sequential processing
    if interactive:
        max_workers = 1

    # Process all pairs (no filtering - let _process_one_pair handle the logic)
    pending = pairs

    if dry_run:
        for track, dest in pending:
            if _is_flac_exists(dest):
                log.info("Would check metadata for: %s", posix_display(dest))
            elif _is_original_exists(dest, track.source_path):
                log.info("Would skip (original exists): %s", posix_display(_get_copied_dest_path(dest, track.source_path)))
            elif copy_missing_tracks:
                copied_dest = _get_copied_dest_path(dest, track.source_path)
                log.info("Would copy: %s", posix_display(copied_dest))
            else:
                log.info("Would fetch: %s", posix_display(dest))
        return 0, 0, errors

    if not pending:
        return written, skipped, errors

    if max_workers <= 1:
        for track, dest in pending:
            if interactive:
                try:
                    if not _prompt_user_action(track, dest, track.source_path, copy_missing_tracks):
                        skipped += 1
                        continue
                except KeyboardInterrupt as exc:
                    errors.append(str(exc))
                    log.warning("%s", exc)
                    break

            status, msg, dest_path, sz = _process_one_pair(
                track,
                dest,
                source,
                state,
                flac_root,
                copy_missing_tracks,
                enhance_metadata,
            )
            if status == "downloaded":
                written += 1
                log.info("Downloaded %s (%s bytes)", posix_display(dest_path), sz)
                # Record state
                rel_path = str(dest_path.relative_to(flac_root))
                new_state[rel_path] = {'hash': _get_file_hash(dest_path), 'type': 'flac'}
            elif status == "copied":
                written += 1
                log.info("Copied %s (%s bytes)", posix_display(dest_path), sz)
                # Record state
                rel_path = str(dest_path.relative_to(flac_root))
                new_state[rel_path] = {'hash': _get_file_hash(dest_path), 'type': 'original'}
            elif status == "metadata_updated":
                written += 1
                log.info("Updated metadata for %s", posix_display(dest_path))
                # Update state hash
                rel_path = str(dest_path.relative_to(flac_root))
                new_state[rel_path] = {'hash': _get_file_hash(dest_path), 'type': 'flac'}
            elif status == "skipped":
                skipped += 1
                # Record current state for skipped files
                if dest_path.exists():
                    rel_path = str(dest_path.relative_to(flac_root))
                    file_type = 'flac' if dest_path.suffix.lower() == '.flac' else 'original'
                    new_state[rel_path] = {'hash': _get_file_hash(dest_path), 'type': file_type}
            else:
                errors.append(msg or "")
                log.error("%s", msg)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_map = {
                pool.submit(
                    _process_one_pair,
                    track,
                    dest,
                    source,
                    state,
                    flac_root,
                    copy_missing_tracks,
                    enhance_metadata,
                ): (track, dest)
                for track, dest in pending
            }
            for fut in as_completed(future_map):
                status, msg, dest_path, sz = fut.result()
                if status == "downloaded":
                    written += 1
                    log.info("Downloaded %s (%s bytes)", posix_display(dest_path), sz)
                    rel_path = str(dest_path.relative_to(flac_root))
                    new_state[rel_path] = {'hash': _get_file_hash(dest_path), 'type': 'flac'}
                elif status == "copied":
                    written += 1
                    log.info("Copied %s (%s bytes)", posix_display(dest_path), sz)
                    rel_path = str(dest_path.relative_to(flac_root))
                    new_state[rel_path] = {'hash': _get_file_hash(dest_path), 'type': 'original'}
                elif status == "metadata_updated":
                    written += 1
                    log.info("Updated metadata for %s", posix_display(dest_path))
                    rel_path = str(dest_path.relative_to(flac_root))
                    new_state[rel_path] = {'hash': _get_file_hash(dest_path), 'type': 'flac'}
                elif status == "skipped":
                    skipped += 1
                    if dest_path.exists():
                        rel_path = str(dest_path.relative_to(flac_root))
                        file_type = 'flac' if dest_path.suffix.lower() == '.flac' else 'original'
                        new_state[rel_path] = {'hash': _get_file_hash(dest_path), 'type': file_type}
                else:
                    if msg:
                        errors.append(msg)
                        log.error("%s", msg)

    # Save new state
    _save_sync_state(flac_root, new_state)

    return written, skipped, errors
