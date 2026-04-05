from pathlib import Path

from music_flac.models import ScanResult, TrackRecord
from music_flac.api.stub import StubFlacSource, STUB_MARKER
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
