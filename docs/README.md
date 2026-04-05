# music-flac documentation

Help for installing, configuring, and using **music-flac**: scan a music library, preview where FLAC files will land, and sync them using a pluggable backend.

## Quick start

1. [Install](configuration.md#installation) the package (`pip install -e .`).
2. Run **`music-flac scan`** to list tracks and tags (see [CLI reference](cli-reference.md#scan)).
3. Run **`music-flac plan`** to see each source file mapped to a mirror path (see [Mirror layout and naming](library-mirror-naming.md)).
4. Run **`music-flac sync --dry-run`**, then **`music-flac sync`** with **`stub`**, **`http`**, or **`hifi`** (see [Sync and backends](sync-and-backends.md)). To try [hifi.geeked.wtf](https://hifi.geeked.wtf/) on one track: **`music-flac hifi-fetch-one`** ([CLI reference](cli-reference.md#hifi-fetch-one)).

Built-in help: `music-flac --help` and `music-flac <command> --help`.

## Guides

| Document | Contents |
|----------|----------|
| [Configuration](configuration.md) | Environment variables, default paths, timeouts |
| [CLI reference](cli-reference.md) | Every command and flag |
| [Library, mirror, and naming](library-mirror-naming.md) | Supported formats, tags, folder layout, clean filenames, YouTube id stripping |
| [Sync and backends](sync-and-backends.md) | Stub, HTTP, **hifi** (search → manifest → CDN), dry-run, force, atomic writes |

## Other project files

- [README.md](../README.md) — project summary and links
- [LICENSE](../LICENSE) — **AGPL-3.0-or-later** (full text)
- [CHANGELOG.md](../CHANGELOG.md) — version history
- [AGENTS.md](../AGENTS.md) — notes for contributors and coding agents
