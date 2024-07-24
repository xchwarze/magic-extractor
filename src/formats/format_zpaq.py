import os
import subprocess
import logging
from extractor import BaseExtractor

class FormatZpaqHandler(BaseExtractor):
    """
    Handler class for ZPAQ archive files that utilizes zpaq for extraction.
    """

    # Common constants
    TOOL_FOLDER = 'extractors'

    def extract(self):
        """
        Extracts ZPAQ files using the zpaq command-line tool.

        Returns:
        bool: True if the extraction was successful, False otherwise.
        """
        # Validate and prepare the output directory
        file_path = str(os.path.abspath(self.cli_args.file_path))
        extract_directory = self.validate_output_directory()

        # Construct the command to execute using the path to zpaq executable
        command_list = [
            os.path.join(self.bin_path, self.TOOL_FOLDER, 'zpaq', 'zpaq.exe'),
            'x',                        # Command to extract
            file_path,                  # File to extract
            f'-to{extract_directory}',  # Directory to extract files
            '-f',                       # Force overwrite of existing files
        ]

        # Include password if provided
        if self.cli_args.password:
            command_list += [f'-key{self.cli_args.password}']

        # Running the command using the base class utility method
        try:
            output = self.run_command(command_list, workdir=extract_directory)
            if output:
                return True
            else:
                logging.error("Failed to extract ZPAQ file with no output.")
                return False
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract ZPAQ file with error code {exc.returncode}: {exc.output}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during ZPAQ extraction: {exc}")
            return False
