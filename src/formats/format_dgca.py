import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatDgcaHandler(BaseExtractor):
    """
    Handler for DGCA (.dgc) archives using the dgcac console tool.
    Usage: dgcac.exe e [-pPASSWORD] <archive> <output_dir>
    """

    def extract(self):
        """
        Extracts a DGCA archive into the output directory.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        command_list = [os.path.join(self.extractors_path, 'dgca', 'dgcac.exe'), 'e']
        if getattr(self.cli_args, 'password', None):
            command_list.append(f'-p{self.cli_args.password}')
        command_list += [self.target_file, self.extract_directory]

        try:
            self.run_command(command_list)
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract DGCA archive with error code {exc.returncode}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during extraction: {exc}")
            return False

    def list_contents(self):
        """List archive contents using 'dgcac l'. Returns the listing text, or None on error."""
        command_list = [os.path.join(self.extractors_path, 'dgca', 'dgcac.exe'), 'l']
        if getattr(self.cli_args, 'password', None):
            command_list.append(f'-p{self.cli_args.password}')
        command_list.append(self.target_file)

        try:
            return self.run_command(command_list)
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to list DGCA archive with error code {exc.returncode}")
            return None
        except Exception as exc:
            logging.error(f"An error occurred during listing: {exc}")
            return None
