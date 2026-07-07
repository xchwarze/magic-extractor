from .format_7z import Format7zHandler

class Format7zExtHandler(Format7zHandler):
    """
    7-Zip formats that require a third-party plugin in the bundled 7-Zip's
    Formats/ (or Codecs/) folder: Asar, forensic7z (EWF/AD1/AFF), Iso7z (disc
    images), ExFat7z, eDecoder (mail/encoding), Py7z (PyInstaller).

    Extraction is identical to Format7zHandler (it shells out to the same
    7z.exe, which gains these formats once the plugin is present); only the
    detection set differs. Without the plugin the file is identified but
    extraction fails.
    """

    @classmethod
    def detection_mimes(cls):
        return []

    @classmethod
    def detection_names(cls):
        # DIE/name-based routes (magic-less): PyInstaller (Py7z) + asar name.
        return ['pyinstaller', 'asar archive (electron)']

    @classmethod
    def detection_signatures(cls):
        return [
            # ExFat7z
            {'name': 'exfat', 'patterns': [{'pos': 3, 'hex': '4558464154202020'}]},  # 'EXFAT   ' @3
            # forensic7z (EWF / FTK / AFF)
            {'name': 'encase e01/s01', 'patterns': [{'pos': 0, 'hex': '455646090d0aff00'}]},  # 'EVF\x09\r\n\xff\x00'
            {'name': 'encase ex01', 'patterns': [{'pos': 0, 'hex': '455646320d0a8100'}]},     # 'EVF2\r\n\x81\x00'
            {'name': 'encase l01', 'patterns': [{'pos': 0, 'hex': '4c5646090d0aff00'}]},      # 'LVF\x09\r\n\xff\x00'
            {'name': 'encase lx01', 'patterns': [{'pos': 0, 'hex': '4c4546320d0a8100'}]},     # 'LEF2\r\n\x81\x00' (per TrID; not LVF2)
            {'name': 'ftk ad1', 'patterns': [{'pos': 0, 'hex': '41445345474d454e54454446494c4500'}]},  # 'ADSEGMENTEDFILE\x00'
            {'name': 'aff', 'patterns': [{'pos': 0, 'hex': '41464631300d0a00'}]},             # 'AFF10\r\n\x00'
            {'name': 'whx', 'patterns': [{'pos': 0, 'hex': '574858204261636b75702076312e3000'}]},  # 'WHX Backup v1.0\x00' (WinHex)
            # Iso7z (disc images)
            {'name': 'ciso/cso', 'patterns': [{'pos': 0, 'hex': '4349534f'}]},                # 'CISO'
            {'name': 'chd', 'patterns': [{'pos': 0, 'hex': '4d436f6d70724844'}]},             # 'MComprHD' (MAME CHD)
            {'name': 'ecm', 'patterns': [{'pos': 0, 'hex': '45434d00'}]},                     # 'ECM\x00'
            {'name': 'isz', 'patterns': [{'pos': 0, 'hex': '49735a21'}]},                     # 'IsZ!' (UltraISO)
            {'name': 'alcohol mds', 'patterns': [{'pos': 0, 'hex': '4d454449412044455343524950544f52'}]},  # 'MEDIA DESCRIPTOR'
            {'name': 'clonecd ccd', 'patterns': [{'pos': 0, 'hex': '5b436c6f6e6543445d'}]},   # '[CloneCD]'
            {'name': 'zisofs', 'patterns': [{'pos': 0, 'hex': '37e45396c9dbd607'}]},          # zisofs block magic
            # eDecoder (mail / encoding)
            {'name': 'tnef', 'patterns': [{'pos': 0, 'hex': '789f3e22'}]},                    # winmail.dat (TNEF)
            {'name': 'dbx', 'patterns': [{'pos': 0, 'hex': 'cfad12fe'}]},                     # Outlook Express DBX
            {'name': 'warc', 'patterns': [{'pos': 0, 'hex': '574152432f'}]},                  # 'WARC/'
            {'name': 'binhex', 'patterns': [{'pos': 0, 'hex': '28546869732066696c65206d75737420626520636f6e766572746564'}]},  # BinHex .hqx
            {'name': 'yenc', 'patterns': [{'pos': 0, 'hex': '3d79626567696e'}]},              # '=ybegin' (yEnc)
            {'name': 'tbb', 'patterns': [{'pos': 0, 'hex': '20067919080c0000'}]},             # The Bat! message base
            {'name': 'macbinary', 'patterns': [{'pos': 102, 'hex': '6d42494e'}]},             # 'mBIN' @102 (MacBinary III only)
            # Modern7z (Codecs/): LZ4 frame + Firefox jsonlz4 (both magic-detectable).
            {'name': 'lz4', 'patterns': [{'pos': 0, 'hex': '04224d18'}]},                     # LZ4 frame magic
            {'name': 'lz5', 'patterns': [{'pos': 0, 'hex': '05224d18'}]},                     # LZ5 frame (LZ4 family, ver 05)
            {'name': 'lizard', 'patterns': [{'pos': 0, 'hex': '06224d18'}]},                  # Lizard frame (LZ4 family, ver 06)
            {'name': 'mozlz4', 'patterns': [{'pos': 0, 'hex': '6d6f7a4c7a343000'}]},          # 'mozLz40\x00' (Firefox jsonlz4)
            # Asar (Electron): 04 00 00 00 @0 AND '{"files"' @16 (AND avoids false matches).
            {'name': 'asar archive (electron)', 'patterns': [
                {'pos': 0, 'hex': '04000000'}, {'pos': 16, 'hex': '7b2266696c657322'}]},
        ]
