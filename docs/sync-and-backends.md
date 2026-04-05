# Sync behavior and backends

## End-to-end flow

1. **Scan** the source library (same rules as `scan` / `plan`).
2. **Compute** one destination `.flac` path per track ([mirror and naming](library-mirror-naming.md)).
3. For each `(track, destination)` pair:
   - If **`--force`** is not set and the destination exists and has **non-zero size**, the track is **skipped**.
   - If **`--dry-run`** is set, nothing is written; the tool logs what it **would** do.
   - Otherwise the tool calls the backend’s **`fetch_flac(track)`**, receives **bytes**, and writes the file.

## Atomic writes

The sync step writes to a **temporary file** in the destination directory, then **replaces** the final name. If the destination already exists on Windows, it is removed before replace, so updates are less likely to leave a half-written `.flac` visible under the final name.

## Backend: `stub`

- **`music-flac sync --backend stub`** (default)
- Does **not** use the network.
- Writes a **small placeholder** payload (not valid FLAC audio) so you can validate folder layout, permissions, and scripting.
- Intended for **tests and dry runs** of the pipeline, not for listening.

## Backend: `http`

- **`music-flac sync --backend http`**
- Requires **`MUSIC_FLAC_API_URL`** or **`--api-url`**.
- Sends a **`POST`** with **`Content-Type: application/json`** and this JSON body:

```json
{
  "artist": "...",
  "album": "...",
  "title": "...",
  "tracknumber": "...",
  "discnumber": "...",
  "relative_path": "Artist/Album/file.mp3"
}
```

- Optional auth: **`MUSIC_FLAC_API_TOKEN`** or **`--api-token`** as `Authorization: Bearer <token>`.
- The **entire response body** is saved as the `.flac` file. Your server should return raw FLAC bytes (or whatever format you intend to store under a `.flac` name).

To change the method, URL shape, or payload, edit **`src/music_flac/api/http.py`**.

## Backend: `hifi`

- **`music-flac sync --backend hifi`**
- Uses a **hifi-api-compatible** server (default [hifi.geeked.wtf](https://hifi.geeked.wtf/); set **`MUSIC_FLAC_HIFI_BASE`** or **`--hifi-base-url`**).
- Per track:
  1. Build a search string from tags (artist, title, album) or the cleaned filename stem.
  2. **`GET /search?s=…&limit=…`** and pick the best hit vs. tags (`pick_best_search_item`).
  3. **`GET /track?id=<tidal_track_id>&quality=…`** trying, in order, **`LOSSLESS`**, **`HI_RES_LOSSLESS`**, **`HIGH`** until a manifest yields a URL.
  4. Decode the base64 **`manifest`**: JSON (**`application/vnd.tidal.bts`**) with a **`urls`** list, or fall back to scanning DASH/XML text for `https://…` (preferring `.flac` when present).
  5. **`GET`** the first stream URL and save the bytes as the destination file.

Upstream schema and extra endpoints (**`/trackManifests`**, **`/info`**, etc.) are documented in [binimum/hifi-api](https://github.com/binimum/hifi-api) and [hifi-api-workers](https://github.com/monochrome-music/hifi-api-workers). This backend uses **`/search`** + **`/track`** only; extend **`music_flac.hifi`** / **`HifiFlacSource`** if you need manifest types we do not parse yet.

### Smoke test: one song

```bash
music-flac hifi-fetch-one --query "Artist TrackTitle" --artist "Artist" --title "TrackTitle" -o out.flac
```

Requires network access to the hifi base URL and a working Tidal-backed deployment.

### User-Agent

Some hosts return **403** to Python’s default **urllib** user agent. **`HifiClient`** sends an explicit **User-Agent** header on JSON and CDN requests.

## Troubleshooting

| Symptom | Things to check |
|--------|------------------|
| `Not a directory` | `--source` must be an existing folder. |
| HTTP backend exits 2 | Set `MUSIC_FLAC_API_URL` or `--api-url`. |
| hifi search / track errors | Check tags, try `-v`; verify server with **`hifi-probe`**. |
| Empty or corrupt `.flac` | Server must return **only** audio bytes; check status codes and errors in logs (`-v`). |
| Wrong file names | Tag quality drives naming; see [library-mirror-naming.md](library-mirror-naming.md). |
| Skipped files | Expected if the destination exists; use **`--force`** to refetch. |

## Related

- [Configuration](configuration.md) — env vars and timeouts
- [CLI reference — `sync` / `hifi-probe` / `hifi-fetch-one`](cli-reference.md)
