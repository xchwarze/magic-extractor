import os
from .base_extractor import BaseExtractor

class FormatZpaqHandler(BaseExtractor):
    """
    Handler class for ZPAQ archive files that utilizes zpaq for extraction.
    """

    @classmethod
    def detection_signatures(cls):
        # '7kSt' at 0.
        return [{'name': 'zpaq compressed archive', 'patterns': [{'pos': 0, 'hex': '376b5374'}]}]

    @classmethod
    def detection_names(cls):
        return ['zpaq compressed archive (.zpaq)']  # DIE

    def extract(self):
        """
        Extracts ZPAQ files using the zpaq command-line tool.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        # Construct the command to execute using the path to zpaq executable
        command_list = [
            os.path.join(self.extractors_path, 'zpaq', 'zpaq.exe'),
            'x',                            # Command to extract
            self.target_file,               # File to extract
            '-to', self.extract_directory,  # Directory to extract files (separate token)
            '-f',                           # Force overwrite of existing files
        ]

        # Include password if provided (flag and value are separate tokens)
        if self.cli_args.password:
            command_list += ['-key', self.cli_args.password]

        return self.run_extraction(command_list, workdir=self.extract_directory, label="ZPAQ")
