import os
import subprocess
import logging
from extractor import BaseExtractor

class FormatInnoSetupHandler(BaseExtractor):
    """
    Handler class for Inno Setup files that utilizes innounp for extraction.
    """

    # Common constants
    TOOL_FOLDER = 'extractors'

    def extract(self):
        """
        Extracts Inno Setup files to a specified output directory using innounp executable.

        Returns:
        bool: True if the extraction was successful, False otherwise.
        """
        # Validate and prepare the output directory
        file_path = str(os.path.abspath(self.cli_args.file_path))
        extract_directory = self.validate_output_directory()

        # Construct the command to execute using the path to innounp executable
        command_list = [
            os.path.join(self.bin_path, self.TOOL_FOLDER, 'innounp', 'innounp.exe'),
            '-e',  # extract files without paths
            '-m',  # extract internal embedded files
            '-a',  # extract all copies of duplicate files
            '-y',  # assume Yes on all queries
            f'-d"{extract_directory}"'  # directory to extract files
            f' "{file_path}"',  # setup executable to unpack
        ]

        # Running the command using the base class utility method
        try:
            output = self.run_command(command_list, os.path.join(self.bin_path, self.TOOL_FOLDER, 'innounp'))
            if output:
                self.post_extraction_cleanup(extract_directory)
                return True
            else:
                logging.error("Failed to extract Inno Setup file with no output.")
                return False
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract Inno Setup file with error code {exc.returncode}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during extraction: {exc}")
            return False

    def post_extraction_cleanup(self, extract_directory):
        """
        Handles post-extraction cleanup including renaming and deleting specific files.

        Args:
        extract_directory (str): The directory where files have been extracted.
        """
        # Example logic for renaming files
        app_dir = os.path.join(extract_directory, '{app}')
        self.rename_files(app_dir)
        self.remove_files(app_dir)

    def rename_files(self, directory):
        """
        Rename files with version suffixes in the directory.
        """
        for filename in os.listdir(directory):
            if ',1' in filename:
                new_name = filename.replace(',1', '')
                os.rename(os.path.join(directory, filename), os.path.join(directory, new_name))
                logging.info(f"Renamed {filename} to {new_name}")

    def remove_files(self, directory):
        """
        Remove files that are not needed after extraction.
        """
        cleanup_patterns = ['*,2.*', '*,3.*', 'install_script.iss']
        for pattern in cleanup_patterns:
            for filename in fnmatch.filter(os.listdir(directory), pattern):
                os.remove(os.path.join(directory, filename))
                logging.info(f"Removed {filename}")
