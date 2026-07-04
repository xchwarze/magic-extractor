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
