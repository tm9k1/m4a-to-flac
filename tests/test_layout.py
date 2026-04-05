from pathlib import Path

from music_flac.layout import (
    destination_path,
    flac_mirror_path,
    is_audio_file,
    relative_under,
)


def test_flac_mirror_path_preserves_directories():
    rel = Path("Artist") / "Album" / "01 - Song.mp3"
    assert flac_mirror_path(rel) == Path("Artist") / "Album" / "01 - Song.flac"


def test_destination_path():
    root = Path(r"D:\Libraries\Music\Good Music FLACs")
    rel = Path("A") / "B.flac"
    assert destination_path(root, Path("A") / "B.mp3") == root / rel


def test_is_audio_file():
    assert is_audio_file(Path("x.mp3")) is True
    assert is_audio_file(Path("x.FLAC")) is True
    assert is_audio_file(Path("x.txt")) is False


def test_relative_under(tmp_path):
    root = tmp_path / "lib"
    root.mkdir()
    f = root / "a" / "b.mp3"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"")
    assert relative_under(root, f) == Path("a") / "b.mp3"
