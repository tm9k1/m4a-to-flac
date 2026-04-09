from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

from music_flac.models import TrackRecord

log = logging.getLogger(__name__)


def _payload(track: TrackRecord) -> dict[str, str | None]:
    return {
        "artist": track.artist,
        "album": track.album,
        "title": track.title,
        "tracknumber": track.tracknumber,
        "discnumber": track.discnumber,
        "relative_path": track.relative_path.as_posix(),
    }


@dataclass(slots=True)
class HttpFlacSource:
    """
    POST JSON to `api_url` and expect raw FLAC bytes in the response body.

    Set ``MUSIC_FLAC_API_URL`` and optionally ``MUSIC_FLAC_API_TOKEN`` (sent as
    ``Authorization: Bearer …``). Adjust this class if your API uses a different contract.
    """

    api_url: str
    token: str | None = None
    timeout_s: float = 120.0

    def fetch_flac(self, track: TrackRecord) -> bytes:
        data = json.dumps(_payload(track)).encode("utf-8")
        req = urllib.request.Request(
            self.api_url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            log.error("HTTP %s from API: %s", e.code, body[:500])
            raise
        except urllib.error.URLError as e:
            log.error("Request failed: %s", e)
            raise

    def fetch_metadata(self, track: TrackRecord) -> dict[str, object]:
        return {}

    def fetch_flac_with_metadata(self, track: TrackRecord) -> tuple[bytes, dict[str, object]]:
        return self.fetch_flac(track), {}

    def fetch_flac_with_metadata(self, track: TrackRecord) -> tuple[bytes, dict[str, object]]:
        return self.fetch_flac(track), {}
