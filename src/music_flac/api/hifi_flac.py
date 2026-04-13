from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from music_flac.hifi import (
    HifiClient,
    pick_best_search_item,
    search_query_from_track,
    search_query_title_only,
    search_query_title_without_parens,
    search_query_without_album,
    stream_urls_from_track_api_response,
)
from music_flac.metadata import apply_flac_metadata
from music_flac.models import TrackRecord

log = logging.getLogger(__name__)

DEFAULT_QUALITIES = ("LOSSLESS", "HI_RES_LOSSLESS", "HIGH")


@dataclass(slots=True)
class HifiFlacSource:
    """
    hifi-api: ``GET /search?s=…`` → ``GET /track?id=…&quality=…`` → decode manifest → GET stream URL.

    See `binimum/hifi-api <https://github.com/binimum/hifi-api>`_.
    """

    client: HifiClient
    qualities: tuple[str, ...] = DEFAULT_QUALITIES

    def set_quality_preference(self, quality: str) -> None:
        """Set the preferred quality level for downloads."""
        if quality not in DEFAULT_QUALITIES:
            raise ValueError(f"Invalid quality: {quality}. Must be one of {DEFAULT_QUALITIES}")
        self.qualities = (quality,) + tuple(q for q in DEFAULT_QUALITIES if q != quality)

    def fetch_flac(self, track: TrackRecord) -> bytes:
        data, _ = self.fetch_flac_with_metadata(track)
        return data

    def fetch_metadata(self, track: TrackRecord) -> dict[str, object]:
        choice, tid = self._resolve_track(track)
        payload = self._find_track_payload(tid)
        return self._metadata_from_track_json(payload, track)

    def fetch_flac_with_metadata(self, track: TrackRecord) -> tuple[bytes, dict[str, object]]:
        choice, tid = self._resolve_track(track)
        payload = self._find_track_payload(tid)
        metadata = self._metadata_from_track_json(payload, track)
        urls = stream_urls_from_track_api_response(payload)
        if not urls:
            raise RuntimeError(f"Could not obtain stream URL for track id {tid}")
        log.info("hifi: fetching audio for track id %s (%s URL(s))", tid, len(urls))
        return self.client.fetch_bytes(urls[0]), metadata

    def _resolve_track(self, track: TrackRecord) -> tuple[dict[str, Any], int]:
        q = search_query_from_track(track)
        if not q:
            raise RuntimeError(f"No search query derivable for {track.relative_path!s}")
        items = self.client.search_tracks(q)
        if not items and track.album and str(track.album).strip():
            q2 = search_query_without_album(track)
            if q2 and q2 != q:
                log.info(
                    "hifi: empty search for %r; retrying without album as %r",
                    q,
                    q2,
                )
                q = q2
                items = self.client.search_tracks(q)
        if not items:
            q3 = search_query_title_only(track)
            if q3 and q3 != q:
                log.info(
                    "hifi: empty search for %r; retrying with title only as %r",
                    q,
                    q3,
                )
                q = q3
                items = self.client.search_tracks(q)
        if not items:
            q4 = search_query_title_without_parens(track)
            if q4 and q4 != q:
                log.info(
                    "hifi: empty search for %r; retrying with title without parentheses as %r",
                    q,
                    q4,
                )
                q = q4
                items = self.client.search_tracks(q)
        if not items:
            raise RuntimeError(f"hifi search returned no tracks for query: {q!r}")
        choice = pick_best_search_item(items, track)
        assert choice is not None
        tid = int(choice["id"])
        log.info(
            "hifi: using track id %s (%s — %s)",
            tid,
            (choice.get("artist") or {}).get("name", "?"),
            choice.get("title", "?"),
        )
        return choice, tid

    def _find_track_payload(self, tid: int) -> dict[str, Any]:
        last: Exception | None = None
        for quality in self.qualities:
            try:
                payload = self.client.get_track_json(tid, quality=quality)
                if stream_urls_from_track_api_response(payload):
                    return payload
            except Exception as exc:
                last = exc
                log.debug("hifi: quality %s failed: %s", quality, exc)
        raise RuntimeError(f"Could not obtain track payload for id {tid}") from last

    def _metadata_from_track_json(
        self,
        payload: dict[str, Any],
        track: TrackRecord,
    ) -> dict[str, object]:
        data = payload.get("data")
        if not isinstance(data, dict):
            return {}

        tags: dict[str, str] = {}
        tags["TITLE"] = self._coalesce(
            data,
            ["title", "name"],
            default=track.title,
        )
        tags["ARTIST"] = self._coalesce(
            data.get("artist", {}),
            ["name", "title"],
            default=track.artist,
        )
        tags["ALBUM"] = self._coalesce(
            data.get("album", {}),
            ["title", "name"],
            default=track.album,
        )
        tags["TRACKNUMBER"] = self._coalesce(
            data,
            ["trackNumber", "track_number", "track"],
            default=track.tracknumber,
        )
        tags["DISCNUMBER"] = self._coalesce(
            data,
            ["discNumber", "disc_number", "disc"],
            default=track.discnumber,
        )
        date = self._coalesce(
            data,
            ["releaseDate", "year", "release_date"],
        )
        if date:
            tags["DATE"] = date
        genre = self._coalesce(data, ["genre"])
        if genre:
            tags["GENRE"] = genre

        pictures: list[dict[str, object]] = []
        for url in self._image_urls_from_hifi_data(data):
            try:
                image_data, content_type = self.client.fetch_bytes_with_content_type(url)
            except Exception:
                continue
            pictures.append(
                {
                    "data": image_data,
                    "mime": content_type,
                    "url": url,
                    "type": 3,
                    "desc": "Cover art",
                }
            )
            break

        return {"tags": tags, "pictures": pictures}

    def _coalesce(
        self,
        source: Any,
        keys: list[str],
        default: str | None = None,
    ) -> str | None:
        if isinstance(source, dict):
            for key in keys:
                value = source.get(key)
                if value is not None:
                    return str(value)
        return str(default) if default is not None else None

    def _image_urls_from_hifi_data(self, data: dict[str, Any]) -> list[str]:
        candidates: list[str] = []

        def add_url(value: Any) -> None:
            if isinstance(value, str) and value.strip():
                candidates.append(value.strip())

        def scan_object(obj: Any) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key.lower() in {
                        "cover",
                        "picture",
                        "image",
                        "coverurl",
                        "pictureurl",
                        "imageurl",
                        "cover_url",
                        "picture_url",
                        "image_url",
                    }:
                        add_url(value)
                    elif isinstance(value, (dict, list)):
                        scan_object(value)
            elif isinstance(obj, list):
                for item in obj:
                    scan_object(item)

        album = data.get("album")
        artist = data.get("artist")
        scan_object(album)
        scan_object(artist)
        scan_object(data)
        return candidates


def fetch_one_track_to_path(
    client: HifiClient,
    *,
    search_query: str,
    output: Path | str,
    title: str | None = None,
    artist: str | None = None,
    album: str | None = None,
) -> int:
    """
    Run search, pick best match vs optional tags, download first resolved stream, write ``output``.
    Returns byte length written.
    """
    probe = TrackRecord(
        source_path=Path("."),
        relative_path=Path("probe.mp3"),
        artist=artist,
        album=album,
        title=title,
        tracknumber=None,
        discnumber=None,
    )
    last_q = search_query
    items = client.search_tracks(search_query)
    if not items and album and str(album).strip():
        alt = " ".join(p.strip() for p in (artist, title) if p and str(p).strip())
        if alt and alt.strip() != search_query.strip():
            log.info(
                "hifi: empty search for %r; retrying without album as %r",
                search_query,
                alt,
            )
            last_q = alt
            items = client.search_tracks(alt)
    if not items and title and str(title).strip():
        alt2 = str(title).strip()
        if alt2 != last_q:
            log.info(
                "hifi: empty search for %r; retrying with title only as %r",
                last_q,
                alt2,
            )
            last_q = alt2
            items = client.search_tracks(alt2)
    if not items and title:
        alt3 = re.sub(r'\([^)]*\)', '', str(title)).strip()
        if alt3 and alt3 != last_q:
            log.info(
                "hifi: empty search for %r; retrying with title without parentheses as %r",
                last_q,
                alt3,
            )
            last_q = alt3
            items = client.search_tracks(alt3)
    if not items:
        raise RuntimeError(f"hifi search returned no tracks for query: {last_q!r}")
    choice = pick_best_search_item(items, probe)
    assert choice is not None
    tid = int(choice["id"])
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    last: Exception | None = None
    src = HifiFlacSource(client=client)
    for quality in DEFAULT_QUALITIES:
        try:
            payload = client.get_track_json(tid, quality=quality)
            urls = stream_urls_from_track_api_response(payload)
            if not urls:
                continue
            data = client.fetch_bytes(urls[0])
            out.write_bytes(data)
            try:
                metadata = src._metadata_from_track_json(payload, probe)
                if metadata:
                    apply_flac_metadata(out, metadata)
            except Exception as exc:
                log.warning("Failed to embed metadata for %s: %s", out, exc)
            return len(data)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"Could not download audio for track id {tid}") from last
