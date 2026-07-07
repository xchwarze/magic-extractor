Forensic7z

https://www.tc4shell.com/en/7zip/forensic7z/
Copyright (c) 2018-22 Dec Software.

Forensic7z is a plugin for the popular 7-Zip archiver. You can use Forensic7z to
open and browse disk images created by specialized software for forensic
analysis, such as Encase or FTK Imager.

At the moment, the Forensic7z plugin supports images in the following formats:

    ASR Expert Witness Compression Format (.S01)
    Encase Image File Format (.E01, .Ex01)
    Encase Logical Image File Format (.L01, .Lx01)
    Advanced Forensics Format (.AFF)
    AccessData FTK Imager Logical Image (.AD1)

Encrypted images are not currently supported.

INSTALLATION

To install the plugin into the 7-Zip installation folder, you need to create the
"Formats" subfolder. After that, copy Forensic.64.dll or Forensic.32.dll
(depending on your 7-Zip edition) to that subfolder. If you do that, each time
you launch 7-Zip, it will automatically find Forensic7z and use it when opening
forensic disc images files.

USAGE

When opening a multi-volume disk image, we recommend opening the first volume
first to enable Forensic7z to correctly find and process the rest of the
volumes.

If the image you are opening is a physical disk image, 7-Zip will show a single
file inside – an uncompressed RAW disk image without metadata.

If the file is a disk image with a supported file system (FAT, NTFS, exFAT and
several others), you will be able to open this file as an enclosed archive right
in 7-Zip (this operation does not require the file to be extracted), view and
extract its contents:

If the image file you are opening is a logical evidence file, opening it in
7-Zip will give you a complete list of all files in this image:

The Properties command provides access to various metadata included in the disk
image: Evidence number, Case number, Examiner name, etc.
