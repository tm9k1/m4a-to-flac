# music-flac

Scan an existing music library on disk, show embedded metadata, and **mirror the same folder layout** under a second root where each file is a **`.flac`** fetched from your **external API**.

Default paths (Windows):

| Role | Path |
|------|------|
| Source library | `D:\Libraries\Music\Good Music` |
| FLAC mirror | `D:\Libraries\Music\Good Music FLACs` |

Override with `--source` / `--dest` or environment variables `MUSIC_FLAC_SOURCE` and `MUSIC_FLAC_DEST`.

## Requirements

- Python 3.10+
- Install: `pip install -e ".[dev]"` from this repo (or `pip install -e .` for runtime only).

## CLI

```bash
music-flac scan   [--source PATH]          # list tracks + tags
music-flac plan   [--source PATH] [--dest PATH]   # show source → mirror .flac paths
music-flac sync   [--source PATH] [--dest PATH] [--backend stub|http] [--dry-run]
```

- **`plan`** — No network; shows how each audio file maps to a path under the FLAC root (same relative path, `.flac` extension).
- **`sync`** — **`stub`**: writes small placeholder files (for pipeline tests). **`http`**: POSTs JSON metadata to your API and saves the response body as the `.flac` file.

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

See `CHANGELOG.md` for version history and `AGENTS.md` for contributor/agent notes.

## License

Specify your license here if you publish the repo.
