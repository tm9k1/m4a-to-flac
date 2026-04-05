from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from music_flac.hifi import (
    HifiClient,
    pick_best_search_item,
    search_query_from_track,
    search_query_without_album,
    stream_urls_from_track_api_response,
)
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

    def fetch_flac(self, track: TrackRecord) -> bytes:
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
        last: Exception | None = None
        for quality in self.qualities:
            try:
                payload = self.client.get_track_json(tid, quality=quality)
                urls = stream_urls_from_track_api_response(payload)
                if not urls:
                    continue
                log.info("hifi: fetching quality=%s (%s URL(s))", quality, len(urls))
                return self.client.fetch_bytes(urls[0])
            except Exception as exc:
                last = exc
                log.debug("hifi: quality %s failed: %s", quality, exc)
        raise RuntimeError(
            f"Could not obtain stream URL or audio for track id {tid} ({q!r})"
        ) from last


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
    if not items:
        raise RuntimeError(f"hifi search returned no tracks for query: {last_q!r}")
    choice = pick_best_search_item(items, probe)
    assert choice is not None
    tid = int(choice["id"])
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    last: Exception | None = None
    for quality in DEFAULT_QUALITIES:
        try:
            payload = client.get_track_json(tid, quality=quality)
            urls = stream_urls_from_track_api_response(payload)
            if not urls:
                continue
            data = client.fetch_bytes(urls[0])
            out.write_bytes(data)
            return len(data)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"Could not download audio for track id {tid}") from last
