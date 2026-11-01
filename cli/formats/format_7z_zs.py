from .format_7z import Format7zHandler

class Format7zZsHandler(Format7zHandler):
    """
    7-Zip ZS (https://github.com/mcmilk/7-Zip-zstd) in extractors/7zzstd/:
    7-Zip with Zstandard, Brotli, LZ4, LZ5, Lizard and Fast-LZMA2 built into
    the format handlers themselves, not only as stream codecs.

    Extraction is identical to Format7zHandler; only the 7z.exe differs. It
    claims the same detection keys as the 7z, ZIP, SquashFS, NSIS, XZ, ZSTD,
    lzip and LZ4/LZ5/Lizard handlers and is registered right after
    Format7zExtHandler, so it runs when mainline 7-Zip fails (and before plzip
    for lzip). That covers what mainline 7-Zip (even with the Modern7z codec
    plugin) cannot open, e.g. SquashFS with LZ4 (mainline: "Not implemented")
    or NSIS with ZSTD. Brotli (.br) has no magic bytes, so it cannot be routed
    by detection.
    """

    SEVEN_ZIP_FOLDER = '7zzstd'

    @classmethod
    def detection_mimes(cls):
        return [
            'application/x-7z-compressed', 'application/zip',
            'application/x-squashfs', 'application/vnd.squashfs',
            'application/x-xz', 'application/zstd', 'application/x-zstd-compressed-tar',
            'application/x-lzip',
        ]

    @classmethod
    def detection_names(cls):
        return [
            '7zip', 'sevenzip', '7-zip', 'zip', 'squashfs', 'xz',
            'zstd', 'zstandard compressed data',
            'nullsoft scriptable install system',
            'lzip compressed archive',  # tried before FormatLzipHandler (plzip)
            'lz4', 'lz5', 'lizard',     # tried after Format7zExtHandler (Modern7z)
        ]

    @classmethod
    def detection_signatures(cls):
        return []
