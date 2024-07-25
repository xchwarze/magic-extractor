import os
import subprocess
import logging
from extractor import BaseExtractor

class FormatEggHandler(BaseExtractor):
    """
    Handler class for EGG archive files that utilizes ALZipCon for extraction.
    """

    # Common constants
    TOOL_FOLDER = 'extractors'

    def extract(self):
        """
        Extracts EGG files using the ALZipCon command-line tool.

        Returns:
        bool: True if the extraction was successful, False otherwise.
        """
        # Validate and prepare the output directory
        file_path = str(os.path.abspath(self.cli_args.file_path))
        extract_directory = self.validate_output_directory()

        # Construct the command to execute using the path to ALZipCon executable
        command_list = [
            os.path.join(self.bin_path, self.TOOL_FOLDER, 'alzip', 'ALZipCon.exe'),
            '-x',   # Command to extract
            '-oa',  # Overwrite all existing files without asking
        ]

        # Include password if provided
        if self.cli_args.password:
            command_list.append(f'-p{self.cli_args.password}')

        # Set output directory and target file
        command_list.extend([
            file_path,          # File to extract
            extract_directory   # Directory to extract files to
        ])

        # Running the command using the base class utility method
        try:
            self.run_command(command_list, workdir=extract_directory)
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract EGG file with error code {exc.returncode}: {exc.output}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during EGG extraction: {exc}")
            return False
