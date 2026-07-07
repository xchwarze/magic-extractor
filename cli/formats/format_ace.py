import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatAceHandler(BaseExtractor):
    """
    Handler class for ACE archive files that utilizes unace for extraction.
    """

    @classmethod
    def detection_mimes(cls):
        return ['application/x-ace', 'application/x-ace-compressed']  # puremagic / Magika

    @classmethod
    def detection_names(cls):
        return ['winace', 'ace']  # DIE (sfx) / binwalk-Magika

    @classmethod
    def detection_signatures(cls):
        # '**ACE**' signature at offset 7.
        return [{'name': 'ace compressed archive',
                 'patterns': [{'pos': 7, 'hex': '2a2a4143452a2a'}]}]

    def extract(self):
        """
        Extracts ACE files using the unace command-line tool.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        # Construct the command to execute using the path to unace executable
        command_list = [
            os.path.join(self.extractors_path, 'unace', 'unace.exe'),
            'x',              # Extract with full paths
            self.target_file  # File to extract
        ]

        # Running the command using the base class utility method
        try:
            self.run_command(command_list, workdir=self.extract_directory)  # raises on non-zero
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract ACE file with error code {exc.returncode}: {exc.stderr}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during ACE extraction: {exc}")
            return False
