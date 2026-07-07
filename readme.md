# Magic Extractor

<p align="center">
  <img src="assets/icon.png" alt="Magic Extractor" width="250" height="250">
</p>

## Description
Magic Extractor is a universal extraction tool for Windows that identifies a file
with several detectors and routes it to the right bundled extractor. It aims to
cover mainstream compression formats, the installers you actually see today, and a
range of less common archivers.

It auto-detects **80+ formats** — archives, installers, disk images, forensic
images (EWF/AFF/AD1), disc images, mail stores and modern codecs. See
[`formats.md`](formats.md) for the full list.

## Quick Start
Download the [latest release](../../releases/latest), unzip it, and run:
```text
magic-extractor.exe extract mystery.bin
```
See [Examples](#examples) for `identify`, `list`, `carve`, `--recursive` and `--bruteforce`.

## Project Structure
- `cli`: source code.
  - `bin`: bundled detector and extractor binaries.
    - `detectors`: DIE, Magika, binwalk (TrID's defs are converted to `data/signatures.json`).
    - `extractors`: 7z, unrar, unace, unshield, lessmsi, dark (WiX), and more.
  - `data`: runtime configuration, loaded dynamically (see below).
  - `formats`: one handler module per format family.
- `gui`: optional tkinter front-end that wraps the CLI (see [GUI](#gui)).
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
  handlers (BitRock, Clickteam, Inno, ...), which self-validate.
- The `carve` subcommand additionally uses binwalk's offset map to extract archives
  embedded at arbitrary offsets (e.g. inside firmware images).

The detection → handler routing map lives in `data/handlers.json` (hand-curated,
loaded at runtime); a generic-token blacklist lives in `data/detection_blacklist.json`.

## Supported Formats
See [formats.md](formats.md) for the full list of formats and their handlers.

## Adding a format
To add support for a new format, see
[docs/adding-a-handler.md](docs/adding-a-handler.md) — the end-to-end guide
(handler class, detection declaration, DIE/TrID lookup, magic signatures,
regenerating the routing data, bundling the tool, and testing).

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
- `--open-output-folder <true|false>`: open the output folder when done.
- `--check-free-space <true|false>`: warn if the output volume may lack room.
- `--check-unicode <true|false>`: warn about non-ASCII extracted names.
- `--fix-file-extensions <true|false>`: rename extracted files whose content type disagrees with their extension.
- `--create-log-files <true|false>`: write a per-run log to the output dir.

  (Each defaults to its `config.ini` value when omitted; combine with
  `--update-defaults` to persist the given value — e.g. `--open-output-folder false
  --update-defaults` turns a previously-saved default off.)
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

## GUI
An optional tkinter front-end (in `gui/`) wraps the CLI — a Universal-Extractor-style
window with drag-and-drop, a batch queue, run history and a Preferences dialog. It
shells out to the same `main.py`, so detection and extraction behave identically.
```bash
python gui/main.py                 # launch the window
python gui/main.py <file> [outdir] # prefill the source (and destination)
python gui/main.py <file> /scan    # prefill and start in identify mode
```
Drag-and-drop needs the optional `tkinterdnd2` package (`pip install -r gui/requirements.txt`);
without it the window still works, minus drop support. It can also register an Explorer
context-menu entry from its Preferences dialog.

## Building (Windows)
```bash
cd cli
pyinstaller --onefile main.py --name magic-extractor --collect-data puremagic
```
Then copy `bin/`, `data/` and `config.ini` next to `dist/magic-extractor.exe`.
CI does this automatically — see `.github/workflows/release.yml`.

## License
MIT — see `LICENSE.txt`. Note: the bundled third-party extractor/detector
binaries under `cli/bin/` keep their own licenses (some proprietary freeware)
and are not covered by MIT; verify their redistribution terms before shipping.

## Authors
- Lead Developer: DSR! — xchwarze@gmail.com
- Thanks to all contributors.
