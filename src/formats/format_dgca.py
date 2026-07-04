import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatDgcaHandler(BaseExtractor):
    """
    Handler for DGCA (.dgc) archives using the dgcac console tool.

    dgcac has no output-directory switch, so extraction runs with the output
    directory as the working directory. The 'e' extract command letter should be
    confirmed against dgcac.exe on Windows (docs are Japanese/Shift-JIS).
    """

    def extract(self):
        """
        Extracts a DGCA archive into the output directory.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        command_list = [
            os.path.join(self.extractors_path, 'dgca', 'dgcac.exe'),
            'e',                # extract command (verify on Windows)
            self.target_file,
        ]

        try:
            # dgcac extracts into the current directory; run it inside the output dir.
            self.run_command(command_list, workdir=self.extract_directory)
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to extract DGCA archive with error code {exc.returncode}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during extraction: {exc}")
            return False
