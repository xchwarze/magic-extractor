import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatCicdecHandler(BaseExtractor):
    """
    Handler for Clickteam Install Creator installers using cicdec.
    Usage: cicdec.exe <installer> <output_directory>
    """

    def extract(self):
        """
        Extracts a Clickteam installer to the output directory.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        command_list = [
            os.path.join(self.extractors_path, 'cicdec', 'cicdec.exe'),
            self.target_file,
            self.extract_directory,
        ]

        try:
            self.run_command(command_list)
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract Clickteam installer with error code {exc.returncode}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during extraction: {exc}")
            return False
