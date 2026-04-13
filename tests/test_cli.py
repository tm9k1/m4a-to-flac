from pathlib import Path

from music_flac.cli import filter_tracks_by_patterns
from music_flac.models import TrackRecord


def _track(rel: str) -> TrackRecord:
    p = Path(rel)
    return TrackRecord(
        source_path=Path("/lib") / p,
        relative_path=p,
        artist="Artist",
        album="Album",
        title="Title",
        tracknumber=None,
        discnumber=None,
    )


def test_filter_tracks_by_patterns_with_include():
    pairs = [
        (_track("Rock/one.mp3"), Path("dest/Rock/one.flac")),
        (_track("Pop/two.mp3"), Path("dest/Pop/two.flac")),
    ]
    filtered = filter_tracks_by_patterns(pairs, ["Rock/*"], [])
    assert [t.relative_path.as_posix() for t, _ in filtered] == ["Rock/one.mp3"]


def test_filter_tracks_by_patterns_with_exclude():
    pairs = [
        (_track("Rock/one.mp3"), Path("dest/Rock/one.flac")),
        (_track("Pop/two.mp3"), Path("dest/Pop/two.flac")),
    ]
    filtered = filter_tracks_by_patterns(pairs, [], ["*/two.mp3"])
    assert [t.relative_path.as_posix() for t, _ in filtered] == ["Rock/one.mp3"]


def test_filter_tracks_by_patterns_with_include_and_exclude():
    pairs = [
        (_track("Rock/one.mp3"), Path("dest/Rock/one.flac")),
        (_track("Rock/two.mp3"), Path("dest/Rock/two.flac")),
        (_track("Pop/three.mp3"), Path("dest/Pop/three.flac")),
    ]
    filtered = filter_tracks_by_patterns(pairs, ["Rock/*"], ["*/two.mp3"])
    assert [t.relative_path.as_posix() for t, _ in filtered] == ["Rock/one.mp3"]
