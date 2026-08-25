import os
import shutil
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
        # (options per innounp 2.70.1 command-line reference / innounp-cl.txt)
        command_list = [
            os.path.join(self.extractors_path, 'innounp', 'innounp.exe'),
            '-x',   # extract the files from the installation 
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
        Flattens the "{app}" virtual directory -x extracts files under into
        extract_directory.

        Args:
        extract_directory (str): The directory where files have been extracted.
        """
        app_dir = os.path.join(extract_directory, '{app}')
        if not os.path.isdir(app_dir):
            return

        self.flatten_directory(app_dir, extract_directory)

    def flatten_directory(self, source_dir, target_dir):
        """
        Move every entry out of source_dir into target_dir, then remove the
        now-empty source_dir. source_dir is a subdirectory of target_dir, so
        each move is a same-volume rename (O(1) regardless of file size).
        """
        for name in os.listdir(source_dir):
            destination = os.path.join(target_dir, name)
            if os.path.exists(destination):
                logging.warning(f"Skipped flattening {name}: already exists in {target_dir}")
                continue
            shutil.move(os.path.join(source_dir, name), destination)

        os.rmdir(source_dir)
