import os
from .base_extractor import BaseExtractor

class FormatWixHandler(BaseExtractor):
    """
    Handler for MSI / WiX packages using the WiX 'dark' decompiler (v3.14).
    dark decompiles the MSI to a .wxs and exports its binary/cab streams via -x.
    Usage: dark.exe [-nologo] <database.msi> -x <output_dir> [<source.wxs>]
    """

    @classmethod
    def detection_names(cls):
        return ['wix toolset installer']  # DIE

    def extract(self):
        """
        Extracts an MSI/WiX package's streams to the output directory.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        command_list = [
            os.path.join(self.extractors_path, 'wix', 'dark.exe'),
            '-nologo',
            self.target_file,
            '-x', self.extract_directory,
            os.path.join(self.extract_directory, 'decompiled.wxs'),
        ]

        return self.run_extraction(command_list, label="WiX/MSI")
