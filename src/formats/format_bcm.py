import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatBcmHandler(BaseExtractor):
    """
    Handler class for BCM archive files that utilizes bcm-v160x32.exe for extraction.
    """

    def extract(self):
        """
        Extracts files using the BCM command-line tool.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        # Construct the command to execute using the path to BCM executable
        command_list = [
            os.path.join(self.extractors_path, 'bcm', 'bcm-v160x32.exe'),
            '-d',  # Command to decompress
            '-f',  # Force overwrite of output file
            self.target_file,
        ]

        # Running the command using the base class utility method
        try:
            output = self.run_command(command_list, workdir=self.extract_directory)
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to decompress file with BCM with error code {exc.returncode}: {exc.output}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during BCM decompression: {exc}")
            return False
