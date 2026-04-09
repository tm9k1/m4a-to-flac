import shutil
import subprocess
from pathlib import Path

import pytest
from mutagen.flac import FLAC

from music_flac.models import ScanResult, TrackRecord
from music_flac.api.stub import StubFlacSource, STUB_MARKER
from music_flac.metadata import apply_flac_metadata
from music_flac.sync import mirror_plan, sync_tracks


def _track(rel: str) -> TrackRecord:
    p = Path(rel)
    return TrackRecord(
        source_path=Path("/tmp") / p,
        relative_path=p,
        artist="A",
        album="B",
        title="C",
        tracknumber="1",
        discnumber=None,
    )


def test_mirror_plan(tmp_path):
    root = tmp_path / "src"
    root.mkdir()
    flac_root = tmp_path / "flac"
    t = _track(str(Path("Artist") / "Album" / "song.mp3"))
    result = ScanResult(root=root, tracks=[t])
    pairs = mirror_plan(result, flac_root)
    assert len(pairs) == 1
    _, dest = pairs[0]
    assert dest == flac_root / "Artist" / "Album" / "C.flac"


def test_sync_writes_stub(tmp_path):
    root = tmp_path / "src"
    root.mkdir()
    flac_root = tmp_path / "flac"
    t = _track("x.mp3")
    result = ScanResult(root=root, tracks=[t])
    pairs = mirror_plan(result, flac_root)
    w, sk, errs = sync_tracks(pairs, StubFlacSource(), dry_run=False, skip_existing=True)
    assert w == 1 and sk == 0 and errs == []
    data = (flac_root / "C.flac").read_bytes()
    assert data.startswith(STUB_MARKER)


def test_sync_skips_existing(tmp_path):
    dest = tmp_path / "C.flac"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"keep")
    t = _track("x.mp3")
    pairs = [(t, dest)]
    w, sk, errs = sync_tracks(pairs, StubFlacSource(), dry_run=False, skip_existing=True)
    assert w == 0 and sk == 1
    assert dest.read_bytes() == b"keep"


def test_sync_updates_existing_metadata_when_available(tmp_path, monkeypatch):
    dest = tmp_path / "C.flac"
    dest.write_bytes(b"existing")
    t = _track("x.mp3")
    pairs = [(t, dest)]

    class MetadataSource:
        def fetch_metadata(self, track):
            return {"tags": {"TITLE": "C"}}

    monkeypatch.setattr("music_flac.sync._is_valid_flac_file", lambda _dest: True)
    monkeypatch.setattr("music_flac.sync._update_existing_metadata_if_needed", lambda track, _dest, source: True)

    w, sk, errs = sync_tracks(pairs, MetadataSource(), dry_run=False, skip_existing=True)
    assert w == 1 and sk == 0 and errs == []


def test_apply_flac_metadata_embeds_cover_art(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg required to generate a valid FLAC file")

    flac_path = tmp_path / "test.flac"
    jpg_path = tmp_path / "cover.jpg"
    jpg_path.write_bytes(b"\xff\xd8\xffJPEGDATA")

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:duration=0.1",
            str(flac_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    metadata = {
        "tags": {"TITLE": "Test", "ARTIST": "Me", "ALBUM": "Album"},
        "pictures": [
            {
                "data": jpg_path.read_bytes(),
                "mime": "image/jpeg",
                "url": str(jpg_path),
                "type": 3,
                "desc": "Cover art",
            }
        ],
    }
    apply_flac_metadata(flac_path, metadata)

    flac = FLAC(flac_path)
    assert flac.tags["TITLE"] == ["Test"]
    assert flac.tags["ARTIST"] == ["Me"]
    assert flac.tags["ALBUM"] == ["Album"]
    assert len(flac.pictures) == 1
    assert flac.pictures[0].mime == "image/jpeg"
    assert flac.pictures[0].desc == "Cover art"


def test_sync_parallel_matches_sequential_stub(tmp_path):
    root = tmp_path / "src"
    root.mkdir()
    flac_root = tmp_path / "flac"
    tracks = [
        TrackRecord(
            source_path=Path("/tmp") / f"t{i}.mp3",
            relative_path=Path(f"t{i}.mp3"),
            artist="A",
            album="B",
            title=f"C{i}",
            tracknumber=str(i),
            discnumber=None,
        )
        for i in range(5)
    ]
    result = ScanResult(root=root, tracks=tracks)
    pairs = mirror_plan(result, flac_root)
    w1, sk1, e1 = sync_tracks(
        pairs, StubFlacSource(), dry_run=False, skip_existing=True, max_workers=1
    )
    for p in flac_root.rglob("*.flac"):
        p.unlink()
    w4, sk4, e4 = sync_tracks(
        pairs, StubFlacSource(), dry_run=False, skip_existing=True, max_workers=4
    )
    assert (w1, sk1, e1) == (w4, sk4, e4) == (5, 0, [])
    for i in range(5):
        f = flac_root / f"C{i}.flac"
        assert f.is_file()
        assert f.read_bytes().startswith(STUB_MARKER)
