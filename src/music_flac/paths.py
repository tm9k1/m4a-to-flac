from __future__ import annotations

from pathlib import Path


def posix_display(path: Path) -> str:
    """Render a path with forward slashes for logs, CLI, and API payloads."""
    return path.as_posix()
