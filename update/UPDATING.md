# Updating the bundled tools

This folder vendors the [universal-tool-updater](https://github.com/xchwarze/universal-tool-updater)
release (`updater.exe` + `unrar.exe`) configured to refresh the detector/extractor
binaries under `../cli/bin/`. `tools.ini` holds the config; `scripts/` holds one
per-tool `post_unpack` cleanup that trims/rearranges each download into the exact
layout magic-extractor expects.

## Usage (Windows)

Run from **this** folder — the updater chdir's to its own location, so every
`folder =` in `tools.ini` resolves relative to `update/` into `../cli/bin/`.

```
updater.exe                     # check + update every tool
updater.exe --dry-run           # report what's outdated, download nothing
updater.exe -u DIE 7-Zip        # update only the named sections
updater.exe -f -u Modern7z      # force re-download even if up to date
```

`updater.exe` and `unrar.exe` are the compiled release; the config lives beside
them. `unrar.exe` is what lets the updater unpack the `.rar` innounp release.

## What each tool pulls

| Section | Source | Notes |
|---------|--------|-------|
| DIE | github `horsicq/DIE-engine` | full portable; `clean-die.bat` trims to `diec.exe` + Qt Core/Script + `db`/`info` |
| Magika | web scrape of `google/magika` releases | picks the newest `cli`-tag Windows zip (see caveat) |
| 7-Zip | github `ip7z/7zip` | 32-bit installer; `clean-7z.bat` extracts `7z.exe`+`7z.dll` with the current 7z, `merge` keeps `Formats\`/`Codecs\` |
| innounp | SourceForge | `.rar`, unpacked via bundled `unrar.exe` |
| lessmsi | github `activescott/lessmsi` | `clean-lessmsi.bat` drops the GUI + language folders |
| unshield | scoop `main` (version-check only) + `scripts\update-unshield.bat` | scoop `.7z` is BCJ2 (py7zr can't unpack); the section just detects new versions, the helper installs with the bundled full 7z |
| PeaZip | github `peazip/PeaZip` | `clean-peazip.bat` isolates `pea.exe` from the portable |
| 8 tc4shell plugins | tc4shell.com | version scraped from the page, static `.zip` link; `merge` + `clean-7z-plugin.bat` keeps the 32-bit files (flat, or promoted out of a `32\` subfolder like Modern7z) and renames each generic `ReadMe.txt` to `<Plugin>-ReadMe.txt` so they don't overwrite each other |

## Caveats (verify on first real run)

- **7-Zip** ships the plugin-capable `7z.exe`+`7z.dll` only inside the NSIS
  installer, so `clean-7z.bat` bootstraps extraction with the *currently
  bundled* 7z. The 32-bit installer (`7z####.exe`) is used on purpose — the
  bundle's plugins are `*.32.dll`. If you ever switch the bundle to 64-bit, use
  `re_download = 7z(?:\S+)-x64.exe` and keep `*.64.dll` in `clean-7z-plugin.bat`.
- **tc4shell plugin filenames**: `Asar.zip` and `Modern7z.zip` were confirmed
  byte-for-byte; the other six (`Forensic7z`, `Iso7z`, `ExFat7z`, `eDecoder`,
  `Py7z`, `Grit7z`) follow the identical page template — sanity-check them on the
  first run.
- **Magika**: `google/magika` publishes CLI / python / rust release trains under
  one `latest` pointer, and "latest" is usually a python release with no Windows
  binary. So it's configured as a `web` scrape of the releases page, taking the
  newest `cli`-tag `magika-cli-x86_64-pc-windows-msvc.zip`. That relies on the
  latest cli release still being present in the releases-listing HTML; if Google
  reworks the release layout, re-check the `re_download` regex.
- **unshield**: the scoop `main` package is a BCJ2 `.7z` the updater's py7zr
  can't unpack, and there's no hook between download and unpack to re-fix it. It's
  kept as a section purely as a **version tracker**: while `local_version` equals
  scoop's, the updater reports "latest" and downloads nothing. When scoop bumps
  unshield, the updater flags the new version and then errors on the BCJ2 unpack
  (that error is the signal). To install it, run `scripts\update-unshield.bat`
  (extracts with the bundled full 7z), then bump `local_version` under
  `[unshield]` (and the `VER` in the helper) so the check goes quiet again.
- **Comments don't survive**: the updater rewrites `tools.ini` via configparser
  after each run, which strips `#` comments. That's why the config is bare and
  all the notes live here.
- **Modern7z** ships its DLLs in `32\`/`64\` subfolders (not flat); the plugin
  cleanup promotes the `32\` set to the folder root for the 32-bit bundle.
- **innounp**: effectively frozen (v0.50, 2020). `files/latest/download` can
  resolve to the `src` rar; pin `update_url` to the exact binary rar if that
  ever misbehaves.
- The updater writes each tool's `local_version` back into `tools.ini` after a
  successful run — expect that file to change.
