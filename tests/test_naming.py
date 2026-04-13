from pathlib import Path

from music_flac.models import TrackRecord
from music_flac.naming import (
    apply_name_template,
    resolve_stems_in_folder,
    strip_youtube_id_suffix,
)
from music_flac.paths import posix_display


def test_strip_youtube_trailing_dash():
    assert strip_youtube_id_suffix("My Song - dQw4w9WgXcQ") == "My Song"


def test_strip_youtube_brackets():
    assert strip_youtube_id_suffix("My Song [dQw4w9WgXcQ]") == "My Song"


def test_strip_youtube_underscore():
    assert strip_youtube_id_suffix("My Song_dQw4w9WgXcQ") == "My Song"


def test_posix_display_uses_forward_slashes():
    p = Path("Artist") / "Album" / "track.mp3"
    assert "/" in posix_display(p)
    assert "\\" not in posix_display(p)


def _tr(rel: str, *, title, artist="Ar", album="Al") -> TrackRecord:
    p = Path(rel)
    return TrackRecord(
        source_path=Path("/x") / p,
        relative_path=p,
        artist=artist,
        album=album,
        title=title,
        tracknumber=None,
        discnumber=None,
    )


def test_disambiguate_title_only_when_unique():
    a = _tr("f/a.mp3", title="Only")
    b = _tr("f/b.mp3", title="Other")
    r = resolve_stems_in_folder([a, b])
    assert r[a] == "Only"
    assert r[b] == "Other"


def test_disambiguate_adds_artist_on_title_collision():
    a = _tr("f/a.mp3", title="Same", artist="One")
    b = _tr("f/b.mp3", title="Same", artist="Two")
    r = resolve_stems_in_folder([a, b])
    assert r[a] == "Same - One"
    assert r[b] == "Same - Two"


def test_disambiguate_adds_album_when_needed():
    a = _tr("f/a.mp3", title="Same", artist="Art", album="LP1")
    b = _tr("f/b.mp3", title="Same", artist="Art", album="LP2")
    r = resolve_stems_in_folder([a, b])
    assert r[a] == "Same - Art - LP1"
    assert r[b] == "Same - Art - LP2"


def test_numeric_suffix_when_metadata_identical():
    a = _tr("f/a.mp3", title="Same", artist="Art", album="LP")
    b = _tr("f/b.mp3", title="Same", artist="Art", album="LP")
    r = resolve_stems_in_folder([a, b])
    assert set(r.values()) == {"Same - Art - LP", "Same - Art - LP (2)"}


def test_apply_name_template_formats_track_fields():
    track = _tr("f/a.mp3", title="Song", artist="One", album="Album")
    assert apply_name_template(track, "{artist} - {title}") == "One - Song"


def test_apply_name_template_invalid_template_falls_back():
    track = _tr("f/a.mp3", title="Song")
    assert apply_name_template(track, "{bad}") == "Song"
