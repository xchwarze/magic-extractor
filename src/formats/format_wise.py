import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatWiseHandler(BaseExtractor):
    """
    Handler for Wise installer executables using e_wise.
    e_wise has no output-dir switch; it extracts beside the input, so it is run
    inside the output directory as the working directory.
    """

    def extract(self):
        """
        Extracts a Wise installer into the output directory.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        command_list = [
            os.path.join(self.extractors_path, 'e_wise', 'e_wise.exe'),
            self.target_file,
        ]

        try:
            self.run_command(command_list, workdir=self.extract_directory)
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract Wise installer with error code {exc.returncode}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during extraction: {exc}")
            return False
