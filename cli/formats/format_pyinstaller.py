import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatPyInstallerHandler(BaseExtractor):
    """
    Handler for PyInstaller-built executables using pyinstxtractor-ng.
    It has no output-dir switch; it writes '<name>_extracted' into the working
    directory, so it is run inside the output directory.
    Usage: pyinstxtractor-ng.exe <filename>
    """

    @classmethod
    def detection_names(cls):
        return ['PyInstaller']  # DIE tags it type "packer", name "PyInstaller"

    def extract(self):
        """
        Extracts a PyInstaller executable into the output directory.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        command_list = [
            os.path.join(self.extractors_path, 'pyinstxtractor-ng', 'pyinstxtractor-ng.exe'),
            self.target_file,
        ]

        try:
            self.run_command(command_list, workdir=self.extract_directory)
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract PyInstaller executable with error code {exc.returncode}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during extraction: {exc}")
            return False
