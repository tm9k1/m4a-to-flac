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
| `--backend stub \| http` | **`stub`:** placeholder content (testing). **`http`:** POST JSON to your API; response body = file bytes. |
| `--api-url URL` | Override `MUSIC_FLAC_API_URL` for HTTP backend. |
| `--api-token TOKEN` | Override `MUSIC_FLAC_API_TOKEN` for HTTP backend. |
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
```

See [Sync and backends](sync-and-backends.md) for backend details.

---

## `hifi-probe`

**Purpose:** Perform **`GET /`** against a **hifi-api-compatible** base URL and print the JSON response (typically `version` and `Repo`). Useful to verify connectivity and server identity.

### Options

| Option | Description |
|--------|-------------|
| `--base-url URL` | Server root (default `https://hifi.geeked.wtf/`). Trailing slash optional. |

Uses `MUSIC_FLAC_API_TIMEOUT` as the request timeout unless you change config code.

### Exit codes

- **0** — JSON printed successfully.
- Non-zero — Network or HTTP error (message on stderr).

### Example

```bash
music-flac hifi-probe --base-url https://hifi.geeked.wtf/
```

See [Sync and backends — hifi-api-compatible services](sync-and-backends.md#hifi-api-compatible-services).
