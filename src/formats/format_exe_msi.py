import os
import subprocess
import logging
from extractor import BaseExtractor

class FormatMsiHandler(BaseExtractor):
    """
    Handler class for MSI files that utilizes lessmsi for extraction.
    """

    # Common constants
    TOOL_FOLDER = 'extractors'

    def extract(self):
        """
        Extracts MSI files to a specified output directory using lessmsi executable.

        Returns:
        bool: True if the extraction was successful, False otherwise.
        """
        # Validate and prepare the output directory
        file_path = str(os.path.abspath(self.cli_args.file_path))
        extract_directory = self.validate_output_directory()

        # Construct the command to execute using the path to lessmsi executable
        command_list = [
            os.path.join(self.bin_path, self.TOOL_FOLDER, 'lessmsi', 'lessmsi.exe'),
            'x',                # extract all files
            file_path,          # MSI file to unpack
            extract_directory   # directory to extract files
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
