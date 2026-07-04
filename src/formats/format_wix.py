import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatWixHandler(BaseExtractor):
    """
    Handler for MSI / WiX packages using the WiX 'dark' decompiler.
    dark decompiles the MSI to a .wxs and dumps its binary/cab streams via -x.
    Usage: dark.exe <input.msi> -x <output_dir> <output.wxs>
    """

    def extract(self):
        """
        Extracts an MSI/WiX package's streams to the output directory.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        command_list = [
            os.path.join(self.extractors_path, 'wix', 'dark.exe'),
            self.target_file,
            '-x', self.extract_directory,
            os.path.join(self.extract_directory, 'decompiled.wxs'),
        ]

        try:
            self.run_command(command_list)
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract MSI/WiX package with error code {exc.returncode}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during extraction: {exc}")
            return False
