import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatBcmHandler(BaseExtractor):
    """
    Handler class for BCM archives. BCM 2.x (BCM2) and BCM 1.x (BCM!) use
    incompatible formats, so both bundled binaries are tried in turn.
    """

    # Newest first: v2.03 reads BCM2, v1.60 reads the older BCM! format.
    BCM_EXES = ('bcm-v203x64.exe', 'bcm-v160x32.exe')

    def extract(self):
        """
        Extracts files using the BCM command-line tool.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        for exe in self.BCM_EXES:
            command_list = [
                os.path.join(self.extractors_path, 'bcm', exe),
                '-d',  # Command to decompress
                '-f',  # Force overwrite of output file
                self.target_file,
            ]
            try:
                self.run_command(command_list, workdir=self.extract_directory)
                return True
            except subprocess.CalledProcessError as exc:
                logging.info(f"BCM decompress with {exe} failed (code {exc.returncode}); trying next binary.")
            except Exception as exc:
                logging.info(f"BCM decompress with {exe} errored ({exc}); trying next binary.")

        logging.error(f"Failed to decompress BCM file with all binaries: {self.target_file}")
        return False
