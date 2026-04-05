# Configuration

## Installation

- **Python:** 3.10 or newer.
- **From the repository root:**

```bash
pip install -e .
```

- **With development dependencies (pytest):**

```bash
pip install -e ".[dev]"
```

This installs the `music-flac` console script and the `music_flac` package.

## Default paths

The CLI uses these defaults when you omit `--source` / `--dest` (Windows-oriented; change in `music_flac.config` if you fork):

| Role | Default path |
|------|----------------|
| Source library | `D:\Libraries\Music\Good Music` |
| FLAC mirror root | `D:\Libraries\Music\Good Music FLACs` |

Paths are normal `pathlib.Path` values on disk; only **printed** paths use forward slashes for readability.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `MUSIC_FLAC_SOURCE` | Default root for `--source` when not passed on the CLI. |
| `MUSIC_FLAC_DEST` | Default root for `--dest` when not passed on the CLI. |
| `MUSIC_FLAC_API_URL` | Endpoint URL for **`sync --backend http`** (can be overridden with `--api-url`). |
| `MUSIC_FLAC_API_TOKEN` | Optional bearer token for the HTTP backend (`Authorization: Bearer …`). Override with `--api-token`. |
| `MUSIC_FLAC_API_TIMEOUT` | HTTP request timeout in seconds for the HTTP backend and **`hifi-probe`** (default `120`). |

`AppConfig.from_env()` loads these once per run (see `src/music_flac/config.py`).

## Logging

- **`-v` / `--verbose`** on the top-level `music-flac` command sets logging to **DEBUG** on stderr (affects sync progress messages and library code that uses `logging`).

## Related

- [CLI reference](cli-reference.md) — flags that override defaults per command
- [Sync and backends](sync-and-backends.md) — when `MUSIC_FLAC_API_URL` is required
