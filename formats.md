# Supported Formats

Formats grouped by family, with the handler that extracts each. Most mainstream
compression and disk-image formats are handled by `Format7zHandler` (7-Zip);
dedicated handlers cover the rest.

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
| ACE                   | .ace                             | FormatAceHandler    |
| AlZip                 | .alz                             | FormatAlzipHandler  |
| EGG                   | .egg                             | FormatEggHandler    |
| KGB                   | .kgb                             | FormatKgbHandler    |
| UHARC                 | .uha                             | FormatUharcHandler  |
| ZPAQ                  | .zpaq                            | FormatZpaqHandler   |
| FreeArc               | .arc                             | FormatArcHandler    |
| BCM (v1 + v2)         | .bcm                             | FormatBcmHandler    |
| PeaZip                | .pea                             | FormatPeaHandler    |
| DGCA                  | .dgc                             | FormatDgcaHandler   |

## Installers

| Installer                       | Extension(s) | Handler                    |
|---------------------------------|--------------|----------------------------|
| Windows Installer (MSI)         | .msi         | FormatMsiHandler (lessmsi → 7z) |
| WiX / wixout                    | .msi, .wixout| FormatWixHandler (dark)    |
| Inno Setup                      | .exe         | FormatInnoSetupHandler     |
| Nullsoft Scriptable Install (NSIS) | .exe      | Format7zHandler            |
| InstallShield                   | .cab         | FormatInstallShieldHandler |
| BitRock / InstallBuilder        | .exe         | FormatBitrockHandler       |
| Clickteam Install Creator       | .exe         | FormatCicdecHandler        |
| PyInstaller                     | .exe         | FormatPyInstallerHandler   |

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
| APFS / ext / FAT / HFS        | .img           | Format7zHandler |
| cramfs / squashfs             | .cramfs, .sqsh | Format7zHandler |

## Other

| Format                        | Extension(s) | Handler         |
|-------------------------------|--------------|-----------------|
| Microsoft Compiled HTML Help  | .chm         | Format7zHandler |
| Z (compress)                  | .Z           | Format7zHandler |

## Notes
- Self-extracting `.exe` archives (7-Zip, RAR, Inno) are detected and routed to
  their handler; other wrapped-exe installers are tried via the PE fallback.
- The detection → handler routing is data-driven (`data/handlers.json`).
- `carve` mode uses binwalk to extract archives embedded at arbitrary offsets
  (e.g. inside firmware images).

## Tools

Each handler shells out to a bundled helper binary under `src/bin/extractors/`;
the four content detectors live under `src/bin/detectors/` (except `puremagic`,
which is a pip dependency). Tool paths are relative to those directories.

| Handler | Tool | URL |
|---------|------|-----|
| Format7zHandler | `7z/7z.exe` | http://www.7-zip.org/ |
| FormatRarHandler | `rar/unrar.exe` | http://www.rarlab.com/rar_add.htm |
| FormatAceHandler | `unace/unace.exe` | https://sourceforge.net/projects/peazip/files/Resources/PeaZip%20UNACE%20Plugin/ |
| FormatAlzipHandler | `alzip/ALZipCon.exe` | https://www.altools.com/ |
| FormatEggHandler | `alzip/ALZipCon.exe` | https://www.altools.com/ |
| FormatKgbHandler | `kgb/kgb2_console.exe` | http://kgbarchiver.sourceforge.net/ |
| FormatUharcHandler | `uharc/uharc-v0.6b.exe` | http://en.wikipedia.org/wiki/UHarc |
| FormatZpaqHandler | `zpaq/zpaq.exe` | http://mattmahoney.net/dc/zpaq.html |
| FormatArcHandler | `unarc/unarc.exe` | http://freearc.org/ |
| FormatBcmHandler | `bcm/bcm-v203x64.exe` | https://github.com/encode84/bcm |
| FormatPeaHandler | `peazip/pea.exe` | https://www.peazip.org/ |
| FormatDgcaHandler | `dgca/dgcac.exe` | http://www.emit.jp/dgca/ |
| FormatLzipHandler | `plzip/plzip.exe` | https://encode.su/threads/570-plzip-a-massively-parallel-compressor-based-on-LZMA |
| FormatMsiHandler | `lessmsi/lessmsi.exe` (+ `7z/7z.exe` fallback) | https://github.com/activescott/lessmsi |
| FormatWixHandler | `wix/dark.exe` | http://wixtoolset.org/ |
| FormatInnoSetupHandler | `innounp/innounp.exe` | http://innounp.sourceforge.net/ |
| FormatInstallShieldHandler | `unshield/unshield.exe` | https://github.com/ScoopInstaller/Main/blob/master/bucket/unshield.json |
| FormatBitrockHandler | `bitrock-unpacker/bitrock-unpacker.exe` | https://gist.github.com/mickael9/0b902da7c13207d1b86e |
| FormatCicdecHandler | `cicdec/cicdec.exe` | https://github.com/Bioruebe/cicdec |
| FormatPyInstallerHandler | `pyinstxtractor-ng/pyinstxtractor-ng.exe` | https://github.com/pyinstxtractor/pyinstxtractor-ng |
| DIE (detector) | `detectors/die/diec.exe` | https://github.com/horsicq/Detect-It-Easy |
| Magika (detector) | `detectors/magika/magika.exe` | https://github.com/google/magika |
| binwalk (detector) | `detectors/binwalk/binwalk.exe` | https://github.com/ReFirmLabs/binwalk |
| puremagic (detector) | `puremagic` (pip package) | https://github.com/cdgriffith/puremagic |
