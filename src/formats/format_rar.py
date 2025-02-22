import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatRarHandler(BaseExtractor):
    """
    Handler class for .rar files that utilizes UnRar for extraction.
    """

    def extract(self):
        """
        Extracts RAR files using the unrar command-line tool.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        # Construct the command to execute using the path to unrar executable
        command_list = [
            os.path.join(self.extractors_path, 'rar', 'unrar.exe'), 
            'x',  # Extract files with full paths
            '-y', # Assume Yes on all queries
        ]

        # Include password if provided
        if self.cli_args.password:
            command_list += [f'-p{self.cli_args.password}']

        # Set output directory
        command_list.extend([
            self.target_file,
            self.extract_directory
        ])

        # Running the command using the base class utility method
        try:
            output = self.run_command(command_list)
            if output:
                return True    
            else:
                logging.error("Failed to extract .rar file with no output.")
                return False
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract RAR file with error: {exc.output}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during RAR extraction: {exc}")
            return False
