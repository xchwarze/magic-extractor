# Third-Party Notices

magic-extractor's own source is MIT (see `LICENSE.txt`). It does **not**
reimplement the archive formats — it detects a file and shells out to bundled
third-party detector/extractor programs under `cli/bin/`. Each of those keeps
its own license, listed below. **They are not covered by magic-extractor's MIT
license.**

> This file is informational, not legal advice, and licenses/versions can
> change. Before redistributing the bundle, verify each tool's current terms
> against its own `LICENSE`/`readme` in its `cli/bin/` folder.

## ⚠ Restrictive — verify before redistributing

These are proprietary / shareware / non-commercial and may **not** be freely
bundled in a distributed product. Confirm terms (or drop them / require the user
to supply them):

| Tool | Used for | Terms |
|------|----------|-------|
| `alzip/ALZipCon.exe` (ESTsoft) | ALZ, EGG | **Shareware.** Free for individuals; companies/for-profit/public orgs/Internet cafes must buy a license. Bundling in a product is a concern. |
| `rar/UnRAR` (RARLAB) | RAR | UnRAR EULA: freely distributable, but must **not** be used to recreate the RAR compression algorithm / build a RAR-compatible archiver. |
| `uharc` | UHARC | Freeware, typically **non-commercial** use only. |
| `unace` | ACE | Proprietary freeware; redistribution terms unclear. |
| `dgca` | DGCA | Japanese freeware, proprietary. |

## 7-Zip plugins (tc4shell / Dec Software)

Optional plugins in `extractors/7z/Formats/` and `extractors/7z/Codecs/` that let
7-Zip open extra formats. Freeware from tc4shell (© Dec Software); each ships its
own `*-ReadMe.txt`.

| Plugin | Adds |
|--------|------|
| `Formats/Asar` | Electron .asar |
| `Formats/Forensic7z` | EWF (E01/S01/Ex01/L01/Lx01), AD1, AFF, WHX |
| `Formats/Iso7z` | disc images (CISO/CSO, CHD, ECM, ISZ, MDS, CCD, zisofs, NRG, …) |
| `Formats/ExFat7z` | ExFAT images |
| `Formats/eDecoder` | mail/encoding (TNEF, DBX, WARC, BinHex, yEnc, TBB, MacBinary, …) |
| `Formats/Py7z` | PyInstaller executables |
| `Formats/Grit7z` | Chromium resource pak (.pak) |
| `Codecs/Modern7z` | Zstd, Brotli, LZ4, LZ5, Lizard, Fast-LZMA2 |

## Permissive / open (low risk)

| Tool | Role | License |
|------|------|---------|
| `detectors/binwalk` | detector | MIT |
| `detectors/die` (Detect It Easy) | detector | MIT |
| `detectors/magika` (Google) | detector | Apache-2.0 |
| `extractors/7z` (7-Zip) | many formats | LGPL-2.1+ (with an unRAR-code restriction) |
| `extractors/cicdec` | Clickteam | BSD-3-Clause |
| `extractors/lessmsi` | MSI | MIT |
| `extractors/unshield` | InstallShield | MIT (© 2003 David Eriksson) |
| `extractors/peazip` | PEA | LGPL |
| `extractors/unarc` (FreeArc) | ARC | FreeArc license (GPL-based) |
| `extractors/kgb` | KGB | GPL |
| `extractors/plzip` | lzip | GPL |
| `extractors/zpaq` (Matt Mahoney) | ZPAQ | Public domain |
| `extractors/bcm` (Ilya Muravyov) | BCM | Public domain |
| `extractors/innounp` | Inno Setup | Free (Inno-derived) — see tool |
| `extractors/bitrock-unpacker` | BitRock | Open (see tool) — verify |
| `extractors/unalz` | ALZ (open) | BSD-style — verify |
| `extractors/wix` (dark.exe) | WiX MSI | MS-RL (WiX 3) / MIT (WiX 4) — verify |

Licenses tagged **verify** were inferred (no bundled LICENSE file); confirm from
the upstream project before relying on them.

## GPL/LGPL note

Several tools are GPL/LGPL. magic-extractor only **executes** them as separate
programs (subprocess), which is aggregation, not linking — so magic-extractor's
own MIT license is unaffected. But redistributing the GPL binaries still
requires offering their corresponding source (or a written offer), per GPL.
