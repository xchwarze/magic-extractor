"""
Verification aid for the detection -> handler routing map (data/handlers.json).

Read-only reporter. Runs every detector over the sample files in test/ and
cross-checks the strings they emit against the keys in handlers.json:

  * gap    : a detector emitted a string that has no map entry (candidate to add)
  * unused : a map key that no detector emitted across the samples
             (candidate to remove, e.g. unverified names)

It never writes handlers.json; the map is curated by hand. This must run on
Windows, where the bundled detector .exe binaries execute.

Usage:  python test/verify_detections.py
"""

import os
import sys
import logging

# Make the application source importable and resolve bin/ and data/ under it.
SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
sys.path.insert(0, SRC_PATH)

import formats
from file_type import (
    determine_file_type_with_magic,
    determine_file_type_with_binwalk,
    determine_file_type_with_die,
    determine_file_type_with_trid,
    determine_file_type_with_magika,
)

BIN_PATH = os.path.join(SRC_PATH, 'bin')
DATA_PATH = os.path.join(SRC_PATH, 'data')
TEST_DIR = os.path.dirname(os.path.abspath(__file__))

# Directories that hold tool data rather than sample files.
SKIP_DIRS = {'defs'}
SKIP_EXTENSIONS = {'.py'}


def collect_for(file_path):
    """Return (mime_strings, detection_strings) emitted by all detectors for one file."""
    mimes, detections = set(), set()

    magic_mimes = determine_file_type_with_magic(file_path=file_path, fast_check=False)
    if magic_mimes:
        mimes.update(value.lower() for value in magic_mimes)

    magika_result = determine_file_type_with_magika(file_path=file_path, bin_path=BIN_PATH)
    if magika_result:
        mimes.update(value.lower() for value in magika_result["mime_types"])
        detections.update(value.lower() for value in magika_result["labels"])

    for detector in (determine_file_type_with_binwalk, determine_file_type_with_die, determine_file_type_with_trid):
        result = detector(file_path=file_path, bin_path=BIN_PATH)
        if result:
            detections.update(value.lower() for value in result)

    return mimes, detections


def iter_samples():
    """Yield sample file paths under test/, skipping tool-data dirs and this script."""
    for root, dirs, files in os.walk(TEST_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if os.path.splitext(name)[1].lower() in SKIP_EXTENSIONS:
                continue
            yield os.path.join(root, name)


def main():
    # Detector functions log errors for unmatched files; silence them for a clean report.
    logging.disable(logging.CRITICAL)
    formats.init_handlers(DATA_PATH)

    mime_keys = set(formats.MIME_HANDLERS)
    detection_keys = set(formats.DETECTION_HANDLERS)
    seen_mime, seen_detection = set(), set()

    print("=== per-sample gaps (emitted but not mapped) ===")
    for sample in iter_samples():
        mimes, detections = collect_for(sample)
        seen_mime |= mimes
        seen_detection |= detections

        mime_gaps = mimes - mime_keys
        detection_gaps = detections - detection_keys
        if mime_gaps or detection_gaps:
            print(f"[{os.path.relpath(sample, TEST_DIR)}]")
            for value in sorted(mime_gaps):
                print(f"   MIME gap     : {value}")
            for value in sorted(detection_gaps):
                print(f"   detect gap   : {value}")

    print("\n=== unused map keys (mapped but never emitted across samples) ===")
    for value in sorted(mime_keys - seen_mime):
        print(f"   unused MIME  : {value}")
    for value in sorted(detection_keys - seen_detection):
        print(f"   unused detect: {value}")


if __name__ == '__main__':
    main()
