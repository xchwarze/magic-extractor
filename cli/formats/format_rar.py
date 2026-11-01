import os
from .base_extractor import BaseExtractor

class FormatRarHandler(BaseExtractor):
    """
    Handler class for .rar files that utilizes UnRar for extraction.
    """

    @classmethod
    def detection_mimes(cls):
        return ['application/vnd.rar', 'application/x-rar', 'application/x-rar-compressed']  # puremagic / Magika

    @classmethod
    def detection_names(cls):
        return ['winrar', 'rar', 'winrar installer']  # DIE (sfx/installer) / binwalk-Magika

    @classmethod
    def detection_signatures(cls):
        # 'Rar!\x1a' at 0 (covers RAR 4.x and 5.x).
        return [{'name': 'rar compressed archive', 'patterns': [{'pos': 0, 'hex': '526172211a'}]}]

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

        # Password if provided; otherwise -p- so an encrypted archive fails
        # instead of prompting.
        command_list.append(f'-p{self.cli_args.password}' if self.cli_args.password else '-p-')

        # Set output directory
        command_list.extend([
            self.target_file,
            self.extract_directory
        ])

        return self.run_extraction(command_list, label="RAR")

    def list_contents(self):
        """List the archive with 'unrar l'. Returns the listing text, or None on error."""
        command_list = [os.path.join(self.extractors_path, 'rar', 'unrar.exe'), 'l']
        # -p- : never prompt for a password (an encrypted header would block)
        command_list.append(f'-p{self.cli_args.password}' if self.cli_args.password else '-p-')
        command_list.append(self.target_file)
        return self.run_listing(command_list, label="RAR")
