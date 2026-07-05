# Magic Extractor

<p align="center">
  <img src="assets/icon.png" alt="Magic Extractor" width="250" height="250">
</p>

## Description
Magic Extractor is a universal extraction tool for Windows that identifies a file
with several detectors and routes it to the right bundled extractor. It aims to
cover mainstream compression formats, the installers you actually see today, and a
range of less common archivers.

## Quick Start
Download the [latest release](../../releases/latest), unzip it, and run:
```text
magic-extractor.exe extract mystery.bin
```
See [Examples](#examples) for `identify`, `list`, `carve`, `--recursive` and `--bruteforce`.

## Project Structure
- `src`: source code.
  - `bin`: bundled detector and extractor binaries.
    - `detectors`: DIE, Magika, binwalk (TrID's defs are converted to `data/signatures.json`).
    - `extractors`: 7z, unrar, unace, unshield, lessmsi, dark (WiX), and more.
  - `data`: runtime configuration, loaded dynamically (see below).
  - `formats`: one handler module per format family.
- `test`: sample files per format (fixtures for the extraction/detection tests).
- `tools`: developer tooling (`generate_data.py` — builds the data files from handlers).

The compiled build keeps `bin/`, `data/` and `config.ini` external to the exe so
they can be updated with a file swap; the path resolver in `main.py` finds them
beside the executable (frozen) or under `cli/` (dev).

## How detection works
For normal extraction, detectors run in this order with **early-exit** — the first
one that yields a known handler wins (cheapest first, so the ML model is usually skipped):

1. **puremagic** — pure-python, no subprocess; a cheap MIME check for well-formed archives.
2. **built-in signatures** — magic-byte patterns in `data/signatures.json`; names
   archivers the engines miss (bcm, dgca, kgb, uharc, alzip, freearc, ...) with no
   external process.
3. **DIE** (Detect It Easy) — signature engine; the specialist for installers, PE and SFX.
4. **binwalk** — short type keys (cpio, lzma, ...) and embedded content.
5. **Magika** — Google's AI content-type detector, as a catch-all.

Each detector contributes uniquely (they are complementary, not redundant): the
signature DB names archivers the engines miss, DIE handles installers/PE, binwalk
catches a few types the others miss, puremagic/Magika cover MIME.

Each handler declares its own indicators via `detection_mimes()` /
`detection_names()` / `detection_signatures()`; `tools/generate_data.py` compiles
these into `data/handlers.json` and `data/signatures.json` (with an optional
`data/extra_detections.json` merged on top). TrID is not used.

> Note: any format whose signature is missing from puremagic's
> [`magic_data.json`](https://github.com/cdgriffith/puremagic/blob/master/puremagic/magic_data.json)
> (or that puremagic reports only as a generic `application/octet-stream`) must
> declare a custom `detection_signatures()` entry in its handler — otherwise it
> will not be detected by content.

- `--bruteforce` disables early-exit: every detector runs and each detected handler
  is tried in turn (useful when the first guess is wrong).
- Executables that no detector identifies fall back to the wrapped-exe installer
  handlers (BitRock, Clickteam, PyInstaller, Inno, ...), which self-validate.
- The `carve` subcommand additionally uses binwalk's offset map to extract archives
  embedded at arbitrary offsets (e.g. inside firmware images).

The detection → handler routing map lives in `data/handlers.json` (hand-curated,
loaded at runtime); a generic-token blacklist lives in `data/detection_blacklist.json`.

## Supported Formats
See [formats.md](formats.md) for the full list of formats and their handlers.

## Installation (from source)
Most users just download the release (see [Quick Start](#quick-start)). To run from source:
```bash
git clone <repo-url>
cd magic-extractor
pip install -r cli/requirements.txt
```

## Usage
Magic Extractor uses subcommands:
```bash
python cli/main.py extract  <path> [output_dir] [options]   # detect and extract
python cli/main.py identify <path>                          # report type + candidate handlers
python cli/main.py list     <path>                          # list archive contents
python cli/main.py carve    <path> [output_dir] [options]   # carve embedded archives (binwalk offsets)
```
A bare path with no subcommand defaults to `extract` (backward compatible):
```bash
python cli/main.py <path> <output_dir> [options]
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

> In the examples below, `magic-extractor` is the built `.exe`. From source, replace
> it with `python cli/main.py` — the arguments are identical.

## Examples

**Extract an archive** — you don't need to know its type; it is auto-detected:
```text
magic-extractor extract mystery.bin
# extracts into mystery_extracted/ next to the file
```

**Identify** a file without touching it — shows what each detector saw and which
handler would run:
```text
magic-extractor identify setup.exe
File: setup.exe
  [DIE] detect   inno setup installer
Candidate handlers (in order):
  - FormatInnoSetupHandler
```

**List** an archive's contents (no extraction):
```text
magic-extractor list backup.7z
```

**Recursive** — extract archives found inside the output (e.g. a .tar.gz, or an
installer that contains more archives), up to `--max-depth` levels:
```text
magic-extractor extract app-1.0.tar.gz --recursive
```

**Bruteforce** — when detection is unsure, try every handler that matched instead
of stopping at the first:
```text
magic-extractor extract weird-archive.dat --bruteforce
```

**Carve** — pull archives that are embedded at some offset inside a bigger file
(classic for firmware images). Inspect first, then carve:
```text
magic-extractor carve router-firmware.bin --list
IDX      OFFSET          SIZE  NAME       DESCRIPTION
  0  0x00000000       793,720  pe         Windows PE binary
  1  0x000c1c78     2,495,983  lzma       LZMA compressed data

magic-extractor carve router-firmware.bin              # carve + extract the known blobs
magic-extractor carve router-firmware.bin --fragment 1 # carve only fragment #1
```

## Building (Windows)
```bash
cd src
pyinstaller --onefile main.py --name magic-extractor --collect-data puremagic
```
Then copy `bin/`, `data/` and `config.ini` next to `dist/magic-extractor.exe`.
CI does this automatically — see `.github/workflows/release.yml`.

## License
LGPL-3.0-only — see `LICENSE.txt`.

## Authors
- Lead Developer: DSR! — xchwarze@gmail.com
- Thanks to all contributors.
