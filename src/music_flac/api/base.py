from __future__ import annotations

from typing import Protocol

from music_flac.models import TrackRecord


class FlacSource(Protocol):
    """Fetches FLAC payload for a track. Implementations call your external API."""

    def fetch_flac(self, track: TrackRecord) -> bytes:
        """Return raw FLAC bytes for this track."""
        ...

    def fetch_metadata(self, track: TrackRecord) -> dict[str, object]:
        """Return optional metadata that can be written into an existing FLAC file."""
        ...

    def fetch_flac_with_metadata(self, track: TrackRecord) -> tuple[bytes, dict[str, object]]:
        """Return raw FLAC bytes and optional metadata for embedding into the downloaded file."""
        ...

    def fetch_flac_with_metadata(self, track: TrackRecord) -> tuple[bytes, dict[str, object]]:
        """Return raw FLAC bytes and optional metadata for embedding into the downloaded file."""
        ...
