# Changelog

All notable changes to this project are documented in this file.

## [0.3.1] — 2026-04-05

### Added

- **`sync --workers N`**: parallel track downloads via **`ThreadPoolExecutor`** (default **8** from **`MUSIC_FLAC_SYNC_WORKERS`** when `--workers` is omitted). **`sync_tracks(..., max_workers=…)`** for library use; default **`1`** keeps sequential behavior for direct callers.

### Documentation

- Configuration and sync docs updated for worker env / flags.

## [0.3.0] — 2026-04-05

### Added

- **`HifiFlacSource`** (`sync --backend hifi`): `GET /search?s=…` → best-hit selection → `GET /track` (qualities `LOSSLESS`, `HI_RES_LOSSLESS`, `HIGH`) → decode base64 manifest (JSON `urls` or DASH/XML URL scrape) → `GET` stream bytes.
- **`music-flac hifi-fetch-one`** for a one-song smoke test; **`MUSIC_FLAC_HIFI_BASE`** / `--hifi-base-url` / shared timeout with other HTTP.
- **`HifiClient`**: `search_tracks`, `get_track_json`, `fetch_bytes`; helpers `stream_urls_from_track_api_response`, `pick_best_search_item`, `search_query_from_track`.
- Tests for manifest JSON parsing and search pick scoring. `.gitignore` `_hifi_test*`.

### Changed

- **`hifi-probe`** default base URL comes from **`MUSIC_FLAC_HIFI_BASE`** when `--base-url` is omitted.

### Documentation

- Updated `docs/` for **`hifi`** backend and **`hifi-fetch-one`**.

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
