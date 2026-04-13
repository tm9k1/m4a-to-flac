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
| `--include PATTERN` | Include only tracks matching glob pattern (can be used multiple times). |
| `--exclude PATTERN` | Exclude tracks matching glob pattern (can be used multiple times). |
| `--name-template TEMPLATE` | Custom filename template using `{artist}`, `{album}`, `{title}`, `{tracknumber}`, etc. |

### Exit codes

- **0** — Success.
- **2** — Source path is not a directory.

### Example

```bash
music-flac plan --source "D:/Libraries/Music/Good Music" --dest "D:/Libraries/Music/Good Music FLACs"
```

---

## `sync`

**Purpose:** Scan the library, compute mirror paths (same as `plan`), then for each track **fetch bytes** from a hifi-compatible source and write a `.flac` file. Supports interactive approval, include/exclude filtering, quality selection, and enhanced metadata.

### Options

| Option | Description |
|--------|-------------|
| `--source PATH` | Library root. |
| `--dest PATH` | FLAC mirror root. |
| `--base-url URL` | Override `MUSIC_FLAC_HIFI_BASE` for hifi backend. |
| `--workers N` | Parallel track downloads (thread pool). Default: `MUSIC_FLAC_SYNC_WORKERS` or **8**. Use **`1`** for sequential. |
| `--dry-run` | Do not write files; still logs what would happen. |
| `--copy-missing-tracks` | Copy missing tracks from source directory preserving original extension if hifi fetch fails. |
| `--interactive` | Review and approve each change interactively before applying. |
| `--include PATTERN` | Include only tracks matching glob pattern (can be used multiple times). |
| `--exclude PATTERN` | Exclude tracks matching glob pattern (can be used multiple times). |
| `--quality {LOSSLESS,HI_RES_LOSSLESS,HIGH}` | Preferred quality level for FLAC downloads (default: LOSSLESS). |
| `--name-template TEMPLATE` | Custom filename template using `{artist}`, `{album}`, `{title}`, `{tracknumber}`, etc. |
| `--enhance-metadata` | Fetch and apply additional metadata (genres, cover art) from hifi API. |

### Exit codes

- **0** — Success (no per-track errors).
- **1** — One or more tracks failed (details on stderr).
- **2** — Source path is not a directory.

### Examples

```bash
music-flac sync --dry-run
music-flac sync --base-url https://hifi.geeked.wtf/
music-flac sync --workers 16
music-flac sync --copy-missing-tracks
```
