import base64
import json
from pathlib import Path

from music_flac.hifi import pick_best_search_item, stream_urls_from_track_api_response
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
