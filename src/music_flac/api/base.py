from __future__ import annotations

from typing import Protocol

from music_flac.models import TrackRecord


class FlacSource(Protocol):
    """Fetches FLAC payload for a track. Implementations call your external API."""

    def fetch_flac(self, track: TrackRecord) -> bytes:
        """Return raw FLAC bytes for this track."""
        ...
