from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Any

from mutagen.flac import FLAC, FLACNoHeaderError, Picture

log = logging.getLogger(__name__)


def _normalize_mime_type(content_type: str | None, url: str | None, data: bytes | None = None) -> str:
    if content_type:
        mime = content_type.split(";", 1)[0].strip()
        if mime:
            return mime

    if url:
        mime, _ = mimetypes.guess_type(url)
        if mime:
            return mime

    if data is not None:
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
            return "image/gif"

    return "application/octet-stream"


def apply_flac_metadata(dest: Path, metadata: dict[str, Any]) -> None:
    if not metadata:
        return

    tags = metadata.get("tags") or {}
    pictures = metadata.get("pictures") or []
    if not tags and not pictures:
        return

    try:
        flac = FLAC(dest)
    except (FLACNoHeaderError, Exception) as exc:
        log.warning("Cannot open FLAC file for metadata update at %s: %s", dest, exc)
        return

    for key, value in tags.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            flac[key] = [str(v) for v in value if v is not None]
        else:
            flac[key] = [str(value)]

    if pictures:
        flac.clear_pictures()
        for pic in pictures:
            data = pic.get("data")
            if not isinstance(data, (bytes, bytearray)):
                log.warning("Skipping invalid picture data for %s", dest)
                continue
            mime = _normalize_mime_type(pic.get("mime"), pic.get("url"), bytes(data))
            picture = Picture()
            picture.data = bytes(data)
            picture.mime = mime
            picture.type = int(pic.get("type", 3))
            picture.desc = str(pic.get("desc", ""))
            for field in ("width", "height", "depth", "colors"):
                if isinstance(pic.get(field), int):
                    setattr(picture, field, pic[field])
            flac.add_picture(picture)

    flac.save()


def needs_flac_metadata_update(dest: Path, metadata: dict[str, Any]) -> bool:
    tags = metadata.get("tags") or {}
    pictures = metadata.get("pictures") or []
    if not tags and not pictures:
        return False

    try:
        flac = FLAC(dest)
    except (FLACNoHeaderError, Exception) as exc:
        log.warning("Cannot open FLAC file for metadata check at %s: %s", dest, exc)
        return False

    existing_tags = flac.tags or {}

    for key, desired in tags.items():
        desired_values = _tag_values(desired)
        existing_values = [str(v) for v in existing_tags.get(key, [])]
        if existing_values != desired_values:
            return True

    if pictures:
        existing_pictures = getattr(flac, "pictures", []) or []
        desired_fps = [_picture_fingerprint(pic) for pic in pictures]
        existing_fps = [_picture_fingerprint_mutagen(pic) for pic in existing_pictures]
        if existing_fps != desired_fps:
            return True

    return False


def _tag_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v is not None]
    return [str(value)]


def _picture_fingerprint(pic: dict[str, Any]) -> tuple[str, int, str, bytes | None]:
    return (
        str(pic.get("mime", "")),
        int(pic.get("type", 3)),
        str(pic.get("desc", "")),
        bytes(pic.get("data")) if isinstance(pic.get("data"), (bytes, bytearray)) else None,
    )


def _picture_fingerprint_mutagen(pic: Picture) -> tuple[str, int, str, bytes | None]:
    return (
        pic.mime or "",
        pic.type or 3,
        pic.desc or "",
        bytes(pic.data) if pic.data is not None else None,
    )

