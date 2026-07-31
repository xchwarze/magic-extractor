# Magic Extractor 1.2.0 — Massive format expansion

The tool performed as I had expected. So, in keeping with an old tradition, I'm
sharing a track with you to celebrate.

*'search of a life worth living'* by hkmori — Bandcamp · Helltube

This release roughly triples the number of recognized formats: **80+ formats**
are now auto-detected and extracted, including forensic disk images, optical
disc images, mail/message stores and modern compression codecs. It also splits
plugin-dependent 7-Zip formats into their own handler and ships a handful of
detection and reliability fixes.

## New: forensic disk images

Detected by magic and extracted via the bundled forensic7z plugin:

* **EnCase / EWF** — `.E01`, `.S01`, `.Ex01`, `.L01`, `.Lx01`
* **AccessData FTK Imager** — `.AD1`
* **Advanced Forensics Format** — `.AFF`
* **WinHex evidence** — `.whx`

## New: optical disc images

Via the bundled Iso7z plugin:

* Compact / Compressed ISO (`.ciso`, `.cso`), MAME **CHD**, **ECM**, UltraISO
  **ISZ**, Alcohol 120% **MDS**, CloneCD **CCD**, **zisofs**.

## New: mail & message stores

Via the bundled eDecoder plugin:

* Outlook **TNEF** (winmail.dat), Outlook Express **DBX**, **WARC** web archives,
  **BinHex** (`.hqx`), **yEnc**, The Bat! **TBB**, **MacBinary III**.

## New: modern compression & app packages

* **LZ4 / LZ5 / Lizard** frames and Firefox **jsonlz4 / mozlz4** (Modern7z).
* **Electron .asar** (Asar plugin) and **Chromium resource pak** (Grit7z).
* **PyInstaller** executables now extract via the Py7z plugin.
* More native 7-Zip filesystems now detected by magic: **NTFS, GPT, UEFI
  firmware volumes** (ExFAT is detected too, via the ExFat7z plugin).

## Under the hood

* **New `Format7zExtHandler`** — plugin-dependent 7-Zip formats are separated
  from the native ones. Same extraction (it shells to 7-Zip), but clearly marks
  which formats need a plugin. Plugins ship in `7z/Formats/` and `7z/Codecs/`.
* All magic signatures were cross-checked against the TrID database and the
  Detect-It-Easy signature set (this caught and fixed a wrong EnCase Lx01 magic).
* Detection routing data (`handlers.json` / `signatures.json`) is generated from
  each handler's declarations — see the new **`docs/adding-a-handler.md`** guide
  for how to add a format end to end.
* Extraction success/failure is now decided in one place — the tool's exit code
  (`BaseExtractor.run_extraction`) — removing per-handler boilerplate and a class
  of false failures.

## Fixes

* **Inno Setup** installers now extract correctly — a cleanup bug reported every
  successful extraction as a failure.
* **ZPAQ** archives now extract — the output/password arguments were malformed,
  so extraction always failed.
* **Self-extracting ARC / KGB / UHARC** `.exe` archives now route to their own
  extractor instead of being claimed by the Inno Setup unpacker.
* Extractors that succeed without printing anything are no longer reported as
  failed; when a tool does fail, its real error is logged.
* Boolean `extract` options (`--open-output-folder`, `--check-free-space`,
  `--check-unicode`, `--fix-file-extensions`, `--create-log-files`) now honor
  `true`/`false`. Previously any value counted as *true*, so a default saved
  with `--update-defaults` could not be turned back off.
* A missing detector binary no longer crashes the whole run.
* Directory (batch) extraction now exits non-zero if any file failed.
* The output directory is now **created automatically** if it doesn't exist
  (previously `extract <file> <newdir>` errored).
* Corrected the EnCase `.Lx01` magic (`LEF2`, not `LVF2`).
* Normalized the bundled tc4shell plugin ReadMe URLs (http→https; fixed a 404).

## Notes

Plugin-dependent formats (marked † in `formats.md`) are identified even without
their plugin, but only extract when the matching plugin is present in the bundled
7-Zip's `Formats/` / `Codecs/` folder (they ship with the release). See
[`formats.md`](formats.md) for the full list and `THIRD-PARTY-NOTICES.md` for the
bundled tools.

**Full Changelog**: https://github.com/xchwarze/magic-extractor/compare/1.1.0...1.2.0
