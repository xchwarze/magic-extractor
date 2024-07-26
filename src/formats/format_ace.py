import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatAceHandler(BaseExtractor):
    """
    Handler class for ACE archive files that utilizes unace for extraction.
    """

    def extract(self):
        """
        Extracts ACE files using the unace command-line tool.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        # Construct the command to execute using the path to unace executable
        command_list = [
            os.path.join(self.extractors_path, 'unace', 'unace.exe'),
            'x',              # Extract with full paths
            self.target_file  # File to extract
        ]

        # Running the command using the base class utility method
        try:
            output = self.run_command(command_list, workdir=self.extract_directory)
            if output:
                return True
            else:
                logging.error("Failed to extract ACE file with no output.")
                return False
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract ACE file with error code {exc.returncode}: {exc.output}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during ACE extraction: {exc}")
            return False
