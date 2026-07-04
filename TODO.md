# TODO — format gaps

Modern formats not yet covered (mainstream compression + today's installers are done).

- [ ] **MSIX / APPX** — modern Windows app packages. ZIP-based, so 7z likely already
      opens them; verify with a `.msix`/`.appx` sample. Probably zero code.
- [ ] **Asar** — Electron desktop app packaging (very common today). Needs `asar` (node) or a small unpacker.
- [ ] **Install4j** — Java installer, still current. Needs its extractor tool.
- [ ] **Squirrel** — Electron/Windows installer; usually NSIS or nupkg(zip), so partially covered via 7z. Verify.
