"""
Helpers and notes for hifi-api-compatible HTTP services.

The public instance at https://hifi.geeked.wtf/ identifies itself with ``GET /``
(JSON: ``version``, ``Repo``). The API matches the schema documented in
`binimum/hifi-api <https://github.com/binimum/hifi-api>`_ (also implemented as
`monochrome-music/hifi-api-workers <https://github.com/monochrome-music/hifi-api-workers>`_).

Relevant endpoints for lossless audio (see upstream README for full schema):

- ``GET /`` — service metadata.
- ``GET /info?id=<tidal_track_id>`` — track metadata.
- ``GET /track?id=<tidal_track_id>&quality=HI_RES_LOSSLESS`` — stream manifest
  (JSON with base64 manifest; decoded payload includes ``audio/flac`` URLs).
- ``GET /trackManifests?id=<tidal_track_id>`` — richer manifests (preferred upstream).
- ``GET /search?query=...`` — discovery (params per upstream docs).

This package does not perform Tidal decryption or manifest parsing yet; wire
your own ``FlacSource`` or extend the HTTP client once you map local tags to
Tidal track IDs (e.g. via search).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

from music_flac import __version__

DEFAULT_HIFI_BASE = "https://hifi.geeked.wtf/"


@dataclass(frozen=True, slots=True)
class HifiClient:
    """Minimal read-only client for index and JSON endpoints."""

    base_url: str = DEFAULT_HIFI_BASE
    timeout_s: float = 30.0

    def _url(self, path: str) -> str:
        return urljoin(self.base_url.rstrip("/") + "/", path.lstrip("/"))

    def get_json(self, path: str) -> dict[str, Any]:
        url = self._url(path)
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
                # Some deployments block default Python urllib; behave like a normal client.
                "User-Agent": f"music-flac/{__version__} (+https://github.com/monochrome-music/hifi-api-workers)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"hifi HTTP {e.code} for {url}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"hifi request failed for {url}: {e}") from e
        return json.loads(raw)

    def service_info(self) -> dict[str, Any]:
        """``GET /`` — version string and source repo URL."""
        return self.get_json("/")
