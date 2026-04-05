# CLI reference

Syntax: `music-flac [global options] <command> [command options]`

Global options apply before the subcommand.

## Global options

| Option | Description |
|--------|-------------|
| `-h`, `--help` | Show help and exit. |
| `--version` | Print program version and exit. |
| `-v`, `--verbose` | Enable DEBUG logging on stderr. |

---

## `scan`

**Purpose:** Recursively find audio files under the source root, read metadata with Mutagen, and print a human-readable list (artist, album, title, relative path).

**Does not** write files or call the network.

### Options

| Option | Description |
|--------|-------------|
| `--source PATH` | Library root (default: see [Configuration](configuration.md#default-paths)). |

### Exit codes

- **0** — Success.
- **2** — Source path is not a directory.

### Example

```bash
music-flac scan --source "D:/Libraries/Music/Good Music"
```

---

## `plan`

**Purpose:** Same scan as `scan`, then print how each source file maps to a **`.flac`** path under the mirror root. Uses **forward slashes** in output. Leaf filenames follow the [naming rules](library-mirror-naming.md#destination-filenames-disambiguation).

**Does not** write files or call the network.

### Options

| Option | Description |
|--------|-------------|
| `--source PATH` | Library root (default: configured default). |
| `--dest PATH` | FLAC mirror root (default: configured default). |

### Exit codes

- **0** — Success.
- **2** — Source path is not a directory.

### Example

```bash
music-flac plan --source "D:/Libraries/Music/Good Music" --dest "D:/Libraries/Music/Good Music FLACs"
```

---

## `sync`

**Purpose:** Scan the library, compute mirror paths (same as `plan`), then for each track **fetch bytes** from a backend and write a `.flac` file. Skips destinations that already exist as non-empty files unless **`--force`**.

### Options

| Option | Description |
|--------|-------------|
| `--source PATH` | Library root. |
| `--dest PATH` | FLAC mirror root. |
| `--backend stub \| http \| hifi` | **`stub`:** placeholder. **`http`:** POST JSON; response body = file bytes. **`hifi`:** hifi-api search → track manifest → CDN. |
| `--api-url URL` | Override `MUSIC_FLAC_API_URL` for HTTP backend. |
| `--api-token TOKEN` | Override `MUSIC_FLAC_API_TOKEN` for HTTP backend. |
| `--hifi-base-url URL` | Override `MUSIC_FLAC_HIFI_BASE` for **`hifi`** backend. |
| `--workers N` | Parallel track downloads (thread pool). Default: `MUSIC_FLAC_SYNC_WORKERS` or **8**. Use **`1`** for sequential. |
| `--dry-run` | Do not write files; still logs what would happen. |
| `--force` | Re-fetch and overwrite even if the destination file exists and is non-empty. |

### Exit codes

- **0** — Success (no per-track errors).
- **1** — One or more tracks failed (details on stderr).
- **2** — Source path is not a directory, or HTTP backend chosen without a URL.

### Examples

```bash
music-flac sync --backend stub --dry-run
music-flac sync --backend http --api-url https://example.com/flac
music-flac sync --backend hifi --hifi-base-url https://hifi.geeked.wtf/
music-flac sync --backend hifi --workers 16
```

See [Sync and backends](sync-and-backends.md) for backend details.

---

## `hifi-probe`

**Purpose:** Perform **`GET /`** against a **hifi-api-compatible** base URL and print the JSON response (typically `version` and `Repo`). Useful to verify connectivity and server identity.

### Options

| Option | Description |
|--------|-------------|
| `--base-url URL` | Server root (default: `MUSIC_FLAC_HIFI_BASE` or `https://hifi.geeked.wtf/`). Trailing slash optional. |

Uses `MUSIC_FLAC_API_TIMEOUT` as the request timeout unless you change config code.

### Exit codes

- **0** — JSON printed successfully.
- Non-zero — Network or HTTP error (message on stderr).

### Example

```bash
music-flac hifi-probe --base-url https://hifi.geeked.wtf/
```

See [Sync and backends — Backend: `hifi`](sync-and-backends.md#backend-hifi).

---

## `hifi-fetch-one`

**Purpose:** Run **`GET /search?s=…`**, pick the best hit (optionally guided by **`--title` / `--artist` / `--album`**), resolve **`GET /track`**, download the first stream URL, and write **`--output`**. Intended as a **smoke test** or manual one-off download (see [Sync and backends](sync-and-backends.md#backend-hifi)).

### Options

| Option | Description |
|--------|-------------|
| `--base-url URL` | Same as **`hifi-probe`** (default from env). |
| `--query STR` | Track search string (`s` parameter). Optional if you build a query from **`--artist` / `--title` / `--album`**. |
| `--title` / `--artist` / `--album` | Hints for choosing among search results. |
| `--output` / `-o PATH` | Destination file (required). |

At least one of **`--query`**, **`--title`**, **`--artist`**, or **`--album`** is required.

### Exit codes

- **0** — File written; byte count printed on stdout.
- **2** — Missing search hints or fatal usage error.
- Non-zero — Search empty, manifest/URL failure, or network error.

### Example

```bash
music-flac hifi-fetch-one --query "Oasis Wonderwall" --artist "Oasis" --title "Wonderwall" -o wonderwall.flac
```
