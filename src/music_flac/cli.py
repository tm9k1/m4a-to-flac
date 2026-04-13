from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from music_flac import __version__
from music_flac.config import AppConfig, DEFAULT_FLAC_ROOT, DEFAULT_SOURCE_ROOT
from music_flac.models import TrackRecord
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
    pairs = mirror_plan(result, flac_root, name_template=getattr(args, 'name_template', None))
    if getattr(args, 'include', None) or getattr(args, 'exclude', None):
        pairs = filter_tracks_by_patterns(pairs, args.include or [], args.exclude or [])

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


def filter_tracks_by_patterns(
    pairs: list[tuple[TrackRecord, Path]], 
    include_patterns: list[str], 
    exclude_patterns: list[str]
) -> list[tuple[TrackRecord, Path]]:
    """Filter track pairs based on include/exclude glob patterns."""
    if not include_patterns and not exclude_patterns:
        return pairs
    
    import fnmatch
    filtered = []
    
    for track, dest in pairs:
        # Convert path to posix string for consistent glob matching across OSes
        path_str = track.relative_path.as_posix()
        
        excluded = False
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(path_str, pattern):
                excluded = True
                break
        
        if excluded:
            continue
            
        # If include patterns specified, must match at least one
        if include_patterns:
            included = False
            for pattern in include_patterns:
                if fnmatch.fnmatch(path_str, pattern):
                    included = True
                    break
            if not included:
                continue
                
        filtered.append((track, dest))

    return filtered


def cmd_sync(args: argparse.Namespace, cfg: AppConfig) -> int:
    if getattr(args, 'quiet', False):
        logging.getLogger().setLevel(logging.ERROR)

    source_root = Path(args.source).expanduser().resolve()
    flac_root = Path(args.dest).expanduser().resolve()
    if not source_root.is_dir():
        print(f"Not a directory: {source_root}", file=sys.stderr)
        return 2

    # Only hifi backend now
    from music_flac.api.hifi_flac import HifiFlacSource
    from music_flac.hifi import HifiClient

    base = str(args.base_url or cfg.hifi_base_url)
    client = HifiClient(base_url=base, timeout_s=cfg.request_timeout_s)
    source = HifiFlacSource(client)

    result = scan_library(source_root)
    name_template = getattr(args, 'name_template', None)
    pairs = mirror_plan(result, flac_root, name_template=name_template)
    
    if getattr(args, 'include', None) or getattr(args, 'exclude', None):
        pairs = filter_tracks_by_patterns(pairs, args.include or [], args.exclude or [])
    
    dry_run = bool(args.dry_run)
    interactive = bool(getattr(args, 'interactive', False))

    workers = (
        args.workers if args.workers is not None else cfg.sync_max_workers
    )
    workers = max(1, int(workers))

    if hasattr(source, 'set_quality_preference'):
        source.set_quality_preference(args.quality)
    
    enhance_metadata = bool(getattr(args, 'enhance_metadata', False))

    w, sk, errs = sync_tracks(
        pairs,
        source,
        flac_root,
        dry_run=dry_run,
        copy_missing_tracks=bool(args.copy_missing_tracks),
        max_workers=workers,
        interactive=interactive,
        name_template=name_template,
        enhance_metadata=enhance_metadata,
    )
    print(
        f"Done. written={w} skipped_existing={sk} errors={len(errs)} "
        f"dry_run={dry_run} workers={workers}"
    )
    for e in errs:
        print(e, file=sys.stderr)
    return 1 if errs else 0


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
    pp.add_argument(
        "--include",
        action="append",
        metavar="PATTERN",
        help="Include only tracks matching glob pattern (can be used multiple times).",
    )
    pp.add_argument(
        "--exclude",
        action="append",
        metavar="PATTERN",
        help="Exclude tracks matching glob pattern (can be used multiple times).",
    )
    pp.add_argument(
        "--name-template",
        metavar="TEMPLATE",
        help="Custom filename template using {artist}, {album}, {title}, {tracknumber}, etc.",
    )
    pp.set_defaults(func=cmd_plan)

    py = sub.add_parser(
        "sync",
        help="Download FLAC for each track from hifi-api into the mirror tree.",
    )
    py.add_argument("--source", type=Path, default=DEFAULT_SOURCE_ROOT)
    py.add_argument("--dest", type=Path, default=DEFAULT_FLAC_ROOT)
    py.add_argument(
        "--base-url",
        default=None,
        help="Hifi API base URL (default: MUSIC_FLAC_HIFI_BASE or https://hifi.geeked.wtf/).",
    )
    py.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write files; only log what would happen.",
    )
    py.add_argument(
        "--workers",
        type=int,
        default=None,
        metavar="N",
        help="Parallel downloads (max concurrent tracks). Default: MUSIC_FLAC_SYNC_WORKERS or 8. Use 1 for sequential.",
    )
    py.add_argument(
        "--copy-missing-tracks",
        action="store_true",
        help="Copy missing tracks from source directory preserving original extension if hifi fetch fails.",
    )
    py.add_argument(
        "--interactive",
        action="store_true",
        help="Review and approve each change interactively before applying.",
    )
    py.add_argument(
        "--include",
        action="append",
        metavar="PATTERN",
        help="Include only tracks matching glob pattern (can be used multiple times).",
    )
    py.add_argument(
        "--exclude",
        action="append",
        metavar="PATTERN",
        help="Exclude tracks matching glob pattern (can be used multiple times).",
    )
    py.add_argument(
        "--quality",
        choices=["LOSSLESS", "HI_RES_LOSSLESS", "HIGH"],
        default="LOSSLESS",
        help="Preferred quality level for FLAC downloads (default: LOSSLESS).",
    )
    py.add_argument(
        "--name-template",
        metavar="TEMPLATE",
        help="Custom filename template using {artist}, {album}, {title}, {tracknumber}, etc.",
    )
    py.add_argument(
        "--enhance-metadata",
        action="store_true",
        help="Fetch and apply additional metadata (genres, cover art) from hifi API.",
    )
    py.set_defaults(func=cmd_sync)

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
