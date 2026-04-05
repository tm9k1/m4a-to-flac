# Agent notes — music-flac

Context for anyone (human or assistant) working in this repository.

## What we’re building

1. **Scan** the source library (`MUSIC_FLAC_SOURCE`, default `D:\Libraries\Music\Good Music`), parse tags (Mutagen), print a readable listing (`music-flac scan`).
2. **Mirror** the same **parent** paths under the FLAC root (`MUSIC_FLAC_DEST`, default `D:\Libraries\Music\Good Music FLACs`); each leaf is **`.flac`** with a **clean, disambiguated name** from tags (`Title` → `Title - Artist` → `Title - Artist - Album`, plus numeric suffixes; strip trailing YouTube id from stem when title is missing). CLI paths print with **forward slashes** (`posix_display` / `as_posix()`).
3. **Fetch** FLAC bytes per track via a pluggable **`FlacSource`**: `stub` for tests, `http` POST JSON to `MUSIC_FLAC_API_URL` (see `music_flac.api.http`). For **hifi-api**-style Tidal proxies (e.g. [hifi.geeked.wtf](https://hifi.geeked.wtf/)), see `music_flac.hifi` and upstream [binimum/hifi-api](https://github.com/binimum/hifi-api) docs; `music-flac hifi-probe` checks `GET /`.

## Design preferences

- **Keep scope small.** One clear CLI or module entry point; avoid frameworks unless needed.
- **Stable “song record” shape:** Prefer a simple dataclass or dict schema (artist, album, title, track number, path, codec, etc.) that both the printer and a future API client can consume.
- **Libraries:** Use well-maintained tag readers (e.g. Mutagen) rather than reinventing parsers per format.
- **Errors:** Missing tags or unreadable files should degrade gracefully (warn, skip, or show placeholders) instead of crashing the whole run.

## Out of scope (for now)

- Heavy UI beyond CLI output unless explicitly requested.
- Validating that HTTP responses are real FLAC streams (trust API or add `flac`/`mutagen` checks later if needed).

## Files to respect

- **`README.md`** — user-facing overview; update it when behavior or usage changes meaningfully.
- **`docs/`** — user help (configuration, CLI, naming, backends); keep in sync when behavior or flags change.
- **`AGENTS.md`** — this file; update when direction or constraints change.
- **`CHANGELOG.md`** — add a bullet under the current version for user-visible or structural changes each iteration.

## When adding code

- Match existing style (imports, naming, no unnecessary abstractions).
- Add or update `requirements.txt` with pinned or minimum versions when introducing dependencies.
- Prefer explicit CLI flags (`--path`, `--verbose`) over magic defaults.
