import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class Format7zHandler(BaseExtractor):
    """
    Handler class for .7z files that utilizes 7z for extraction.
    """

    def extract(self):
        """
        Extracts .7z files to a specified output directory using the 7z executable.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        # Construct the command to execute using the path to 7z executable
        command_list = [
            os.path.join(self.extractors_path, '7z', '7z.exe'),
            'x',  # extract files with full paths
            '-y', # assume Yes on all queries
        ]

        # Include password if provided
        if self.cli_args.password:
            command_list += [f'-p{self.cli_args.password}']

        # Set output directory
        command_list.extend([
            self.target_file,
            f'-o{self.extract_directory}'
        ])

        # Running the command using the base class utility method
        try:
            output = self.run_command(command_list)
            if output:
                return True
            else:
                logging.error("Failed to extract .7z file with no output.")
                return False
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract 7z file with error code {exc.returncode}")
            if e.returncode == 3:
                logging.error("Missing parts of the 7z file.")

            return False
        except Exception as exc:
            logging.error(f"An error occurred during extraction: {exc}")
            return False
