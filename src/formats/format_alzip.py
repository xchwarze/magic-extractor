import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatAlzipHandler(BaseExtractor):
    """
    Handler class for ALZip archive files that utilizes ALZipCon for extraction.
    If I want to use a 100% gpl version of the decompressor I can use unalz.exe which is already downloaded in the bin folder.
    """

    def extract(self):
        """
        Extracts ALZip files using the ALZipCon command-line tool.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        # Construct the command to execute using the path to ALZipCon executable
        command_list = [
            os.path.join(self.extractors_path, 'alzip', 'ALZipCon.exe'),
            '-x',   # Command to extract
            '-oa',  # Extract without using folder names
        ]

        # Include password if provided
        if self.cli_args.password:
            command_list.append(f'-p{self.cli_args.password}')

        # Set output directory and target file
        command_list.extend([
            self.target_file,       # File to extract
            self.extract_directory  # Directory to extract files to
        ])

        # Running the command using the base class utility method
        try:
            self.run_command(command_list, workdir=self.extract_directory)
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract ALZip file with error code {exc.returncode}: {exc.output}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during ALZip extraction: {exc}")
            return False
