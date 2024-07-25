import os
import subprocess
import logging
from extractor import BaseExtractor

class FormatBcmHandler(BaseExtractor):
    """
    Handler class for BCM archive files that utilizes bcm-v160x32.exe for extraction.
    """

    # Common constants
    TOOL_FOLDER = 'extractors'

    def extract(self):
        """
        Extracts files using the BCM command-line tool.

        Returns:
        bool: True if the extraction was successful, False otherwise.
        """
        # Validate and prepare the output directory
        file_path = str(os.path.abspath(self.cli_args.file_path))
        extract_directory = os.path.join(self.validate_output_directory(), os.path.basename(file_path))

        # Construct the command to execute using the path to BCM executable
        command_list = [
            os.path.join(self.bin_path, self.TOOL_FOLDER, 'bcm', 'bcm-v160x32.exe'),
            '-d',  # Command to decompress
            file_path,
            extract_directory,
            '-f'   # Force overwrite of output file
        ]

        # Running the command using the base class utility method
        try:
            output = self.run_command(command_list)
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to decompress file with BCM with error code {exc.returncode}: {exc.output}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during BCM decompression: {exc}")
            return False
