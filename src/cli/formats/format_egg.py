import os
from .base_extractor import BaseExtractor

class FormatEggHandler(BaseExtractor):
    """
    Handler class for EGG archive files that utilizes ALZipCon for extraction.
    """

    @classmethod
    def detection_signatures(cls):
        # 'EGGA\x00\x01' at 0.
        return [{'name': 'egg compressed archive', 'patterns': [{'pos': 0, 'hex': '454747410001'}]}]

    def extract(self):
        """
        Extracts EGG files using the ALZipCon command-line tool.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        # Construct the command to execute using the path to ALZipCon executable
        command_list = [
            os.path.join(self.extractors_path, 'alzip', 'ALZipCon.exe'),
            '-x',   # Command to extract
            '-oa',  # Overwrite all existing files without asking
        ]

        # Include password if provided
        if self.cli_args.password:
            command_list.append(f'-p{self.cli_args.password}')

        # Set output directory and target file
        command_list.extend([
            self.target_file,       # File to extract
            self.extract_directory  # Directory to extract files to
        ])

        return self.run_extraction(command_list, workdir=self.extract_directory, label="EGG")
