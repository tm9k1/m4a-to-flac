from __future__ import annotations

import logging

from music_flac.models import TrackRecord

log = logging.getLogger(__name__)

# Not a valid FLAC stream; for pipeline tests only. Replace with real API for production.
STUB_MARKER = b"# music-flac stub - not audio\n"


class StubFlacSource:
    """Returns placeholder bytes so layout and writes can be tested without a server."""

    def fetch_flac(self, track: TrackRecord) -> bytes:
        meta = f"{track.artist!s} / {track.album!s} / {track.title!s}\n".encode("utf-8")
        log.debug("Stub fetch for %s", track.relative_path)
        return STUB_MARKER + meta
