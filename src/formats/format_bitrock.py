import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatBitrockHandler(BaseExtractor):
    """
    Handler for BitRock / InstallBuilder installers using bitrock-unpacker.
    Usage: bitrock-unpacker.exe INSTALLER.EXE OUTPUT_DIR
    """

    @classmethod
    def detection_names(cls):
        return ['bitrock installer']  # DIE

    def extract(self):
        """
        Extracts a BitRock installer to the output directory.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        command_list = [
            os.path.join(self.extractors_path, 'bitrock-unpacker', 'bitrock-unpacker.exe'),
            self.target_file,
            self.extract_directory,
        ]

        try:
            self.run_command(command_list)
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract BitRock installer with error code {exc.returncode}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during extraction: {exc}")
            return False
