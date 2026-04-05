"""
Client for hifi-api-compatible HTTP services (e.g. https://hifi.geeked.wtf/).

Schema reference: `binimum/hifi-api <https://github.com/binimum/hifi-api>`_ /
`monochrome-music/hifi-api-workers <https://github.com/monochrome-music/hifi-api-workers>`_.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from music_flac import __version__
from music_flac.models import TrackRecord
from music_flac.naming import strip_youtube_id_suffix

DEFAULT_HIFI_BASE = "https://hifi.geeked.wtf/"

_URL_IN_TEXT = re.compile(r"https://[^\s\"'<>]+")


def search_query_from_track(track: TrackRecord) -> str:
    parts = [track.artist, track.title, track.album]
    q = " ".join(p.strip() for p in parts if p and str(p).strip())
    if not q:
        q = strip_youtube_id_suffix(track.relative_path.stem)
    return q.strip()


def search_query_without_album(track: TrackRecord) -> str:
    """Same as full tag query but omits album (artist + title, then filename stem)."""
    parts = [track.artist, track.title]
    q = " ".join(p.strip() for p in parts if p and str(p).strip())
    if not q:
        q = strip_youtube_id_suffix(track.relative_path.stem)
    return q.strip()


def pick_best_search_item(
    items: list[dict[str, Any]],
    record: TrackRecord,
) -> dict[str, Any] | None:
    if not items:
        return None

    def norm(x: str | None) -> str:
        return (x or "").lower().strip()

    tt, ta, talb = norm(record.title), norm(record.artist), norm(record.album)
    if not tt and not ta and not talb:
        return items[0]

    best: dict[str, Any] | None = None
    best_score = -1
    for it in items:
        score = 0
        tit = norm(it.get("title"))
        art = norm((it.get("artist") or {}).get("name") if isinstance(it.get("artist"), dict) else None)
        alb = norm((it.get("album") or {}).get("title") if isinstance(it.get("album"), dict) else None)
        if tt:
            if tt == tit:
                score += 5
            elif tt in tit or tit in tt:
                score += 3
        if ta:
            if ta == art:
                score += 5
            elif ta in art or art in ta:
                score += 3
        if talb and talb in alb:
            score += 2
        if score > best_score:
            best_score = score
            best = it
    return best if best is not None else items[0]


def stream_urls_from_track_api_response(api_doc: dict[str, Any]) -> list[str]:
    """
    Parse ``GET /track`` JSON: base64 ``manifest`` may be JSON (tidal.bts) or DASH XML.
    Returns HTTP(S) URLs to fetch (first is usually the main stream).
    """
    data = api_doc.get("data")
    if not isinstance(data, dict):
        return []
    manifest_b64 = data.get("manifest")
    if not manifest_b64 or not isinstance(manifest_b64, str):
        return []
    mime = (data.get("manifestMimeType") or "").lower()
    try:
        raw = base64.b64decode(manifest_b64, validate=False)
    except (binascii.Error, ValueError):
        return []

    stripped = raw.lstrip()
    if stripped.startswith(b"{") or "tidal.bts" in mime:
        try:
            j = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            j = None
        if isinstance(j, dict):
            urls = j.get("urls")
            if isinstance(urls, list) and urls:
                return [str(u) for u in urls if isinstance(u, str)]

    text = raw.decode("utf-8", errors="replace")
    urls = _URL_IN_TEXT.findall(text)
    if not urls:
        return []
    # Prefer direct .flac links when present (simple CD-quality manifests).
    flac = [u for u in urls if ".flac" in u.lower()]
    if flac:
        return [flac[0]]
    return [urls[0]]


@dataclass(frozen=True, slots=True)
class HifiClient:
    """HTTP JSON + byte fetch for hifi-api-compatible bases."""

    base_url: str = DEFAULT_HIFI_BASE
    timeout_s: float = 120.0

    def _url(self, path: str) -> str:
        return urllib.parse.urljoin(self.base_url.rstrip("/") + "/", path.lstrip("/"))

    def _request(self, url: str, *, method: str = "GET", data: bytes | None = None) -> urllib.request.Request:
        return urllib.request.Request(
            url,
            method=method,
            data=data,
            headers={
                "Accept": "application/json" if method == "GET" and data is None else "*/*",
                "User-Agent": f"music-flac/{__version__} (+https://github.com/monochrome-music/hifi-api-workers)",
            },
        )

    def get_json(self, path: str) -> dict[str, Any]:
        url = self._url(path)
        req = self._request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"hifi HTTP {e.code} for {url}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"hifi request failed for {url}: {e}") from e
        return json.loads(raw)

    def fetch_bytes(self, url: str) -> bytes:
        req = self._request(url, method="GET")
        req.add_header("Accept", "*/*")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"stream HTTP {e.code} for {url}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"stream request failed for {url}: {e}") from e

    def service_info(self) -> dict[str, Any]:
        return self.get_json("/")

    def search_tracks(self, s: str, *, limit: int = 15) -> list[dict[str, Any]]:
        path = "search?" + urllib.parse.urlencode({"s": s, "limit": str(limit)})
        doc = self.get_json(path)
        data = doc.get("data")
        if isinstance(data, dict):
            items = data.get("items")
            if isinstance(items, list):
                return [x for x in items if isinstance(x, dict)]
        return []

    def get_track_json(self, track_id: int, *, quality: str = "LOSSLESS") -> dict[str, Any]:
        path = "track?" + urllib.parse.urlencode({"id": str(int(track_id)), "quality": quality})
        return self.get_json(path)
