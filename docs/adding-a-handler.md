# Adding a format handler

How to add support for a new archive/installer/image format, end to end. Written
from the patterns the codebase already uses — follow them and detection +
extraction "just work".

## How detection & routing works

1. **Detectors** run over the file (in `cli/file_type.py`), cheapest first:
   `puremagic` (MIME) → built-in signatures (`data/signatures.json`) → DIE →
   binwalk → Magika. Each emits MIME types and/or detection-name strings.
2. **Filtering** (`cli/detection_filter.py`) drops generic noise via
   `data/detection_blacklist.json` (e.g. `application/octet-stream`, `pe`).
3. **Routing** (`cli/formats/__init__.py`): a MIME or detection string is looked
   up (lowercased) in `data/handlers.json` (`mime_handlers` / `detection_handlers`)
   to find the handler class. First detector with a mapped handler wins
   (early-exit; `--bruteforce` tries all).
4. **The handler** shells out to a bundled tool and extracts.

Key point: **`handlers.json` and `signatures.json` are generated**, not
hand-edited. They are built from each handler's `detection_*` class methods by
`tools/generate_data.py`. You declare detection *in the handler*, then regenerate.

## 1. Write the handler class

Create `cli/formats/format_<name>.py`, subclassing `BaseExtractor`:

```python
import os, subprocess, logging
from .base_extractor import BaseExtractor

class FormatFooHandler(BaseExtractor):
    """Handler for FOO archives (uses foo/foo.exe)."""

    @classmethod
    def detection_mimes(cls):
        return ['application/x-foo']          # MIME types (puremagic / Magika)

    @classmethod
    def detection_names(cls):
        return ['foo archive']                 # DIE / binwalk / Magika strings (lowercased)

    @classmethod
    def detection_signatures(cls):
        # Custom magic bytes for what the engines miss. name is auto-added to
        # detection_names. patterns = list of {pos, hex} = AND; repeat the entry
        # with the same name for OR.
        return [{'name': 'foo archive', 'patterns': [{'pos': 0, 'hex': '464f4f00'}]}]  # 'FOO\0'

    def extract(self):
        cmd = [os.path.join(self.extractors_path, 'foo', 'foo.exe'),
               'x', self.target_file, self.extract_directory]
        try:
            self.run_command(cmd)          # raises on non-zero; logs tool stderr at ERROR
            return True
        except subprocess.CalledProcessError:
            return False

    # optional: def list_contents(self): return "<listing>" or None
```

- `self.target_file`, `self.extract_directory`, `self.extractors_path`
  (= `cli/bin/extractors/`), `self.cli_args.password` are provided by the base.
- Any of the three `detection_*` methods may be omitted (base returns `[]`).

## 2. Which detection method? (mime vs name vs signature)

A file reaches your handler when ANY detector's output matches something your
handler declares. You have three levers — use whichever the format actually
gives you (often more than one, for redundancy):

| Method | Declares | Fill it when… | Source of truth |
|--------|----------|---------------|-----------------|
| `detection_mimes` | MIME strings | puremagic or Magika already recognizes the format and emits a real MIME (e.g. `application/x-rar`). Cheapest path — no magic needed. | run `identify` and read the `[puremagic] MIME` / `[Magika] MIME` lines |
| `detection_names` | detector name strings | DIE / binwalk / Magika name the format but there's no clean MIME (installers, SFX, packers, exotic archivers) | DIE signature DB + `identify --debug` |
| `detection_signatures` | your own magic bytes | nothing above catches it, but the file has a reliable fixed-offset magic (most niche/older formats). This is the fallback that makes detection self-contained. | TrID defs + the format spec |

So: **mime = "an engine already knows it"; name = "an engine names it but no
MIME"; signature = "I teach it the magic myself."** All three are lowercased and
compared case-insensitively.

### Finding the DIE name

DIE's real output string lives in its signature DB as `meta("<type>", "<name>")`.
Grep for your format:

```bash
grep -rl -i "yourformat" cli/bin/detectors/die/db/
grep -rhoE 'meta\("[^"]*", ?"[^"]*"\)' cli/bin/detectors/die/db/**/*yourformat*.sg
```

Use the lowercased `<name>` in `detection_names`.

- **Gotcha:** `file_type.determine_file_type_with_die` only keeps values whose
  `type` ∈ `{sfx, archive, installer, packer}`. If DIE tags your format as
  anything else (Library, Format, Partition, tool…) its name is **dropped** — so
  either add a magic signature, or widen `relevant_types` in `file_type.py`.

### Finding the magic in TrID

TrID has ~21k defs, one XML per format under `triddefs_xml/defs/<letter>/`, with
`<Pattern><Bytes>HEX</Bytes><Pos>N</Pos></Pattern>` (`<Pos>` = decimal offset,
`<Bytes>` = uppercase hex). It's the most reliable magic source — it caught a
wrong EnCase Lx01 magic here. Search by extension/name and read the pattern:

```bash
ls triddefs_xml/defs/*/ | grep -i yourext
grep -oE '<Bytes>[0-9A-Fa-f]+</Bytes>|<Pos>[0-9]+</Pos>|<Ext>[^<]+</Ext>' \
    triddefs_xml/defs/y/yourformat.trid.xml
```

Convert bytes to lowercase for the handler. Reject weak patterns (1–2 bytes,
all-zero, or a generic value like `04000000` alone — anchor it with a second
`{pos,hex}`).

### binwalk / Magika

Short keys / labels — the surest way is to run the CLI on a real sample and read
what each detector prints:

```bash
python cli/main.py identify --debug path/to/sample.foo
```
Copy the exact `[binwalk] detect` / `[Magika] detect|MIME` strings into
`detection_names` / `detection_mimes`.

### Writing reliable magic signatures

- Prefer a distinctive multi-byte constant at a fixed offset.
- A generic lead (e.g. `04000000`) needs a second anchor: use AND
  (two `{pos,hex}` in one `patterns` group), like asar =
  `04000000`@0 **and** `{"files"`@16. Avoid short/common magics (a 2-byte or
  all-zero pattern will false-positive).
- Multiple alternative magics for one format = repeat the entry with the same
  `name` (they become OR groups).

## 3. Register + regenerate

- Add the class to `cli/formats/__init__.py`: import it and append to
  `_HANDLER_CLASSES`.
- Regenerate the data files:
  ```
  python tools/generate_data.py
  ```
  This rewrites `cli/data/handlers.json` + `cli/data/signatures.json` from all
  handlers. Commit those alongside the handler.

## 4. Bundle the extractor tool

- Put the tool under `cli/bin/extractors/<tool>/` (matches the path your
  `extract()` builds). It ships beside the exe in the release zip.
- **Windows runtime gotcha:** old tools may need a VC++ runtime via a
  side-by-side manifest (error `WinError 14001`). Ship the runtime **app-local**:
  a `Microsoft.VCxx.CRT/` folder (or loose files + `.manifest`) beside the tool,
  matching the exact assembly identity the exe requests. See the `alzip/` layout.
- Add the tool + its license to `THIRD-PARTY-NOTICES.md` and the Tools table in
  `formats.md`.

### 7-Zip plugin formats

If the format is handled by a 7-Zip plugin (tc4shell etc.) rather than a
standalone tool, don't write a new handler — add the detection to
`Format7zExtHandler` (`cli/formats/format_7z_ext.py`), which inherits 7-Zip's
`extract()`. Drop the plugin DLL in `cli/bin/extractors/7z/Formats/` (or
`Codecs/`). Native 7-Zip formats go in `Format7zHandler` instead.

### PE installers

Wrapped-exe installers can't be told apart by content. Add the class name to
`PE_INSTALLER_FALLBACK` in `cli/main.py` — it's tried on any `MZ` file; the tool
self-validates and fails cleanly on a mismatch. (7-Zip is deliberately excluded.)

## 5. Test

- Drop a real sample at `test/samples/<fmt>/test-file.<ext>` — the battery walks
  every file under `test/samples/` automatically, no registration needed.
- Run it:
  ```
  python test/run_battery.py            # unit tests + extraction battery (Windows)
  python test/run_battery.py --unit-only   # pure-python, runs anywhere
  ```
- Add pure-logic unit tests under `test/cli/` (see `test_formats_registry.py`).

## 6. Document

- Add a row to the right table in `formats.md` (format, extension(s), handler);
  mark plugin-dependent formats with `†`.
- Update `THIRD-PARTY-NOTICES.md` if you bundled a new tool.

## Checklist

- [ ] `cli/formats/format_<name>.py` with `extract()` + `detection_*`
- [ ] Detection strings verified against DIE db / TrID (not guessed)
- [ ] Registered in `cli/formats/__init__.py`
- [ ] `python tools/generate_data.py` run; `handlers.json`/`signatures.json` committed
- [ ] Tool bundled under `cli/bin/extractors/` (+ runtime if needed)
- [ ] Sample in `test/samples/<fmt>/`; battery green
- [ ] `formats.md` + `THIRD-PARTY-NOTICES.md` updated
