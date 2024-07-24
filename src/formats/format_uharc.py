import os
import subprocess
import logging
from extractor import BaseExtractor

class FormatUharcHandler(BaseExtractor):
    """
    Handler class for UHARC archive files that utilizes various versions of uharc for extraction.
    """

    # Common constants
    TOOL_FOLDER = 'extractors'
    UHARC_VERSIONS = ['uharc-v0.6b.exe', 'uharc-v0.4.exe', 'uharc-v0.2.exe']

    def extract(self):
        """
        Attempts to extract UHARC files using different versions of uharc command-line tools.

        Returns:
        bool: True if the extraction was successful, False otherwise.
        """
        # Validate and prepare the output directory
        file_path = str(os.path.abspath(self.cli_args.file_path))
        extract_directory = self.validate_output_directory()

        for uharc_version in self.UHARC_VERSIONS:
            if self.try_extract_with_uharc(uharc_version, file_path, extract_directory):
                return True

        logging.error("Failed to extract UHARC file with all provided versions.")
        return False

    def try_extract_with_uharc(self, uharc_version, file_path, extract_directory):
        """
        Tries to extract the file using a specific uharc version.

        Args:
        uharc_version (str): The uharc executable name.
        file_path (str): Path to the archive file.
        extract_directory (str): Directory to extract files.

        Returns:
        bool: True if successful, False otherwise.
        """
        command_list = [
            os.path.join(self.bin_path, self.TOOL_FOLDER, 'uharc', uharc_version),
            'x',                        # Extract files
            f'-t{extract_directory}',   # Target directory
            file_path                   # File to extract
        ]

        try:
            output = self.run_command(command_list, workdir=extract_directory)
            if output:
                logging.info(f"Successfully extracted using {uharc_version}")
                return True
            else:
                logging.info(f"No output from extraction attempt using {uharc_version}")
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract with {uharc_version}: {exc}")
        return False

