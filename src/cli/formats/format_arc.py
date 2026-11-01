import os
from .base_extractor import BaseExtractor

class FormatArcHandler(BaseExtractor):
    """
    Handler class for ARC archive files that utilizes unarc.exe for extraction.
    """

    @classmethod
    def detection_signatures(cls):
        # 'ArC\x01' at 0 (FreeArc).
        return [{'name': 'freearc compressed archive', 'patterns': [{'pos': 0, 'hex': '41724301'}]}]

    @classmethod
    def detection_names(cls):
        return ['freearc archive (.arc)']  # DIE

    def extract(self):
        """
        Extracts ARC files using the unarc.exe command-line tool.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        # Construct the command to execute using the path to unarc executable
        # peazip portable has in its res folder a newer version that supports compression of this binary
        command_list = [
            os.path.join(self.extractors_path, 'unarc', 'unarc.exe'),
            'x',                             # Command to extract files with pathnames
            '-o+',                           # Overwrite existing files without asking
            f'-dp{self.extract_directory}',  # Set the destination path for extracted files
            self.target_file,
        ]

        return self.run_extraction(command_list, label="ARC")
