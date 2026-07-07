import os
from .base_extractor import BaseExtractor

class FormatKgbHandler(BaseExtractor):
    """
    Handler class for KGB archive files that utilizes kgb2_console for extraction.
    """

    @classmethod
    def detection_signatures(cls):
        # 'KGB_arch -' at 0 + CRLF at 11. No engine names KGB.
        return [{'name': 'kgb archiver compressed archive',
                 'patterns': [{'pos': 0, 'hex': '4b47425f61726368202d'}, {'pos': 11, 'hex': '0d0a'}]}]

    def extract(self):
        """
        Extracts KGB files using the kgb2_console command-line tool.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        # Construct the command to execute using the path to kgb2_console executable
        command_list = [
            os.path.join(self.extractors_path, 'kgb', 'kgb2_console.exe'),
            self.target_file  # File to extract
        ]

        return self.run_extraction(command_list, workdir=self.extract_directory, label="KGB")
