from unittest.mock import patch

from music_flac.hifi import HifiClient


class _FakeResp:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_hifi_service_info_parses_json():
    body = b'{"version":"2.7","Repo":"https://example.com/repo"}'
    with patch("urllib.request.urlopen", return_value=_FakeResp(body)):
        c = HifiClient(base_url="https://hifi.example/")
        info = c.service_info()
    assert info["version"] == "2.7"
    assert "Repo" in info
