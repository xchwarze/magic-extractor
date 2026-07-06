import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class Format7zHandler(BaseExtractor):
    """
    Handler class for .7z files that utilizes 7z for extraction.
    """

    @classmethod
    def detection_mimes(cls):
        # 7-Zip is the workhorse: it opens most mainstream archive / disk-image MIMEs.
        return [
            'application/x-7z-compressed', 'application/x-xz', 'application/x-bzip2',
            'application/gzip', 'application/x-gzip', 'application/x-tar', 'application/x-gtar',
            'application/zip', 'application/x-ms-wim', 'application/x-apfs-image',
            'application/x-archive', 'application/x-arj', 'application/vnd.ms-cab-compressed',
            'application/vnd.ms-htmlhelp', 'application/x-cpio', 'application/x-cramfs',
            'application/x-apple-diskimage', 'application/x-extfs-image', 'application/x-fatfs-image',
            'application/x-hfs', 'application/x-iso9660-image', 'application/x-lzh-compressed',
            'application/x-lzma', 'application/x-qemu-disk', 'application/x-rpm',
            'application/x-squashfs', 'application/x-udf', 'application/x-virtualbox-vdi',
            'application/x-vhd', 'application/x-vhdx', 'application/x-vmdk', 'application/x-xar',
            'application/x-compress', 'application/zstd', 'application/vnd.squashfs',
            'application/vnd.debian.binary-package', 'application/x-zstd-compressed-tar',
            'application/arj', 'application/x-lha',  # exact MIMEs puremagic emits
        ]

    @classmethod
    def detection_names(cls):
        return [
            # binwalk short keys
            '7zip', 'xz', 'bzip2', 'gzip', 'tar', 'apfs', 'cab', 'chm', 'cpio', 'cramfs',
            'dmg', 'ext', 'fat', 'efigpt', 'iso9660', 'lzma', 'mbr', 'ntfs', 'squashfs',
            'zip', 'zlib', 'zstd', 'compressd',
            # Magika labels
            'sevenzip', 'gzipped data',
            # DIE names
            '7-zip', 'gzip (.gz)', 'nullsoft scriptable install system',
            'microsoft cabinet file', 'ar archive', 'debian linux package', 'rpm package',
            'xar', 'bzip2 compressed archive', 'cpio archive (binary)',
            'debian software package (.deb)', 'zstandard compressed data',
            'asar archive (electron)', 'pyinstaller',
        ]

    @classmethod
    def detection_signatures(cls):
        return [
            # '7z\xbc\xaf\x27\x1c' at 0.
            {'name': '7-zip', 'patterns': [{'pos': 0, 'hex': '377abcaf271c'}]},
            # cpio magics (engines miss binary cpio): binary LE/BE + ASCII odc/newc/newc-crc.
            {'name': 'cpio', 'patterns': [{'pos': 0, 'hex': 'c771'}]},
            {'name': 'cpio', 'patterns': [{'pos': 0, 'hex': '71c7'}]},
            {'name': 'cpio', 'patterns': [{'pos': 0, 'hex': '303730373037'}]},
            {'name': 'cpio', 'patterns': [{'pos': 0, 'hex': '303730373031'}]},
            {'name': 'cpio', 'patterns': [{'pos': 0, 'hex': '303730373032'}]},
            # formats puremagic misses or reports as generic (octet-stream) / unrouted MIME
            {'name': 'arj', 'patterns': [{'pos': 0, 'hex': '60ea'}]},
            {'name': 'lzh', 'patterns': [{'pos': 2, 'hex': '2d6c68'}]},           # '-lh'
            {'name': 'chm', 'patterns': [{'pos': 0, 'hex': '49545346'}]},          # 'ITSF'
            {'name': 'qcow2', 'patterns': [{'pos': 0, 'hex': '514649fb'}]},        # 'QFI\xfb'
            {'name': 'vhdx', 'patterns': [{'pos': 0, 'hex': '7668647866696c65'}]}, # 'vhdxfile'
            {'name': 'vmdk', 'patterns': [{'pos': 0, 'hex': '4b444d56'}]},         # 'KDMV'
            {'name': 'vdi', 'patterns': [{'pos': 64, 'hex': '7f10dabe'}]},         # VDI image signature
            {'name': 'wim', 'patterns': [{'pos': 0, 'hex': '4d5357494d000000'}]},  # 'MSWIM\0\0\0'
            {'name': 'apfs', 'patterns': [{'pos': 32, 'hex': '4e585342'}]},        # 'NXSB' @0x20
            {'name': 'xar', 'patterns': [{'pos': 0, 'hex': '78617221'}]},          # 'xar!'
            {'name': 'uefi', 'patterns': [{'pos': 40, 'hex': '5f465648'}]},        # '_FVH' @0x28 (UEFI firmware volume)
            {'name': 'exfat', 'patterns': [{'pos': 3, 'hex': '4558464154202020'}]}, # 'EXFAT   ' @3 (needs ExFat7z plugin)
            {'name': 'ntfs', 'patterns': [{'pos': 3, 'hex': '4e544653'}]},         # 'NTFS' OEM id @3 (redundant w/ binwalk)
            {'name': 'efigpt', 'patterns': [{'pos': 512, 'hex': '4546492050415254'}]},  # 'EFI PART' @0x200 (GPT header)
            # Forensic disk images (extracted by 7-Zip with the forensic7z plugin).
            {'name': 'encase e01/s01', 'patterns': [{'pos': 0, 'hex': '455646090d0aff00'}]},  # 'EVF\x09\r\n\xff\x00' (EnCase E01 / ASR SMART S01)
            {'name': 'encase ex01', 'patterns': [{'pos': 0, 'hex': '455646320d0a8100'}]},     # 'EVF2\r\n\x81\x00'
            {'name': 'encase l01', 'patterns': [{'pos': 0, 'hex': '4c5646090d0aff00'}]},      # 'LVF\x09\r\n\xff\x00'
            {'name': 'encase lx01', 'patterns': [{'pos': 0, 'hex': '4c5646320d0a8100'}]},     # 'LVF2\r\n\x81\x00'
            {'name': 'ftk ad1', 'patterns': [{'pos': 0, 'hex': '41445345474d454e54454446494c4500'}]},  # 'ADSEGMENTEDFILE\x00'
            {'name': 'aff', 'patterns': [{'pos': 0, 'hex': '41464631300d0a00'}]},             # 'AFF10\r\n\x00' (AFFLIB)
            # Disc images (extracted by 7-Zip with the Iso7z plugin).
            {'name': 'ciso/cso', 'patterns': [{'pos': 0, 'hex': '4349534f'}]},                # 'CISO' (Compact/Compressed ISO)
            {'name': 'chd', 'patterns': [{'pos': 0, 'hex': '4d436f6d70724844'}]},             # 'MComprHD' (MAME CHD)
            {'name': 'ecm', 'patterns': [{'pos': 0, 'hex': '45434d00'}]},                     # 'ECM\x00'
            {'name': 'isz', 'patterns': [{'pos': 0, 'hex': '49735a21'}]},                     # 'IsZ!' (UltraISO)
            {'name': 'alcohol mds', 'patterns': [{'pos': 0, 'hex': '4d454449412044455343524950544f52'}]},  # 'MEDIA DESCRIPTOR'
            {'name': 'clonecd ccd', 'patterns': [{'pos': 0, 'hex': '5b436c6f6e6543445d'}]},   # '[CloneCD]'
            {'name': 'zisofs', 'patterns': [{'pos': 0, 'hex': '37e45396c9dbd607'}]},          # zisofs block magic
            # asar (Electron): pickle header 04 00 00 00 @0 AND JSON '{"files"' @16.
            # Both conditions (AND) keep the generic 04000000 from false-matching.
            {'name': 'asar archive (electron)', 'patterns': [
                {'pos': 0, 'hex': '04000000'}, {'pos': 16, 'hex': '7b2266696c657322'}]},
        ]

    def list_contents(self):
        """List archive contents using '7z l'. Returns the listing text, or None on error."""
        command_list = [
            os.path.join(self.extractors_path, '7z', '7z.exe'),
            'l',   # list contents
            '-y',  # assume Yes on all queries
        ]
        if self.cli_args.password:
            command_list += [f'-p{self.cli_args.password}']

        command_list.append(self.target_file)

        try:
            return self.run_command(command_list)
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to list 7z file with error code {exc.returncode}")
            return None
        except Exception as exc:
            logging.error(f"An error occurred during listing: {exc}")
            return None

    def extract(self):
        """
        Extracts .7z files to a specified output directory using the 7z executable.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        # Construct the command to execute using the path to 7z executable
        command_list = [
            os.path.join(self.extractors_path, '7z', '7z.exe'),
            'x',  # extract files with full paths
            '-y', # assume Yes on all queries
        ]

        # Include password if provided
        if self.cli_args.password:
            command_list += [f'-p{self.cli_args.password}']

        # Set output directory
        command_list.extend([
            self.target_file,
            f'-o{self.extract_directory}'
        ])

        # Running the command using the base class utility method
        try:
            output = self.run_command(command_list)
            if output:
                return True
            else:
                logging.error("Failed to extract .7z file with no output.")
                return False
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract 7z file with error code {exc.returncode}")
            if exc.returncode == 3:
                logging.error("Missing parts of the 7z file.")

            return False
        except Exception as exc:
            logging.error(f"An error occurred during extraction: {exc}")
            return False
