import os
import shutil
import logging
import tempfile
from .base_extractor import BaseExtractor

# kgb2_console exits 0 even when it cannot read the input; this is what it prints.
BROKEN_MARKER = 'Archive is broken!'
# Start of a KGB archive (same bytes as the detection signature).
KGB_MAGIC = b'KGB_arch -'
_SCAN_CHUNK = 1 << 20

class FormatKgbHandler(BaseExtractor):
    """
    Handler class for KGB archive files that utilizes kgb2_console for extraction.

    A KGB SFX (.exe) is a PE stub with the archive appended. kgb2_console
    cannot open the .exe itself, so the payload (from the first KGB_MAGIC) is
    copied to a temporary .kgb and extracted from there.
    """

    @classmethod
    def detection_signatures(cls):
        # 'KGB_arch -' at 0 + CRLF at 11. No engine names KGB.
        return [{'name': 'kgb archiver compressed archive',
                 'patterns': [{'pos': 0, 'hex': '4b47425f61726368202d'}, {'pos': 11, 'hex': '0d0a'}]}]

    def _sfx_payload_offset(self):
        """
        Offset of the KGB archive inside a PE (SFX) file: None for a plain
        archive, -1 for a PE without a KGB payload.
        """
        with open(self.target_file, 'rb') as source_fh:
            if source_fh.read(2) != b'MZ':
                return None
            source_fh.seek(0)
            position, tail = 0, b''
            while True:
                chunk = source_fh.read(_SCAN_CHUNK)
                if not chunk:
                    return -1
                block = tail + chunk
                index = block.find(KGB_MAGIC)
                if index != -1:
                    return position - len(tail) + index
                tail = block[-(len(KGB_MAGIC) - 1):]
                position += len(chunk)

    def _extract_archive(self, archive_path):
        command_list = [
            os.path.join(self.extractors_path, 'kgb', 'kgb2_console.exe'),
            archive_path,
        ]
        return self.run_extraction(command_list, workdir=self.extract_directory, label="KGB",
                                   failure_markers=(BROKEN_MARKER,))

    def extract(self):
        """
        Extracts KGB files (or the archive inside a KGB SFX) using kgb2_console.

        Returns:
            bool: True if the extraction was successful, False otherwise.
        """
        try:
            offset = self._sfx_payload_offset()
        except OSError as exc:
            logging.error(f"KGB: cannot read {self.target_file}: {exc}")
            return False

        if offset is None:
            return self._extract_archive(self.target_file)
        if offset < 0:
            logging.error(f"KGB: no KGB archive inside {self.target_file}")
            return False

        logging.info(f"KGB SFX: archive payload at offset {offset}")
        temp_dir = tempfile.mkdtemp(prefix='mx_kgb_')
        try:
            base_name = os.path.splitext(os.path.basename(self.target_file))[0]
            payload_path = os.path.join(temp_dir, base_name + '.kgb')
            with open(self.target_file, 'rb') as source_fh, open(payload_path, 'wb') as payload_fh:
                source_fh.seek(offset)
                shutil.copyfileobj(source_fh, payload_fh)
            return self._extract_archive(payload_path)
        except OSError as exc:
            logging.error(f"KGB: cannot copy the SFX payload: {exc}")
            return False
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
