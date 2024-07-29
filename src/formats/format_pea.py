import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatPeaHandler(BaseExtractor):
    """
    Handler class for PEA archive files that utilizes PeaZip for extraction.
    """

    def extract(self):
        """
        Extracts PEA files using the PeaZip command-line tool.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        # Construct the command to execute using the path to PeaZip executable
        # These parameters and their order came from parse_unpea_cl() from unit_pea.pas
        command_list = [
            os.path.join(self.extractors_path, 'peazip', 'pea.exe'),
            'UNPEA',                 # Command to extract files simply
            self.target_file,        # The PEA file to extract
            self.extract_directory,  # Destination directory for the extracted files
            'RESETDATE',             # This is the only possible value for this field that is expected in this position...
            'SETATTR',               # This field can have these values: SETATTR, RESETATTR
            'EXTRACT2DIR',           # This is the only possible value for this field that is expected in this position...
            'HIDDEN',                # This field can have these values: HIDDEN, BATCH, INTERACTIVE, INTERACTIVE_REPORT, BATCH_REPORT, HIDDEN_REPORT
        ]

        # Include password if provided
        if self.cli_args.password:
            command_list += [self.cli_args.password]

        # Running the command using the base class utility method
        try:
            output = self.run_command(command_list)
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to decompress PEA file with error code {exc.returncode}: {exc.output}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during PEA decompression: {exc}")
            return False
