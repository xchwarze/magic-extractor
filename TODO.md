# TODO

Pending work for magic-extractor. Full design in
`docs/superpowers/specs/2026-07-04-universal-extractor-roadmap-design.md`.

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
- [ ] Phase 8 — PyInstaller packaging; fix `config.ini` path to be base-path relative.
- [ ] Phase 4 deferred flags: `fix_file_extensions`, `warn_before_executing`
      (no execution point today), `extract_video_tracks` (niche, needs ffmpeg).

## Done
- Phase 1 — empirical `handlers.json` + `build_handlers.py` + `detection_blacklist.json`.
- Phase 2 — detector pipeline refactor + puremagic demotion (`detection_filter`).
- Phase 3 — `extract`/`identify`/`list` subcommands (bare path -> extract).
- Phase 4 — `check_free_space` (+ Windows disk fix), `open_output_folder`,
  `create_log_files`, `check_unicode`.
- Phase 5 — `carve` subcommand (binwalk offsets -> carve -> extract).
- Phase 6 — bitrock/cicdec/dgca/wix handlers (dgca/cicdec CLIs verified).
- Phase 7 — recursive extraction (`-r`/`--max-depth`).
