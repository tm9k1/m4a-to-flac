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

## hifi-api-compatible services

Public or self-hosted instances that implement the **hifi-api** shape (for example [hifi.geeked.wtf](https://hifi.geeked.wtf/)) speak a **Tidal-oriented** JSON API described in upstream projects such as [binimum/hifi-api](https://github.com/binimum/hifi-api) and [monochrome-music/hifi-api-workers](https://github.com/monochrome-music/hifi-api-workers).

Typical pieces:

- **`GET /`** — service metadata (`version`, `Repo`). **`music-flac hifi-probe`** calls this.
- **`GET /search`** — discover tracks (query parameters per upstream docs).
- **`GET /info?id=<tidal_track_id>`** — track metadata.
- **`GET /track?id=<tidal_track_id>&quality=…`** — stream manifest (often base64 JSON with FLAC URLs).
- **`GET /trackManifests`** — richer manifests (preferred in upstream docs for some formats).

**music-flac** does not yet implement search → manifest → CDN download as a built-in **`FlacSource`**. The **`http`** backend is a simple **POST→bytes** contract for your **own** gateway. To use hifi-api directly, add a new backend or extend the HTTP client to match that API.

### User-Agent

Some hosts return **403** to Python’s default **urllib** user agent. **`hifi-probe`** and **`HifiClient`** send an explicit **User-Agent** header; if you add custom clients, keep that in mind.

## Troubleshooting

| Symptom | Things to check |
|--------|------------------|
| `Not a directory` | `--source` must be an existing folder. |
| HTTP backend exits 2 | Set `MUSIC_FLAC_API_URL` or `--api-url`. |
| Empty or corrupt `.flac` | Server must return **only** audio bytes; check status codes and errors in logs (`-v`). |
| Wrong file names | Tag quality drives naming; see [library-mirror-naming.md](library-mirror-naming.md). |
| Skipped files | Expected if the destination exists; use **`--force`** to refetch. |

## Related

- [Configuration](configuration.md) — env vars and timeouts
- [CLI reference — `sync` / `hifi-probe`](cli-reference.md)
