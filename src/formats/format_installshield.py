import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatInstallShieldHandler(BaseExtractor):
    """
    Handler for InstallShield CAB archives using unshield.
    Extract: unshield -d <dir> x <cabfile>. Some InstallShield cabs are
    obfuscated; if extraction fails, unshield-deobfuscate is tried first.
    """

    @classmethod
    def detection_names(cls):
        return ['installshield setup']  # DIE

    def _unshield_exe(self):
        return os.path.join(self.extractors_path, 'unshield', 'unshield.exe')

    def _deobfuscate_exe(self):
        return os.path.join(self.extractors_path, 'unshield', 'unshield-deobfuscate.exe')

    def _extract_cab(self, cabfile):
        command_list = [self._unshield_exe(), '-d', self.extract_directory, 'x', cabfile]
        try:
            self.run_command(command_list)
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"unshield failed with error code {exc.returncode}")
            return False
        except Exception as exc:
            logging.error(f"An error occurred during extraction: {exc}")
            return False

    def extract(self):
        """
        Extracts an InstallShield CAB, deobfuscating and retrying if needed.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        if self._extract_cab(self.target_file):
            return True

        # Retry via deobfuscation for obfuscated InstallShield cabs.
        logging.info("unshield extraction failed; trying deobfuscation.")
        deobfuscated = os.path.join(self.extract_directory, 'deobfuscated.cab')
        try:
            self.run_command([self._deobfuscate_exe(), self.target_file, deobfuscated])
        except Exception as exc:
            logging.error(f"unshield-deobfuscate failed: {exc}")
            return False

        return self._extract_cab(deobfuscated)

    def list_contents(self):
        """List CAB contents using 'unshield l'. Returns the listing text, or None on error."""
        command_list = [self._unshield_exe(), 'l', self.target_file]
        try:
            return self.run_command(command_list)
        except subprocess.CalledProcessError as exc:
            logging.error(f"unshield list failed with error code {exc.returncode}")
            return None
        except Exception as exc:
            logging.error(f"An error occurred during listing: {exc}")
            return None
