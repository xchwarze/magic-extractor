# Magic Extractor

## Description
Magic Extractor is a universal extraction tool for Windows that identifies a file
with several detectors and routes it to the right bundled extractor. It aims to
cover mainstream compression formats, the installers you actually see today, and a
range of less common archivers.

## Development Status
Functional but still under active development; no release tags yet. Features and
the on-disk layout may still change.

## Project Structure
- `src`: source code.
  - `bin`: bundled detector and extractor binaries.
    - `detectors`: DIE, Magika, binwalk (TrID's defs are converted to `data/signatures.json`).
    - `extractors`: 7z, unrar, unace, unshield, lessmsi, dark (WiX), and more.
  - `data`: runtime configuration, loaded dynamically (see below).
  - `formats`: one handler module per format family.
- `test`: sample files per format (fixtures for the extraction/detection tests).
- `tools`: developer tooling (`build_handlers.py`).

The compiled build keeps `bin/`, `data/` and `config.ini` external to the exe so
they can be updated with a file swap; the path resolver in `main.py` finds them
beside the executable (frozen) or under `src/` (dev).

## How detection works
For normal extraction, detectors run in this order with **early-exit** — the first
one that yields a known handler wins (cheapest first, so the ML model is usually skipped):

1. **puremagic** — pure-python, no subprocess; a cheap MIME check for well-formed archives.
2. **built-in signatures** — magic-byte patterns in `data/signatures.json`, harvested
   from the public TrID defs by `tools/convert_trid_defs.py`; names most archivers
   (alzip, freearc, dgca, kgb, uharc, ...) with no external process.
3. **DIE** (Detect It Easy) — signature engine; the specialist for installers, PE and SFX.
4. **binwalk** — short type keys (cpio, lzma, ...) and embedded content.
5. **Magika** — Google's AI content-type detector, as a catch-all.

Each detector contributes uniquely (they are complementary, not redundant): the
signature DB names most archivers, DIE handles installers/PE, binwalk catches a
few types the others miss, puremagic/Magika cover MIME. (TrID itself is no longer
run — its signatures live in `data/signatures.json`.)

- `--bruteforce` disables early-exit: every detector runs and each detected handler
  is tried in turn (useful when the first guess is wrong).
- Executables that no detector identifies fall back to the wrapped-exe installer
  handlers (BitRock, Clickteam, PyInstaller, Inno, ...), which self-validate.
- The `carve` subcommand additionally uses binwalk's offset map to extract archives
  embedded at arbitrary offsets (e.g. inside firmware images).

The detection → handler routing map lives in `data/handlers.json` (hand-curated,
loaded at runtime); a generic-token blacklist lives in `data/detection_blacklist.json`.

## Supported Formats
See `formats.md` for the full list of formats and their handlers.

## Installation
```bash
git clone <repo-url>
cd magic-extractor
pip install -r src/requirements.txt
```

## Usage
Magic Extractor uses subcommands:
```bash
python src/main.py extract  <path> [output_dir] [options]   # detect and extract
python src/main.py identify <path>                          # report type + candidate handlers
python src/main.py list     <path>                          # list archive contents
python src/main.py carve    <path> [output_dir] [options]   # carve embedded archives (binwalk offsets)
```
A bare path with no subcommand defaults to `extract` (backward compatible):
```bash
python src/main.py <path> <output_dir> [options]
```

`extract` options:
- `--password <password>`: password for encrypted archives.
- `-r`, `--recursive`: extract archives found inside the output (bounded by `--max-depth`, default 5).
- `-b`, `--bruteforce`: try every handler detected instead of stopping at the first.
- `--open-output-folder <bool>`: open the output folder when done.
- `--check-free-space <bool>`: warn if the output volume may lack room.
- `--check-unicode <bool>`: warn about non-ASCII extracted names.
- `--fix-file-extensions <bool>`: rename extracted files whose content type disagrees with their extension.
- `--create-log-files <bool>`: write a per-run log to the output dir.
- `--no-fast-check`: read the whole file for detection instead of the first 2048 bytes.
- `--update-defaults`: persist the given settings as defaults in `config.ini`.

`carve` options: `--list` (print the binwalk fragment table), `--fragment N` (carve one
fragment by index), `--raw` (carve every fragment, not only handler-known ones).

## Building (Windows)
```
pyinstaller magic-extractor.spec
```
Then copy `src/bin`, `src/data` and `src/config.ini` into `dist/magic-extractor/`.

## License
LGPL-3.0-only — see `LICENSE.txt`.

## Authors
- Lead Developer: DSR! — xchwarze@gmail.com
- Thanks to all contributors.
