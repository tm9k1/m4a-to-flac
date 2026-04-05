from __future__ import annotations

from pathlib import Path

AUDIO_EXTENSIONS = frozenset(
    {
        ".mp3",
        ".flac",
        ".m4a",
        ".aac",
        ".ogg",
        ".opus",
        ".wav",
        ".wma",
    }
)


def is_audio_file(path: Path) -> bool:
    return path.suffix.lower() in AUDIO_EXTENSIONS


def relative_under(root: Path, path: Path) -> Path:
    return path.relative_to(root.resolve())


def flac_mirror_path(relative_audio: Path) -> Path:
    """Same folders and basename as the source file, with a .flac extension."""
    return relative_audio.with_suffix(".flac")


def destination_path(flac_root: Path, relative_audio: Path) -> Path:
    return flac_root / flac_mirror_path(relative_audio)
