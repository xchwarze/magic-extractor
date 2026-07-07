import os
import fnmatch
import logging
from .base_extractor import BaseExtractor

class FormatInnoSetupHandler(BaseExtractor):
    """
    Handler class for Inno Setup files that utilizes innounp for extraction.
    """

    @classmethod
    def detection_names(cls):
        return ['inno setup installer', 'inno setup module', 'inno setup']  # DIE

    def extract(self):
        """
        Extracts Inno Setup files to a specified output directory using innounp executable.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        # Construct the command to execute using the path to innounp executable
        # (options per innounp 2.70.0 command-line reference / innounp-cl.txt)
        command_list = [
            os.path.join(self.extractors_path, 'innounp', 'innounp.exe'),
            '-e',   # extract files without paths
            '-m',   # extract internal embedded files (license, uninstall.exe)
            '-a',   # extract all copies of duplicate files
            '-b',   # batch / non-interactive: never prompt for password or disk change
            '-y',   # assume Yes on all queries (e.g. overwrite)
            '-o',   # no colored console output (keeps captured logs clean)
            f'-d{self.extract_directory}',  # directory to extract files
        ]

        # Password-protected installers: -b makes innounp fail instead of prompt,
        # so pass the password explicitly when we have one.
        if self.cli_args.password:
            command_list.append(f'-p{self.cli_args.password}')

        command_list.append(self.target_file)  # setup executable to unpack (last)

        if not self.run_extraction(command_list, label="Inno Setup"):
            return False

        # Extraction succeeded; cleanup is cosmetic, so a hiccup there does not
        # turn a good extraction into a failure.
        try:
            self.post_extraction_cleanup(self.extract_directory)
        except OSError as exc:
            logging.error(f"Inno Setup post-extraction cleanup failed: {exc}")
        return True

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
