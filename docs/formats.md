# Supported Formats

**80+ formats** grouped by family, with the handler that extracts each. Most
mainstream compression and disk-image formats are handled by `Format7zHandler`
(7-Zip); plugin-dependent 7-Zip formats (marked †) use `Format7zExtHandler`; and
dedicated handlers cover the rest. `Format7zZsHandler` (7-Zip ZS) is a fallback
tried after 7-Zip for several formats (see
[7-Zip ZS fallback](#7-zip-zs-fallback)).

## Compressed Archives

| Format                | Extension(s)                     | Handler             |
|-----------------------|----------------------------------|---------------------|
| 7-Zip                 | .7z, .exe (SFX)                  | Format7zHandler     |
| ZIP                   | .zip, .jar                       | Format7zHandler     |
| XZ                    | .xz                              | Format7zHandler     |
| bzip2                 | .bz2, .tbz2                      | Format7zHandler     |
| gzip                  | .gz, .tgz                        | Format7zHandler     |
| tar                   | .tar                             | Format7zHandler     |
| Zstandard             | .zst                             | Format7zHandler     |
| LZMA                  | .lzma                            | Format7zHandler     |
| lzip                  | .lz                              | FormatLzipHandler   |
| ARJ                   | .arj                             | Format7zHandler     |
| LHA/LZH               | .lzh, .lha                       | Format7zHandler     |
| cpio                  | .cpio                            | Format7zHandler     |
| ar / Unix archive     | .a, .ar                          | Format7zHandler     |
| Debian package        | .deb                             | Format7zHandler     |
| RPM package           | .rpm                             | Format7zHandler     |
| XAR                   | .xar                             | Format7zHandler     |
| RAR                   | .rar, .exe (SFX)                 | FormatRarHandler    |
| ACE                   | .ace, .exe (SFX)                 | FormatAceHandler    |
| AlZip                 | .alz                             | FormatAlzipHandler  |
| EGG                   | .egg                             | FormatEggHandler    |
| KGB                   | .kgb, .exe (SFX)                 | FormatKgbHandler    |
| UHARC                 | .uha, .exe (SFX)                 | FormatUharcHandler  |
| ZPAQ                  | .zpaq                            | FormatZpaqHandler   |
| FreeArc               | .arc, .exe (SFX)                 | FormatArcHandler    |
| BCM (v1 + v2)         | .bcm                             | FormatBcmHandler    |
| PeaZip                | .pea                             | FormatPeaHandler    |
| DGCA                  | .dgc                             | FormatDgcaHandler   |

## Installers

| Installer                       | Extension(s) | Handler                    |
|---------------------------------|--------------|----------------------------|
| Windows Installer (MSI)         | .msi         | FormatMsiHandler (lessmsi → 7z) |
| WiX Toolset (MSI)               | .msi         | FormatWixHandler (dark)    |
| Inno Setup                      | .exe         | FormatInnoSetupHandler     |
| Nullsoft Scriptable Install (NSIS) | .exe      | Format7zHandler            |
| InstallShield                   | .cab         | FormatInstallShieldHandler |
| BitRock / InstallBuilder        | .exe         | FormatBitrockHandler       |
| Clickteam Install Creator       | .exe         | FormatCicdecHandler        |
| PyInstaller                     | .exe         | Format7zExtHandler †          |

## Disk Images

| Image type                    | Extension(s)   | Handler         |
|-------------------------------|----------------|-----------------|
| Microsoft WIM                 | .wim           | Format7zHandler |
| Apple Disk Image              | .dmg           | Format7zHandler |
| ISO 9660                      | .iso           | Format7zHandler |
| UDF                           | .udf           | Format7zHandler |
| QEMU                          | .qcow2         | Format7zHandler |
| VirtualBox                    | .vdi           | Format7zHandler |
| Virtual Hard Disk             | .vhd, .vhdx    | Format7zHandler |
| VMware                        | .vmdk          | Format7zHandler |
| APFS / ext / FAT / HFS / NTFS | .img           | Format7zHandler |
| cramfs / squashfs             | .cramfs, .sqsh | Format7zHandler |
| MBR / GPT partition table     | .img, .bin     | Format7zHandler |
| UEFI firmware volume          | .fd, .rom, .bin| Format7zHandler |
| ExFAT                         | .img           | Format7zExtHandler † |

> Intel HEX (`.hex`) is supported by the underlying 7-Zip but is a plain-text
> format with no reliable signature, so it is not auto-detected/routed.

## Forensic Images

Detected and routed to 7-Zip; extraction requires the **forensic7z** plugin in
the bundled 7-Zip's `Formats/` folder.

| Format                                | Extension(s)   | Handler              |
|---------------------------------------|----------------|----------------------|
| EnCase / ASR SMART (EWF)              | .E01, .S01     | Format7zExtHandler † |
| EnCase v7 (EWF2)                      | .Ex01          | Format7zExtHandler † |
| EnCase Logical                        | .L01           | Format7zExtHandler † |
| EnCase v7 Logical                     | .Lx01          | Format7zExtHandler † |
| AccessData FTK Imager Logical         | .AD1           | Format7zExtHandler † |
| Advanced Forensics Format             | .AFF           | Format7zExtHandler † |
| WinHex evidence                       | .whx           | Format7zExtHandler † |

## Disc Images (Iso7z plugin)

Detected and routed to 7-Zip; extraction requires the **Iso7z** plugin.

| Format                                | Extension(s)   | Handler           |
|---------------------------------------|----------------|-------------------|
| Compact / Compressed ISO              | .ciso, .cso    | Format7zExtHandler † |
| MAME CHD                              | .chd           | Format7zExtHandler † |
| ECM                                   | .ecm           | Format7zExtHandler † |
| UltraISO ISZ                          | .isz           | Format7zExtHandler † |
| Alcohol 120% descriptor               | .mds           | Format7zExtHandler † |
| CloneCD control                       | .ccd           | Format7zExtHandler † |
| zisofs                                | —              | Format7zExtHandler † |

> Also Iso7z targets but not auto-detected (no reliable start-of-file magic):
> NRG (Nero), CDI (DiscJuggler), GDI (Dreamcast), CUE/BIN. Their data files are
> raw/text; add them manually if needed.

## Mail / Encoding (eDecoder plugin)

Detected and routed to 7-Zip; extraction requires the **eDecoder** plugin.

| Format                                | Extension(s)   | Handler           |
|---------------------------------------|----------------|-------------------|
| TNEF (Outlook winmail.dat)            | .dat           | Format7zExtHandler † |
| Outlook Express mail store            | .dbx           | Format7zExtHandler † |
| Web ARChive                           | .warc          | Format7zExtHandler † |
| BinHex                                | .hqx           | Format7zExtHandler † |
| yEnc                                  | .ntx           | Format7zExtHandler † |
| The Bat! message base                 | .tbb           | Format7zExtHandler † |
| MacBinary III                         | .bin           | Format7zExtHandler † |

> Other eDecoder targets are plain text with no reliable signature, so they are
> not auto-detected: MBOX, EML/NWS/MHT/MHTML/B64, EMLX, UUE/XXE, MGS, MBX, PMM,
> and MacBinary I/II (only v3 has a magic). The plugin can still extract them if
> reached.

## Modern Compression (Modern7z plugin)

Detected and routed to 7-Zip; extraction requires the **Modern7z** plugin in the
bundled 7-Zip's `Codecs/` folder.

| Format                                | Extension(s)   | Handler              |
|---------------------------------------|----------------|----------------------|
| LZ4 frame                             | .lz4           | Format7zExtHandler † |
| LZ5 frame                             | .lz5           | Format7zExtHandler † |
| Lizard frame                          | .liz           | Format7zExtHandler † |
| Firefox jsonlz4                        | .jsonlz4, .mozlz4 | Format7zExtHandler † |

> Modern7z also adds Brotli, Fast-LZMA2 and Zstd/Brotli-in-Zip, but those are raw
> streams with no reliable magic, so they are not auto-detected. Plain Zstd
> (`.zst`) is already handled natively.

## Other

| Format                        | Extension(s) | Handler          |
|-------------------------------|--------------|------------------|
| Microsoft Compiled HTML Help  | .chm         | Format7zHandler  |
| Z (compress)                  | .Z           | Format7zHandler  |
| Electron Asar                 | .asar        | Format7zExtHandler † |
| Chromium resource pak (v5)    | .pak         | Format7zExtHandler † |

> **† Needs a 7-Zip plugin.** These formats are detected and routed to 7-Zip,
> but 7-Zip only extracts them when the matching plugin is present in the bundled
> 7-Zip's `Formats/` (or `Codecs/`) folder. Without the plugin the file is
> identified but extraction fails. Plugin per format:
>
> | Plugin       | Covers                                                    |
> |--------------|-----------------------------------------------------------|
> | **Asar**     | Electron `.asar`                                          |
> | **forensic7z** | EWF (E01/S01/Ex01/L01/Lx01), FTK AD1, AFF (forensic images) |
> | **Iso7z**    | disc images (CISO/CSO, CHD, ECM, ISZ, MDS, CCD, zisofs)   |
> | **ExFat7z**  | ExFAT disk images                                        |
> | **eDecoder** | mail/encoding (TNEF, DBX, WARC, BinHex, yEnc)             |
> | **Modern7z** | LZ4/LZ5/Lizard, Firefox jsonlz4/mozlz4 (Codecs/ folder)  |
> | **Py7z**     | PyInstaller executables                                   |
> | **Grit7z**   | Chromium resource pak (.pak v5)                          |

## 7-Zip ZS fallback

`Format7zZsHandler` runs [7-Zip ZS](https://github.com/mcmilk/7-Zip-zstd)
(`7zzstd/7z.exe`), a 7-Zip build with Zstandard, Brotli, LZ4, LZ5, Lizard and
Fast-LZMA2 inside the format handlers themselves. It claims the same detection
keys as the handlers below; candidates sharing a key are tried in registry order
(`_HANDLER_CLASSES`), each only if the previous one failed:

| Format                    | Order                                     | What ZS adds                          |
|---------------------------|-------------------------------------------|---------------------------------------|
| SquashFS                  | Format7zHandler → Format7zZsHandler       | LZ4-compressed images (mainline: "Not implemented") |
| NSIS                      | Format7zHandler → Format7zZsHandler       | ZSTD-compressed installers            |
| 7-Zip, ZIP, XZ, Zstandard | Format7zHandler → Format7zZsHandler       | second opinion with the ZS codecs     |
| LZ4 / LZ5 / Lizard frame  | Format7zExtHandler † → Format7zZsHandler  | works without the Modern7z plugin     |
| lzip                      | Format7zZsHandler → FormatLzipHandler     | native lzip; plzip as second opinion  |

Brotli (`.br`) has no magic bytes, so it cannot be routed by detection.

## Notes
- Self-extracting `.exe` archives (7-Zip, RAR, Inno) are detected and routed to
  their handler; other SFX and wrapped-exe installers (ACE, FreeArc, KGB, UHARC,
  BitRock, Clickteam) are tried via the PE fallback, where each handler rejects
  files that are not its own.
- The detection → handler routing is data-driven (`data/handlers.json`).
- `carve` mode uses binwalk to extract archives embedded at arbitrary offsets
  (e.g. inside firmware images).

## Tools

Each handler shells out to a bundled helper binary under `src/cli/bin/extractors/`;
the content detectors DIE, binwalk and Magika live under `src/cli/bin/detectors/`
(`puremagic` is a pip dependency, not a bundled binary). Tool paths are relative
to those directories.

| Handler | Tool | URL |
|---------|------|-----|
| Format7zHandler | `7z/7z.exe` | http://www.7-zip.org/ |
| Format7zZsHandler | `7zzstd/7z.exe` (7-Zip ZS, fallback) | https://github.com/mcmilk/7-Zip-zstd |
| Format7zExtHandler | `7z/7z.exe` + plugins in `7z/Formats/` (Asar, forensic7z, Iso7z, ExFat7z, eDecoder, Py7z, Grit7z) and `7z/Codecs/` (Modern7z) | https://www.tc4shell.com/en/7zip/ |
| FormatRarHandler | `rar/unrar.exe` | http://www.rarlab.com/rar_add.htm |
| FormatAceHandler | `unace/unace.exe` | https://sourceforge.net/projects/peazip/files/Resources/PeaZip%20UNACE%20Plugin/ |
| FormatAlzipHandler | `alzip/ALZipCon.exe` | https://www.altools.com/ |
| FormatEggHandler | `alzip/ALZipCon.exe` | https://www.altools.com/ |
| FormatKgbHandler | `kgb/kgb2_console.exe` | http://kgbarchiver.sourceforge.net/ |
| FormatUharcHandler | `uharc/uharc-v0.6b.exe` | http://en.wikipedia.org/wiki/UHarc |
| FormatZpaqHandler | `zpaq/zpaq.exe` | http://mattmahoney.net/dc/zpaq.html |
| FormatArcHandler | `unarc/unarc.exe` | http://freearc.org/ |
| FormatBcmHandler | `bcm/bcm-v203x64.exe`, `bcm/bcm-v160x32.exe` | https://github.com/encode84/bcm |
| FormatPeaHandler | `peazip/pea.exe` | https://www.peazip.org/ |
| FormatDgcaHandler | `dgca/dgcac.exe` | http://www.emit.jp/dgca/ |
| FormatLzipHandler | `plzip/plzip.exe` | https://encode.su/threads/570-plzip-a-massively-parallel-compressor-based-on-LZMA |
| FormatMsiHandler | `lessmsi/lessmsi.exe` (+ `7z/7z.exe` fallback) | https://github.com/activescott/lessmsi |
| FormatWixHandler | `wix/dark.exe` | http://wixtoolset.org/ |
| FormatInnoSetupHandler | `innounp/innounp.exe` | http://innounp.sourceforge.net/ |
| FormatInstallShieldHandler | `unshield/unshield.exe` | https://github.com/ScoopInstaller/Main/blob/master/bucket/unshield.json |
| FormatBitrockHandler | `bitrock-unpacker/bitrock-unpacker.exe` | https://gist.github.com/mickael9/0b902da7c13207d1b86e |
| FormatCicdecHandler | `cicdec/cicdec.exe` | https://github.com/Bioruebe/cicdec |
| DIE (detector) | `detectors/die/diec.exe` | https://github.com/horsicq/Detect-It-Easy |
| Magika (detector) | `detectors/magika/magika.exe` | https://github.com/google/magika |
| binwalk (detector) | `detectors/binwalk/binwalk.exe` | https://github.com/ReFirmLabs/binwalk |
| puremagic (detector) | `puremagic` (pip package) | https://github.com/cdgriffith/puremagic |
