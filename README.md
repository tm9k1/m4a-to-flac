# music-flac

Scan an existing music library on disk, show embedded metadata, and **mirror the same parent folder layout** under a second root where each file is a **`.flac`** fetched from your **external API**.

Output paths in the CLI use **forward slashes** everywhere (`pathlib.Path.as_posix()`), so logs and plans look the same on Windows, macOS, and Linux.

Default paths (Windows):

| Role | Path |
|------|------|
| Source library | `D:\Libraries\Music\Good Music` |
| FLAC mirror | `D:\Libraries\Music\Good Music FLACs` |

Override with `--source` / `--dest` or environment variables `MUSIC_FLAC_SOURCE` and `MUSIC_FLAC_DEST`.

## Documentation

Detailed help lives in the **[docs/](docs/README.md)** folder:

- [Configuration and environment variables](docs/configuration.md)
- [CLI reference (all commands and flags)](docs/cli-reference.md)
- [Library scanning, mirror layout, and file naming](docs/library-mirror-naming.md)
- [Sync behavior, stub/HTTP/**hifi** backends](docs/sync-and-backends.md)

## Mirror file naming

Under each source folder, destination **leaf** names are built from tags (title, artist, album), with this disambiguation **within that folder**:

1. **Title** only, if unique.
2. If two or more collide: **Title - Artist**.
3. If still colliding: **Title - Artist - Album**.
4. If still colliding (identical metadata): **numeric suffix** ` (2)`, ` (3)`, …

When stripping a trailing **YouTube-style 11-character id** from the source filename (e.g. `… - dQw4w9WgXcQ` or `… [dQw4w9WgXcQ]`), that cleaned stem is only used as a **fallback title** when tags omit a title.

## Requirements

- Python 3.10+
- Install: `pip install -e ".[dev]"` from this repo (or `pip install -e .` for runtime only).

## CLI

```bash
music-flac scan        [--source PATH]          # list tracks + tags
music-flac plan        [--source PATH] [--dest PATH]   # source → mirror .flac paths
music-flac sync           [--source PATH] [--dest PATH] [--backend stub|http|hifi] [--workers N] [--dry-run]
music-flac hifi-probe     [--base-url URL]         # GET / JSON (default from MUSIC_FLAC_HIFI_BASE)
music-flac hifi-fetch-one -o out.flac [--query …] [--artist …] [--title …]   # one-track smoke test
```

- **`plan`** — No network; shows mapping with **forward slashes**. Same parent directories as the source; leaf names follow **Mirror file naming** above.
- **`sync`** — **`stub`**: placeholder files. **`http`**: POST JSON to your API; body saved as `.flac`. **`hifi`**: [hifi-api](https://github.com/binimum/hifi-api)-compatible **search → `/track` manifest → CDN** download (default base [hifi.geeked.wtf](https://hifi.geeked.wtf/); override with `MUSIC_FLAC_HIFI_BASE` or `--hifi-base-url`).

### hifi-api-compatible services (e.g. [hifi.geeked.wtf](https://hifi.geeked.wtf/))

These servers expose a **Tidal-oriented** JSON API ([binimum/hifi-api](https://github.com/binimum/hifi-api) / [hifi-api-workers](https://github.com/monochrome-music/hifi-api-workers)). Use **`music-flac hifi-probe`** to verify **`GET /`**. Use **`music-flac hifi-fetch-one`** or **`sync --backend hifi`** for search + stream download. Details: [docs/sync-and-backends.md](docs/sync-and-backends.md).

### HTTP API contract (adjust `music_flac.api.http` if yours differs)

- Set `MUSIC_FLAC_API_URL` to your endpoint.
- Optional: `MUSIC_FLAC_API_TOKEN` (sent as `Authorization: Bearer …`).
- Request: `POST` with `Content-Type: application/json` and body:

```json
{
  "artist": "...",
  "album": "...",
  "title": "...",
  "tracknumber": "...",
  "discnumber": "...",
  "relative_path": "Artist/Album/01 - Song.mp3"
}
```

- Response: raw FLAC bytes in the body.

## Development

```bash
pip install -e ".[dev]"
pytest
music-flac --help
```

See `CHANGELOG.md` for version history, `AGENTS.md` for contributor/agent notes, and **`docs/`** for full feature documentation.

## License

Specify your license here if you publish the repo.
