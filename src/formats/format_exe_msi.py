import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatMsiHandler(BaseExtractor):
    """
    Handler class for MSI files that utilizes lessmsi for extraction.
    """

    def extract(self):
        """
        Extracts MSI files to a specified output directory using lessmsi executable.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        # Construct the command to execute using the path to lessmsi executable
        command_list = [
            os.path.join(self.extractors_path, 'lessmsi', 'lessmsi.exe'),
            'x',                    # extract all files
            self.target_file,       # MSI file to unpack
            self.extract_directory  # directory to extract files
        ]

        # Running the command using the base class utility method
        try:
            output = self.run_command(command_list)
            if output:
                logging.info("MSI extraction completed successfully.")
                return True
            else:
                logging.error("Failed to extract MSI file with no output.")
                return False
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract MSI file with error code {exc.returncode}: {exc.stderr}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during extraction: {exc}")
            return False
