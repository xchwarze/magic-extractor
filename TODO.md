# TODO

Pending work for magic-extractor. Full design in
`docs/superpowers/specs/2026-07-04-universal-extractor-roadmap-design.md`.

## Handlers status (20 registered)
Complete (handler + binary + sample + detection):
7z, rar, ace, alzip, arc, egg, bcm (v1+v2), kgb, pea, uharc, zpaq, inno, msi,
plus 7z-routed cab/iso/rpm/xar/deb/ar/xz/lzma/zstd/zip/cpio/bz2, dgca, lzip,
cicdec (cic), pyinstaller.

Registered, need a real sample to map/verify:
- [ ] bitrock  — binary present, needs a BitRock installer sample.
- [ ] wix      — binary present; verify `dark.exe -?` and add an MSI/wixout sample.
- [ ] installshield — unshield present (+ deobfuscate); needs a real `.cab` sample.

Dropped: Wise (discontinued legacy, ~70MB extractor).

## Open decisions
- [ ] NSIS SFX `.exe`: not extracted because 7z is kept out of the PE fallback
      (7z opens any PE, short-circuiting). Option A: add 7z last in the fallback
      (unknown exes then dump PE sections). Option B (recommended): leave as is.

## Remaining phases / features
- [ ] Phase 8 — build on Windows: `pyinstaller magic-extractor.spec`, then copy
      `src/bin`, `src/data`, `src/config.ini` into `dist/magic-extractor/`.
- [ ] Phase 4 deferred flags: `fix_file_extensions`, `warn_before_executing`,
      `extract_video_tracks` (niche).
- [ ] Optional: Install4j installer (Java; needs its tool).

## Testing
- `python tools/build_handlers.py --live` (Windows): map detections from samples.
- `python test/run_extract_all.py` (Windows): end-to-end extraction smoke test.
- Known e2e edge fails: exotic-format SFX `.exe` (ace/arc/kgb/uharc self-extractors)
  when their tool cannot read its own SFX; `.nsi`/`.iss` are source scripts (skipped).
