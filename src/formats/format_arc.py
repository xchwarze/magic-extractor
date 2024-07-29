import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatArcHandler(BaseExtractor):
    """
    Handler class for ARC archive files that utilizes unarc.exe for extraction.
    """

    def extract(self):
        """
        Extracts ARC files using the unarc.exe command-line tool.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        # Construct the command to execute using the path to unarc executable
        command_list = [
            os.path.join(self.extractors_path, 'unarc', 'unarc.exe'),
            'x',                             # Command to extract files with pathnames
            '-o+',                           # Overwrite existing files without asking
            f'-dp{self.extract_directory}',  # Set the destination path for extracted files
            self.target_file,
        ]

        # Running the command using the base class utility method
        try:
            output = self.run_command(command_list)
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to decompress ARC file with error code {exc.returncode}: {exc.output}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during ARC decompression: {exc}")
            return False
