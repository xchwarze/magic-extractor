import os
from .base_extractor import BaseExtractor

class FormatBitrockHandler(BaseExtractor):
    """
    Handler for BitRock / InstallBuilder installers using bitrock-unpacker.
    Usage: bitrock-unpacker.exe INSTALLER.EXE OUTPUT_DIR
    """

    @classmethod
    def detection_names(cls):
        return ['bitrock installer']  # DIE

    def extract(self):
        """
        Extracts a BitRock installer to the output directory.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        command_list = [
            os.path.join(self.extractors_path, 'bitrock-unpacker', 'bitrock-unpacker.exe'),
            self.target_file,
            self.extract_directory,
        ]

        return self.run_extraction(command_list, label="BitRock")
