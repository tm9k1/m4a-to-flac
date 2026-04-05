from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from music_flac.hifi import DEFAULT_HIFI_BASE

# Default layout on your machine (override with env or CLI).
DEFAULT_SOURCE_ROOT = Path(r"D:\Libraries\Music\Good Music")
DEFAULT_FLAC_ROOT = Path(r"D:\Libraries\Music\Good Music FLACs")


def _path_from_env(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    if raw:
        return Path(raw).expanduser()
    return default


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Paths and API settings. API URL is required for HTTP backend (see env)."""

    source_root: Path
    flac_root: Path
    api_url: str | None
    api_token: str | None
    request_timeout_s: float
    hifi_base_url: str

    @classmethod
    def from_env(cls) -> AppConfig:
        return cls(
            source_root=_path_from_env("MUSIC_FLAC_SOURCE", DEFAULT_SOURCE_ROOT),
            flac_root=_path_from_env("MUSIC_FLAC_DEST", DEFAULT_FLAC_ROOT),
            api_url=os.environ.get("MUSIC_FLAC_API_URL"),
            api_token=os.environ.get("MUSIC_FLAC_API_TOKEN"),
            request_timeout_s=float(os.environ.get("MUSIC_FLAC_API_TIMEOUT", "120")),
            hifi_base_url=os.environ.get("MUSIC_FLAC_HIFI_BASE", DEFAULT_HIFI_BASE),
        )
