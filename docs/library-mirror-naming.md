# Library scanning, mirror layout, and naming

## What gets scanned

The scanner walks the **`--source`** directory **recursively** and considers **regular files** whose extension is one of:

`.mp3`, `.flac`, `.m4a`, `.aac`, `.ogg`, `.opus`, `.wav`, `.wma`

Other files (images, text, folders) are ignored for track collection.

## Metadata (tags)

Tags are read with **Mutagen** (`mutagen.File`). Common frame mappings include:

- **Artist:** `TPE1` (ID3), `ARTIST` (Vorbis), `©ART` (MP4)
- **Album:** `TALB`, `ALBUM`, `©alb`
- **Title:** `TIT2`, `TITLE`, `©nam`
- **Track number:** `TRCK`, `TRACKNUMBER`, `TRACK`
- **Disc number:** `TPOS`, `DISCNUMBER`, `DISC`

If a file cannot be read, the track is still listed where possible; errors are attached to the record and may appear in **`scan`** output.

## Mirror layout (folders)

For each audio file, the mirror path keeps the **same parent directories** relative to the library root.

**Example:** Source file

`Artist Name/Album Name/01 - Song.mp3`

becomes something like

`Artist Name/Album Name/<clean name>.flac`

under **`--dest`**, where **`<clean name>`** is computed from tags and disambiguation rules below—not necessarily the original filename.

## Destination filenames (disambiguation)

Naming is **per source folder** (all tracks that share the same `relative_path.parent` compete for unique names).

1. **Tier 0 — title only**  
   Use the **track title** from tags, sanitized for file names.  
   If the title tag is missing, the tool uses the **file stem** after [YouTube id stripping](#youtube-style-id-stripping).

2. **Tier 1 — title and artist**  
   If two or more tracks in that folder would get the **same** tier-0 name (compared case-insensitively), those tracks use **`Title - Artist`**.

3. **Tier 2 — title, artist, and album**  
   If collisions remain, use **`Title - Artist - Album`**.

4. **Numeric suffixes**  
   If metadata is still identical for multiple tracks in the same folder, names become **`… (2)`**, **`… (3)`**, … after the first occurrence.

### Sanitization

Characters that are problematic on common file systems (`\ / : * ? " < > |`) are replaced with spaces; repeated whitespace is collapsed. Empty segments fall back to placeholders like **`Unknown`** / **`Unknown Artist`** / **`Unknown Album`** where applicable.

## YouTube-style ID stripping

Many source files append an 11-character **YouTube-style** id (letters, digits, `_`, `-`). The tool strips a trailing id when it appears as:

- Brackets: `… [dQw4w9WgXcQ]`
- Parens: `… (dQw4w9WgXcQ)`
- After whitespace: `… dQw4w9WgXcQ`
- After separators `-`, `–`, `—`, or `_`: `… - dQw4w9WgXcQ`

Stripping runs repeatedly until no pattern matches. This cleaned stem is used **only as a fallback title** when tag **title** is missing.

## Path display (forward slashes)

CLI output uses **POSIX-style paths** (`Artist/Album/track.flac`) so plans and logs look the same on Windows and Unix. Actual file operations still use the OS path APIs.

## Related

- [CLI reference — `scan` / `plan` / `sync`](cli-reference.md)
- [Sync and backends](sync-and-backends.md)
