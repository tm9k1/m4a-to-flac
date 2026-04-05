import base64
import json
from pathlib import Path
from unittest.mock import MagicMock

from music_flac.api.hifi_flac import HifiFlacSource
from music_flac.hifi import (
    pick_best_search_item,
    search_query_from_track,
    search_query_without_album,
    stream_urls_from_track_api_response,
)
from music_flac.models import TrackRecord


def test_stream_urls_from_json_manifest():
    inner = {
        "mimeType": "audio/flac",
        "codecs": "flac",
        "urls": ["https://cdn.example/track.flac?token=1"],
    }
    b64 = base64.b64encode(json.dumps(inner).encode()).decode()
    doc = {"data": {"manifest": b64, "manifestMimeType": "application/vnd.tidal.bts"}}
    urls = stream_urls_from_track_api_response(doc)
    assert urls == ["https://cdn.example/track.flac?token=1"]


def test_pick_best_prefers_matching_tags():
    items = [
        {
            "id": 1,
            "title": "Wrong",
            "artist": {"name": "X"},
            "album": {"title": "A"},
        },
        {
            "id": 2,
            "title": "Wonderwall",
            "artist": {"name": "Oasis"},
            "album": {"title": "Morning Glory"},
        },
    ]
    rec = TrackRecord(
        source_path=Path("/x"),
        relative_path=Path("a.mp3"),
        artist="Oasis",
        album="(What's the Story) Morning Glory?",
        title="Wonderwall",
        tracknumber=None,
        discnumber=None,
    )
    best = pick_best_search_item(items, rec)
    assert best["id"] == 2


def test_search_query_without_album_omits_album_tag():
    t = TrackRecord(
        source_path=Path("/x"),
        relative_path=Path("a.mp3"),
        artist="Oasis",
        album="Morning Glory",
        title="Wonderwall",
        tracknumber=None,
        discnumber=None,
    )
    assert "Morning" in search_query_from_track(t)
    assert "Morning" not in search_query_without_album(t)
    assert "Wonderwall" in search_query_without_album(t)


def test_hifi_flac_retries_search_when_empty_and_album_tag_set():
    track = TrackRecord(
        source_path=Path("/x"),
        relative_path=Path("t.mp3"),
        artist="A",
        album="Wrong Album",
        title="Song",
        tracknumber=None,
        discnumber=None,
    )
    client = MagicMock()
    hit = {
        "id": 99,
        "title": "Song",
        "artist": {"name": "A"},
        "album": {"title": "Real"},
    }
    client.search_tracks.side_effect = [[], [hit]]
    inner = {"mimeType": "audio/flac", "urls": ["https://cdn.example/x.flac"]}
    client.get_track_json.return_value = {
        "data": {
            "manifest": base64.b64encode(json.dumps(inner).encode()).decode(),
            "manifestMimeType": "application/vnd.tidal.bts",
        }
    }
    client.fetch_bytes.return_value = b"fLaCdata"

    src = HifiFlacSource(client=client)
    data = src.fetch_flac(track)

    assert data == b"fLaCdata"
    assert client.search_tracks.call_count == 2
    assert client.search_tracks.call_args_list[0][0][0] == "A Song Wrong Album"
    assert client.search_tracks.call_args_list[1][0][0] == "A Song"
