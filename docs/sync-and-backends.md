# Sync behavior and backends

## End-to-end flow

1. **Scan** the source library (same rules as `scan` / `plan`).
2. **Compute** one destination `.flac` path per track ([mirror and naming](library-mirror-naming.md)).
3. Optionally filter the plan with `--include` and `--exclude` patterns before syncing.
4. Optionally override destination leaf names with `--name-template` in `plan` or `sync`.
5. For each `(track, destination)` pair:
   - If **`--dry-run`** is set, nothing is written; the tool logs what it **would** do.
   - If **`--interactive`** is set, each planned action is confirmed before it runs.
   - Otherwise the tool calls the backend’s **`fetch_flac(track)`**, receives **bytes**, and writes the file.

### Enhanced metadata

If **`--enhance-metadata`** is enabled and a `.flac` already exists, the tool may fetch tags and cover art from the backend and update the file if the metadata differs.

### Parallel downloads (`sync --workers`)

Non-dry-run downloads use a **thread pool** so up to **N** tracks are in flight at once (`--workers N`, default from **`MUSIC_FLAC_SYNC_WORKERS`** or **8**). Skips are resolved on the main thread first; only active downloads are parallelized. Use **`--workers 1`** if you hit rate limits or want strictly ordered logs. The same **`FlacSource`** instance is shared across threads (e.g. one **`HifiClient`**); ensure your backend tolerates concurrent requests.

## Atomic writes

The sync step writes to a **temporary file** in the destination directory, then **replaces** the final name. If the destination already exists on Windows, it is removed before replace, so updates are less likely to leave a half-written `.flac` visible under the final name.

## Backend: `hifi`

- **`music-flac sync`**
- Uses a **hifi-api-compatible** server (default [hifi.geeked.wtf](https://hifi.geeked.wtf/); set **`MUSIC_FLAC_HIFI_BASE`** or **`--hifi-base-url`**).
- Per track:
  1. Build a search string from tags (artist, title, album) or the cleaned filename stem.
  2. **`GET /search?s=…&limit=…`** and pick the best hit vs. tags (`pick_best_search_item`). If there are **no** results and an **album** tag was part of the query, **retry** search with **artist + title** only.
  3. **`GET /track?id=<tidal_track_id>&quality=…`** trying, in order, **`LOSSLESS`**, **`HI_RES_LOSSLESS`**, **`HIGH`** until a manifest yields a URL.
  4. Decode the base64 **`manifest`**: JSON (**`application/vnd.tidal.bts`**) with a **`urls`** list, or fall back to scanning DASH/XML text for `https://…` (preferring `.flac` when present).
  5. **`GET`** the first stream URL and save the bytes as the destination file.

Upstream schema and extra endpoints (**`/trackManifests`**, **`/info`**, etc.) are documented in [binimum/hifi-api](https://github.com/binimum/hifi-api) and [hifi-api-workers](https://github.com/monochrome-music/hifi-api-workers). This backend uses **`/search`** + **`/track`** only; extend **`music_flac.hifi`** / **`HifiFlacSource`** if you need manifest types we do not parse yet.


### User-Agent

Some hosts return **403** to Python’s default **urllib** user agent. **`HifiClient`** sends an explicit **User-Agent** header on JSON and CDN requests.

## Troubleshooting

| Symptom | Things to check |
|--------|------------------|
| `Not a directory` | `--source` must be an existing folder. |
| hifi search / track errors | Check tags, try `-v`; verify server connectivity. |
| Empty or corrupt `.flac` | Server must return **only** audio bytes; check status codes and errors in logs (`-v`). |
| Wrong file names | Tag quality drives naming; see [library-mirror-naming.md](library-mirror-naming.md). |
| Skipped files | Expected if the destination exists; use **`--force`** to refetch. |

## Related

- [Configuration](configuration.md) — env vars and timeouts
- [CLI reference — `sync` / `hifi-probe` / `hifi-fetch-one`](cli-reference.md)
