from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path

from music_flac.models import TrackRecord

log = logging.getLogger(__name__)

# YouTube video IDs are 11 characters in this alphabet.
_YT_ID_BODY = re.compile(r"^[A-Za-z0-9_-]{11}$")

# Trailing id patterns (applied repeatedly to the stem).
_YT_SUFFIX_PATTERNS = (
    re.compile(r"(?i)\s*\[\s*([A-Za-z0-9_-]{11})\s*\]\s*$"),
    re.compile(r"(?i)\s*\(\s*([A-Za-z0-9_-]{11})\s*\)\s*$"),
    re.compile(r"(?i)\s+([A-Za-z0-9_-]{11})\s*$"),
    re.compile(r"(?i)\s*[-–—_]+\s*([A-Za-z0-9_-]{11})\s*$"),
)

_INVALID_FS = re.compile(r'[\\/:*?"<>|]+')
_WS = re.compile(r"\s+")


def _is_youtube_id(token: str) -> bool:
    return bool(_YT_ID_BODY.match(token))


def strip_youtube_id_suffix(stem: str) -> str:
    """Remove a trailing YouTube-style 11-char id from a file stem."""
    s = stem.strip()
    changed = True
    while changed:
        changed = False
        for pat in _YT_SUFFIX_PATTERNS:
            m = pat.search(s)
            if not m:
                continue
            if not _is_youtube_id(m.group(1)):
                continue
            s = s[: m.start()]
            s = s.rstrip(" -–—_[]()")
            changed = True
            break
    return s.strip()


def sanitize_filename_segment(s: str) -> str:
    """Strip characters illegal on common filesystems; collapse whitespace."""
    s = _INVALID_FS.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s or "Unknown"


def effective_title(track: TrackRecord) -> str:
    raw_stem = strip_youtube_id_suffix(track.relative_path.stem)
    return sanitize_filename_segment(track.title or raw_stem)


def effective_artist(track: TrackRecord) -> str:
    return sanitize_filename_segment(track.artist or "Unknown Artist")


def effective_album(track: TrackRecord) -> str:
    return sanitize_filename_segment(track.album or "Unknown Album")


def format_at_tier(track: TrackRecord, tier: int) -> str:
    """tier 0: title; 1: title - artist; 2: title - artist - album."""
    title = effective_title(track)
    if tier <= 0:
        return title
    artist = effective_artist(track)
    if tier == 1:
        return f"{title} - {artist}"
    album = effective_album(track)
    return f"{title} - {artist} - {album}"


def _add_numeric_suffixes(stems: dict[TrackRecord, str]) -> dict[TrackRecord, str]:
    """For stems that still collide (case-insensitive), add ' (2)', ' (3)', …."""
    by_lower: dict[str, list[TrackRecord]] = defaultdict(list)
    for t, stem in stems.items():
        by_lower[stem.lower()].append(t)

    out = dict(stems)
    for _lower, group in by_lower.items():
        if len(group) <= 1:
            continue
        canonical = stems[group[0]]
        for i, t in enumerate(group):
            out[t] = canonical if i == 0 else f"{canonical} ({i + 1})"
    return out


def resolve_stems_in_folder(tracks: list[TrackRecord]) -> dict[TrackRecord, str]:
    """
    Within one output directory, assign unique stems (no extension) using
    title-only, then +artist, then +album, then numeric suffixes.
    """
    if not tracks:
        return {}
    tier = {t: 0 for t in tracks}

    def name_for(t: TrackRecord) -> str:
        return format_at_tier(t, tier[t])

    while True:
        buckets: dict[str, list[TrackRecord]] = defaultdict(list)
        for t in tracks:
            buckets[name_for(t).lower()].append(t)
        dups = [ts for ts in buckets.values() if len(ts) > 1]
        if not dups:
            stems = {t: name_for(t) for t in tracks}
            return _add_numeric_suffixes(stems)
        bumped = False
        for group in dups:
            for t in group:
                if tier[t] < 2:
                    tier[t] += 1
                    bumped = True
        if not bumped:
            stems = {t: name_for(t) for t in tracks}
            return _add_numeric_suffixes(stems)


def destination_relative_flac(track: TrackRecord, stem: str) -> Path:
    """Relative path under the FLAC root: same parent dirs as source, new leaf name."""
    return track.relative_path.parent / f"{stem}.flac"


def apply_name_template(track: TrackRecord, template: str) -> str:
    """Apply a custom naming template to a track record."""
    template_vars = {
        'artist': track.artist or 'Unknown Artist',
        'album': track.album or 'Unknown Album',
        'title': track.title or 'Unknown Title',
        'tracknumber': track.tracknumber or 0,
        'discnumber': track.discnumber or 1,
    }

    try:
        result = template.format(**template_vars)
        return sanitize_filename_segment(result)
    except (KeyError, ValueError) as e:
        log.warning("Invalid name template %r: %s. Using default naming.", template, e)
        return sanitize_filename_segment(track.title or 'Unknown Title')
