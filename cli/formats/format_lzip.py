import os
import subprocess
import logging
from .base_extractor import BaseExtractor

class FormatLzipHandler(BaseExtractor):
    """
    Handler for .lz (lzip) single-stream compression using plzip.
    lzip is not a container; it wraps one stream (commonly a .tar), so this
    decompresses to a single file. Use --recursive to then unpack the result.
    Usage: plzip -d -k -f -o <output_file> <file>
    """

    @classmethod
    def detection_mimes(cls):
        return ['application/x-lzip']  # puremagic / Magika

    @classmethod
    def detection_signatures(cls):
        # 'LZIP' at 0.
        return [{'name': 'lzip compressed archive', 'patterns': [{'pos': 0, 'hex': '4c5a4950'}]}]

    def _output_name(self):
        base = os.path.basename(self.target_file)
        return base[:-3] if base.lower().endswith('.lz') else base + '.out'

    def extract(self):
        """
        Decompresses a .lz file into the output directory.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        output_path = os.path.join(self.extract_directory, self._output_name())
        command_list = [
            os.path.join(self.extractors_path, 'plzip', 'plzip.exe'),
            '-d',            # decompress
            '-k',            # keep input file
            '-f',            # overwrite existing output
            '-o', output_path,
            self.target_file,
        ]

        return self.run_extraction(command_list, label="lzip")

    def list_contents(self):
        """Print the (un)compressed sizes using 'plzip -l'. Returns the text, or None on error."""
        command_list = [
            os.path.join(self.extractors_path, 'plzip', 'plzip.exe'),
            '-l',
            self.target_file,
        ]

        try:
            return self.run_command(command_list)
        except subprocess.CalledProcessError as exc:
            logging.error(f"Failed to list lzip file with error code {exc.returncode}")
            return None
        except Exception as exc:
            logging.error(f"An error occurred during listing: {exc}")
            return None
