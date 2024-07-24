import os
import subprocess
import logging
from extractor import BaseExtractor

class Format7zHandler(BaseExtractor):
    """
    Handler class for .7z files that utilizes 7z for extraction.
    """

    # Common constants
    TOOL_FOLDER = 'extractors'

    def extract(self):
        """
        Extracts .7z files to a specified output directory using the 7z executable.

        Returns:
        bool: True if the extraction was successful, False otherwise.
        """
        # Validate and prepare the output directory
        file_path = str(os.path.abspath(self.cli_args.file_path))
        extract_directory = self.validate_output_directory()

        # Construct the command to execute using the path to 7z executable
        command_list = [
            os.path.join(self.bin_path, self.TOOL_FOLDER, '7z', '7z.exe'),
            'x',  # extract files with full paths
            '-y', # assume Yes on all queries
        ]

        # Include password if provided
        if self.cli_args.password:
            command_list += [f'-p{self.cli_args.password}']

        # Set output directory
        command_list.extend([
            file_path,
            f'-o{extract_directory}'
        ])

        # Running the command using the base class utility method
        try:
            output = self.run_command(command_list)
            if output:
                return True
            else:
                logging.error("Failed to extract .7z file with no output.")
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract 7z file with error code {exc.returncode}")
            if e.returncode == 3:
                logging.error("Missing parts of the 7z file.")
        except Exception as exc:
            logging.error(f"An error occurred during extraction: {exc}")

        # Clean and exit
        self.clean_up_directory(extract_directory)
        return False
