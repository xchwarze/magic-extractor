import os
import uuid
import shutil
import logging
from .base_extractor import BaseExtractor, merge_move

# pea.exe does not exit on an error: it shows a modal dialog (e.g.
# "2 NOT_PEA_HEADER" for a file that is not PEA) and waits, in HIDDEN and
# BATCH mode alike, so an unattended run would hang until someone clicks it.
PEA_MAGIC = b'\xea'
# Kill pea.exe if it outlives this budget (a dialog on a damaged archive).
PEA_MIN_SECONDS, PEA_SECONDS_PER_MB = 120, 5


class FormatPeaHandler(BaseExtractor):
    """
    Handler class for PEA archive files that utilizes PeaZip for extraction.

    pea.exe never extracts into a folder that already exists: it creates
    "<folder> - 1" beside it instead (and exits 0). extract() always gets an
    existing (empty) folder, so pea is pointed at a not-yet-existing subfolder
    and its content is moved up afterwards.
    """

    @classmethod
    def detection_signatures(cls):
        # PEA magic 0xEA 0x01 at 0.
        return [{'name': 'pea compressed archive (v1.x)', 'patterns': [{'pos': 0, 'hex': 'ea01'}]}]

    @classmethod
    def detection_names(cls):
        return ['peazip (.pea)']  # DIE

    def extract(self):
        """
        Extracts PEA files using the PeaZip command-line tool.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        try:
            with open(self.target_file, 'rb') as source_fh:
                is_pea = source_fh.read(len(PEA_MAGIC)) == PEA_MAGIC
            size_mb = os.path.getsize(self.target_file) / (1024 * 1024)
        except OSError as exc:
            logging.error(f"PEA: cannot read {self.target_file}: {exc}")
            return False
        if not is_pea:
            # Never hand pea.exe a non-PEA file: it would block on a dialog.
            logging.error(f"PEA: not a PEA archive (no PEA header): {self.target_file}")
            return False

        staging = os.path.join(self.extract_directory, f'.pea_{uuid.uuid4().hex}')

        # Construct the command to execute using the path to PeaZip executable
        # These parameters and their order came from parse_unpea_cl() from unit_pea.pas
        command_list = [
            os.path.join(self.extractors_path, 'peazip', 'pea.exe'),
            'UNPEA',                 # Command to extract files simply
            self.target_file,        # The PEA file to extract
            staging,                 # Destination directory (must not exist yet, see class doc)
            'RESETDATE',             # This is the only possible value for this field that is expected in this position...
            'SETATTR',               # This field can have these values: SETATTR, RESETATTR
            'EXTRACT2DIR',           # This is the only possible value for this field that is expected in this position...
            'HIDDEN',                # This field can have these values: HIDDEN, BATCH, INTERACTIVE, INTERACTIVE_REPORT, BATCH_REPORT, HIDDEN_REPORT
        ]

        # Include password if provided
        if self.cli_args.password:
            command_list += [self.cli_args.password]

        try:
            timeout = max(PEA_MIN_SECONDS, size_mb * PEA_SECONDS_PER_MB)
            if not self.run_extraction(command_list, label="PEA", timeout=timeout):
                return False
            if not os.path.isdir(staging):
                logging.error("PEA: extraction produced no output folder")
                return False
            for name in os.listdir(staging):
                merge_move(os.path.join(staging, name), os.path.join(self.extract_directory, name))
            return True
        except OSError as exc:
            logging.error(f"PEA: could not move the extracted files: {exc}")
            return False
        finally:
            shutil.rmtree(staging, ignore_errors=True)
