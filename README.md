# music-flac

**Safe, user-respecting FLAC conversion for your music library.** Scan your existing music collection and automatically download high-quality FLAC versions while preserving your folder structure and respecting your manual changes.

## What It Does

`music-flac` helps you upgrade your music library to lossless FLAC format. It scans your existing music files, searches for high-quality FLAC versions online, and creates a mirror of your library with the same folder structure. The key difference from other tools: **it respects your choices and never overwrites your work**.

### User-Centric Design

We designed this tool to feel safe and predictable, emulating how you'd manually organize your music:

- **🔒 Respects your existing work** - Never overwrites files you've already processed
- **🛡️ Detects manual changes** - Remembers what you've modified and skips re-processing
- **📁 Preserves your organization** - Maintains your exact folder structure
- **🔄 Smart fallbacks** - If online sources fail, copies your original tracks
- **👀 Transparent preview** - See exactly what will happen before making changes

### Typical User Scenarios

**Scenario 1: First-time setup**
```
Your library: Artist/Album/song.mp3
After sync:  Artist/Album/song.flac  (downloaded)
```

**Scenario 2: You've already converted some tracks**
```
Your library: Artist/Album/song.mp3
FLAC folder: Artist/Album/song.flac  (exists)
Result:      Skipped - respects your existing work
```

**Scenario 3: Online source unavailable**
```
Your library: Artist/Album/song.mp3
FLAC folder: (empty)
Result:      Artist/Album/song.mp3  (copied as fallback)
```

**Scenario 4: You manually edited metadata**
```
Your library: Artist/Album/song.mp3
FLAC folder: Artist/Album/song.flac  (you edited tags)
Result:      Skipped - detects your changes and preserves them
```

## Quick Start

1. **Install**: `pip install -e .`
2. **Preview**: `music-flac plan` (see what would happen)
3. **Test run**: `music-flac sync --dry-run` (safe preview)
4. **Convert**: `music-flac sync` (downloads FLACs)

Default paths (Windows):
- Source: `D:\Libraries\Music\Good Music`
- Destination: `D:\Libraries\Music\Good Music FLACs`

## CLI Overview

```bash
music-flac scan        [--source PATH]          # list tracks + tags
music-flac plan        [--source PATH] [--dest PATH] [--include PATTERN] [--exclude PATTERN] [--name-template TEMPLATE]   # preview source → FLAC mapping
music-flac sync        [--source PATH] [--dest PATH] [--base-url URL] [--dry-run] [--copy-missing-tracks] [--interactive] [--include PATTERN] [--exclude PATTERN] [--quality QUALITY] [--name-template TEMPLATE] [--enhance-metadata]
```

- **`scan`** — Shows what tracks and metadata were found in your library.
- **`plan`** — Previews the exact file mappings with optional filters and custom naming.
- **`sync`** — Downloads FLACs, respecting existing work and user changes, with interactive approval, selective filtering, quality control, and enhanced metadata.
## Safety Features

- **State tracking** - Remembers your modifications in `.music-flac-state.json`
- **Atomic writes** - Temporary files prevent corruption if downloads fail
- **Parallel downloads** - Fast processing with `--workers` option
- **Dry-run mode** - Test everything safely first
- **Fallback copying** - Never leaves you without music

## Requirements

- Python 3.10+
- Internet connection for FLAC downloads
- Install: `pip install -e ".[dev]"` from this repo (or `pip install -e .` for runtime only).

## Documentation

Detailed help in **[docs/](docs/README.md)**:
- [Configuration](docs/configuration.md) - Environment variables and settings
- [CLI Reference](docs/cli-reference.md) - All commands and options
- [File Naming](docs/library-mirror-naming.md) - How filenames are generated
- [Sync Behavior](docs/sync-and-backends.md) - Technical details

## Mirror File Naming

Under each source folder, destination **leaf** names are built from tags (title, artist, album), with this disambiguation **within that folder**:

1. **Title** only, if unique.
2. If two or more collide: **Title - Artist**.
3. If still colliding: **Title - Artist - Album**.
4. If still colliding (identical metadata): **numeric suffix** ` (2)`, ` (3)`, …

When stripping a trailing **YouTube-style 11-character id** from the source filename (e.g. `… - dQw4w9WgXcQ` or `… [dQw4w9WgXcQ]`), that cleaned stem is only used as a **fallback title** when tags omit a title.
