import os
from .base_extractor import BaseExtractor

class FormatCicdecHandler(BaseExtractor):
    """
    Handler for Clickteam Install Creator installers using cicdec.
    Usage: cicdec.exe <installer> <output_directory>
    """

    @classmethod
    def detection_names(cls):
        return ['clickteam']  # DIE

    def extract(self):
        """
        Extracts a Clickteam installer to the output directory.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        command_list = [
            os.path.join(self.extractors_path, 'cicdec', 'cicdec.exe'),
            self.target_file,
            self.extract_directory,
        ]

        return self.run_extraction(command_list, label="Clickteam")
