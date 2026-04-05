from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from music_flac import __version__
from music_flac.api.http import HttpFlacSource
from music_flac.api.stub import StubFlacSource
from music_flac.config import AppConfig, DEFAULT_FLAC_ROOT, DEFAULT_SOURCE_ROOT
from music_flac.paths import posix_display
from music_flac.scanner import scan_library
from music_flac.sync import mirror_plan, sync_tracks


def _format_track(t, width: int = 72) -> str:
    artist = t.artist or "?"
    album = t.album or "?"
    title = t.title or t.relative_path.stem
    line = f"{artist} — {album} — {title}"
    if len(line) > width:
        line = line[: width - 1] + "…"
    return line


def cmd_scan(args: argparse.Namespace, cfg: AppConfig) -> int:
    root = Path(args.source).expanduser().resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 2
    result = scan_library(root)
    print(f"Library: {posix_display(result.root)}")
    print(f"Tracks: {len(result.tracks)}\n")
    for i, t in enumerate(result.tracks, 1):
        err = f"  (!) {t.errors[0]}" if t.errors else ""
        print(f"{i:4}  {_format_track(t)}{err}")
        print(f"      {posix_display(t.relative_path)}")
    return 0


def cmd_plan(args: argparse.Namespace, cfg: AppConfig) -> int:
    source_root = Path(args.source).expanduser().resolve()
    flac_root = Path(args.dest).expanduser().resolve()
    if not source_root.is_dir():
        print(f"Not a directory: {source_root}", file=sys.stderr)
        return 2
    result = scan_library(source_root)
    pairs = mirror_plan(result, flac_root)
    print(f"Source: {posix_display(source_root)}")
    print(f"FLAC root: {posix_display(flac_root)}")
    print(f"Tracks: {len(pairs)}\n")
    try:
        dest_root = flac_root.resolve()
    except OSError:
        dest_root = flac_root
    for t, dest in pairs:
        print(f"{posix_display(t.relative_path)}")
        try:
            rel_out = dest.relative_to(dest_root)
        except ValueError:
            rel_out = dest
        print(f"  -> {posix_display(rel_out)}")
    return 0


def cmd_sync(args: argparse.Namespace, cfg: AppConfig) -> int:
    source_root = Path(args.source).expanduser().resolve()
    flac_root = Path(args.dest).expanduser().resolve()
    if not source_root.is_dir():
        print(f"Not a directory: {source_root}", file=sys.stderr)
        return 2

    backend = args.backend
    if backend == "http":
        url = args.api_url or cfg.api_url
        if not url:
            print(
                "HTTP backend requires --api-url or MUSIC_FLAC_API_URL.",
                file=sys.stderr,
            )
            return 2
        token = args.api_token if args.api_token is not None else cfg.api_token
        source = HttpFlacSource(api_url=url, token=token, timeout_s=cfg.request_timeout_s)
    else:
        source = StubFlacSource()

    result = scan_library(source_root)
    pairs = mirror_plan(result, flac_root)
    dry_run = bool(args.dry_run)
    skip_existing = not bool(args.force)

    w, sk, errs = sync_tracks(
        pairs,
        source,
        dry_run=dry_run,
        skip_existing=skip_existing,
    )
    print(
        f"Done. written={w} skipped_existing={sk} errors={len(errs)} dry_run={dry_run}"
    )
    for e in errs:
        print(e, file=sys.stderr)
    return 1 if errs else 0


def cmd_hifi_probe(args: argparse.Namespace, cfg: AppConfig) -> int:
    from music_flac.hifi import HifiClient

    client = HifiClient(base_url=str(args.base_url), timeout_s=cfg.request_timeout_s)
    info = client.service_info()
    print(json.dumps(info, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="music-flac",
        description="Scan a music library and mirror it under a FLAC folder (clean leaf names, forward-slash paths; fetch via API).",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Log debug messages to stderr.",
    )

    sub = p.add_subparsers(dest="command", required=True)

    ps = sub.add_parser("scan", help="List tracks and metadata under the source library.")
    ps.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE_ROOT,
        help=f"Root of the existing library (default: {DEFAULT_SOURCE_ROOT})",
    )
    ps.set_defaults(func=cmd_scan)

    pp = sub.add_parser(
        "plan",
        help="Show how each source file maps to a path under the FLAC mirror.",
    )
    pp.add_argument("--source", type=Path, default=DEFAULT_SOURCE_ROOT)
    pp.add_argument(
        "--dest",
        type=Path,
        default=DEFAULT_FLAC_ROOT,
        help=f"Root for downloaded FLACs (default: {DEFAULT_FLAC_ROOT})",
    )
    pp.set_defaults(func=cmd_plan)

    py = sub.add_parser(
        "sync",
        help="Download FLAC for each track (stub or HTTP API) into the mirror tree.",
    )
    py.add_argument("--source", type=Path, default=DEFAULT_SOURCE_ROOT)
    py.add_argument("--dest", type=Path, default=DEFAULT_FLAC_ROOT)
    py.add_argument(
        "--backend",
        choices=("stub", "http"),
        default="stub",
        help="stub: placeholder bytes; http: POST JSON to your API (see README).",
    )
    py.add_argument(
        "--api-url",
        default=None,
        help="Override MUSIC_FLAC_API_URL for this run.",
    )
    py.add_argument(
        "--api-token",
        default=None,
        help="Override MUSIC_FLAC_API_TOKEN for this run.",
    )
    py.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write files; only log what would happen.",
    )
    py.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch even if the destination file already exists.",
    )
    py.set_defaults(func=cmd_sync)

    ph = sub.add_parser(
        "hifi-probe",
        help="Fetch GET / JSON from a hifi-api-compatible base URL (default: hifi.geeked.wtf).",
    )
    ph.add_argument(
        "--base-url",
        type=str,
        default="https://hifi.geeked.wtf/",
        help="Server root (trailing slash optional).",
    )
    ph.set_defaults(func=cmd_hifi_probe)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    cfg = AppConfig.from_env()
    return int(args.func(args, cfg))


if __name__ == "__main__":
    raise SystemExit(main())
