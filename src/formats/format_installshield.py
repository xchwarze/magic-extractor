import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatInstallShieldHandler(BaseExtractor):
    """
    Handler for InstallShield CAB archives using unshield.
    Usage: unshield [-d <dir>] x <cabfile>  (operates on the InstallShield .cab,
    e.g. data1.cab; a wrapping setup.exe may need unpacking first).
    """

    def extract(self):
        """
        Extracts an InstallShield CAB to the output directory.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        command_list = [
            os.path.join(self.extractors_path, 'unshield', 'unshield.exe'),
            '-d', self.extract_directory,
            'x',
            self.target_file,
        ]

        try:
            self.run_command(command_list)
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract InstallShield archive with error code {exc.returncode}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during extraction: {exc}")
            return False
