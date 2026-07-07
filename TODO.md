# TODO — format gaps

Modern formats not yet covered (mainstream compression + today's installers are done).

- [ ] **MSIX / APPX** — modern Windows app packages. ZIP-based, so 7z likely already
      opens them; verify with a `.msix`/`.appx` sample. Probably zero code.
- [ ] **Install4j** — Java installer, still current. Needs its extractor tool.

Done: Asar (Electron) — detected (magic + DIE) and extracted via the Asar 7z plugin.
Skipped: Squirrel — not widely used and already covered via NSIS / nupkg (zip).
