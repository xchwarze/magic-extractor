import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatZpaqHandler(BaseExtractor):
    """
    Handler class for ZPAQ archive files that utilizes zpaq for extraction.
    """

    def extract(self):
        """
        Extracts ZPAQ files using the zpaq command-line tool.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        # Construct the command to execute using the path to zpaq executable
        command_list = [
            os.path.join(self.extractors_path, 'zpaq', 'zpaq.exe'),
            'x',                             # Command to extract
            self.target_file,                # File to extract
            f'-to{self.extract_directory}',  # Directory to extract files
            '-f',                            # Force overwrite of existing files
        ]

        # Include password if provided
        if self.cli_args.password:
            command_list += [f'-key{self.cli_args.password}']

        # Running the command using the base class utility method
        try:
            output = self.run_command(command_list, workdir=self.extract_directory)
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
