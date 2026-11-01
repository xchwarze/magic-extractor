import os
from .base_extractor import BaseExtractor

# unace exits 0 even when the input is not an ACE archive; this is what it prints.
NOT_ACE_MARKER = 'Is no ACE-archive'

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

        return self.run_extraction(command_list, workdir=self.extract_directory, label="ACE",
                                   failure_markers=(NOT_ACE_MARKER,))

    def list_contents(self):
        """List the archive with 'unace l'. Returns the listing text, or None on error."""
        command_list = [os.path.join(self.extractors_path, 'unace', 'unace.exe'), 'l', self.target_file]
        return self.run_listing(command_list, label="ACE", failure_markers=(NOT_ACE_MARKER,))
