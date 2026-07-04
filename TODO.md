# TODO

Pending work for magic-extractor. Full design in
`docs/superpowers/specs/2026-07-04-universal-extractor-roadmap-design.md`.

## Installer coverage vs UniExtract2

Handlers written, need the binary copied from a UniExtract2 release into the
given folder, then `build_handlers.py --live` with a sample to map detection:
- [ ] InstallShield -> `src/bin/extractors/unshield/unshield.exe`
- [ ] PyInstaller  -> `src/bin/extractors/pyinstxtractor/pyinstxtractor.exe`
- [ ] Wise         -> `src/bin/extractors/e_wise/e_wise.exe`

Likely already covered (verify): GOG installers (Inno-based -> existing innounp),
Advanced/Actual Installer (MSI-based -> existing MSI/7z).

Add on demand (niche/legacy): Setup Factory, Gentee, InstallAware, Installer VISE,
Smart Install Maker, Create Install, InstallForge, Ghost Installer, Install4j,
MSCF, Netopsystems FEAD, Asar (Electron, needs node).

Skip (out of scope): 500+ game archives, niche CD-image formats, multimedia tracks,
legacy archives (StuffIt/Zoo/LBR/LZX), exe packers (UPX/Enigma/MoleBox).

## Needs Windows / samples
- [ ] Map detections for the new handlers: add sample dirs `test/bitrock/`,
      `test/cicdec/`, `test/dgca/`, `test/wix/` (or `msi`), then run
      `python tools/build_handlers.py --live`. Until mapped, these handlers are
      registered but not reachable by detection.
- [ ] Verify `dark.exe` (wix) CLI — current command is a best guess:
      `dark.exe <input> -x <dir> <out.wxs>`. Confirm with `dark.exe -?`.

## Confirmed extractor CLIs
- dgca: `dgcac e <archive> <out>` / `l <archive>` (verified against tool output).
- cicdec: `cicdec <installer> <out>` (verified against tool output).
- bitrock: `bitrock-unpacker.exe <installer> <out>` (from README).

## Remaining phases
- [ ] Phase 8 — build the exe on Windows: `pyinstaller magic-extractor.spec`,
      then copy `src/bin`, `src/data`, `src/config.ini` into `dist/magic-extractor/`
      (bin/data/config are external + updatable). Spec + config base-path already done.
- [ ] Phase 4 deferred flags: `fix_file_extensions`, `warn_before_executing`
      (no execution point today), `extract_video_tracks` (niche, needs ffmpeg).

## Done
- Phase 1 — empirical `handlers.json` + `build_handlers.py` + `detection_blacklist.json`.
- Phase 2 — detector pipeline refactor + puremagic demotion (`detection_filter`).
- Phase 3 — `extract`/`identify`/`list` subcommands (bare path -> extract).
- Phase 4 — `check_free_space` (+ Windows disk fix), `open_output_folder`,
  `create_log_files`, `check_unicode`.
- Phase 8 groundwork — PyInstaller spec + `config.ini` resolved via base path.
- Phase 5 — `carve` subcommand (binwalk offsets -> carve -> extract).
- Phase 6 — bitrock/cicdec/dgca/wix handlers (dgca/cicdec CLIs verified).
- Phase 7 — recursive extraction (`-r`/`--max-depth`).
