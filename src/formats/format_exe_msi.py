import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatMsiHandler(BaseExtractor):
    """
    Handler class for MSI files. Mirrors UniExtract2's MSI chain: lessmsi first
    (proper filenames), then 7z as a generic OLE2 fallback. (MsiX / jsMSIx are
    further UniExtract fallbacks but are not bundled here.)
    """

    @classmethod
    def detection_names(cls):
        # OLE2 magic is ambiguous (also .doc/.xls), so no custom signature here.
        return ['microsoft windows installer']  # DIE

    def _extract_lessmsi(self):
        command_list = [
            os.path.join(self.extractors_path, 'lessmsi', 'lessmsi.exe'),
            'x',                    # extract all files
            self.target_file,       # MSI file to unpack
            self.extract_directory  # directory to extract files
        ]
        try:
            self.run_command(command_list)
            return True
        except subprocess.CalledProcessError as exc:
            logging.info(f"lessmsi failed (code {exc.returncode}); trying 7z fallback.")
        except Exception as exc:
            logging.info(f"lessmsi errored ({exc}); trying 7z fallback.")
        return False

    def _extract_sevenzip(self):
        command_list = [
            os.path.join(self.extractors_path, '7z', '7z.exe'),
            'x',
            '-y',
            self.target_file,
            f'-o{self.extract_directory}',
        ]
        try:
            self.run_command(command_list)
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"7z MSI fallback failed with error code {exc.returncode}")
        except Exception as exc:
            logging.error(f"An error occurred during 7z MSI extraction: {exc}")
        return False

    def extract(self):
        """
        Extracts MSI files: lessmsi first, then 7z (OLE2) as a fallback.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        if self._extract_lessmsi():
            logging.info("MSI extraction completed with lessmsi.")
            return True
        if self._extract_sevenzip():
            logging.info("MSI extraction completed with 7z fallback.")
            return True

        logging.error(f"Failed to extract MSI file: {self.target_file}")
        return False
