# Changelog

All notable changes to this project are documented in this file.

## [0.2.0] — 2026-04-05

### Added

- **`docs/`** help set: index, configuration, CLI reference, library/mirror/naming guide, sync and backends (including hifi-api notes).
- `music_flac.paths.posix_display` and CLI output using **forward slashes** for all printed paths.
- `music_flac.naming`: strip trailing **YouTube-style 11-character** ids from stems; build destination leaf names as **Title** / **Title - Artist** / **Title - Artist - Album** with per-folder disambiguation and numeric suffixes when metadata still collides.
- `music_flac.hifi.HifiClient` plus CLI **`music-flac hifi-probe`** for `GET /` on hifi-api-compatible hosts (default [hifi.geeked.wtf](https://hifi.geeked.wtf/)); requests send an explicit **User-Agent** (plain urllib is often blocked).
- Tests for naming, paths, and mocked hifi JSON.

### Changed

- `plan` / `sync` mirror targets now use **clean leaf names** (parent folders still match the source tree). HTTP JSON `relative_path` uses `as_posix()`.

## [0.1.0] — 2026-04-05

### Added

- Python package `music_flac` (src layout) with CLI `music-flac`.
- Default library paths: source `D:\Libraries\Music\Good Music`, mirror root `D:\Libraries\Music\Good Music FLACs` (overridable via CLI and `MUSIC_FLAC_SOURCE` / `MUSIC_FLAC_DEST`).
- `scan` — walk the source tree, parse tags with Mutagen, print a readable listing.
- `plan` — show each source file’s relative path and the matching `.flac` path under the mirror root (same directory structure, `.flac` extension).
- `sync` — download bytes per track via `stub` (placeholder for tests) or `http` (POST JSON to `MUSIC_FLAC_API_URL`, optional bearer token).
- Atomic writes to the destination tree with skip-if-exists (override with `--force`).
- Tests for layout mapping and sync behavior.

### Notes

- Stub backend marker uses ASCII-only bytes for broad Python version compatibility.
