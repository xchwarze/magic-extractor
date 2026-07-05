import puremagic
import logging
import subprocess
import os
import json

#####################################
# Detection methods used by the pipeline:
#   * puremagic (MIME)  https://github.com/cdgriffith/puremagic
#   * built-in signatures (data/signatures.json, generated from handler magic())
#   * DIE   https://github.com/horsicq/Detect-It-Easy/
#   * binwalk (offsets / short keys)
#   * Magika https://github.com/google/magika
#####################################

# Built-in magic-byte detector. Signatures come from data/signatures.json, which
# tools/generate_data.py builds from each handler's detection_signatures().
_SIGNATURES_CACHE = None
_SIGNATURES_READ_LEN = 4096

def _load_signatures(data_path):
    """Load and cache the compiled signatures from data/signatures.json."""
    global _SIGNATURES_CACHE, _SIGNATURES_READ_LEN
    if _SIGNATURES_CACHE is not None:
        return _SIGNATURES_CACHE

    _SIGNATURES_CACHE = []
    signatures_file = os.path.join(data_path, 'signatures.json')
    try:
        with open(signatures_file, encoding='utf-8') as sig_fh:
            raw = json.load(sig_fh)
    except (OSError, json.JSONDecodeError) as exc:
        logging.error(f"Failed to load signatures from {signatures_file}: {exc}")
        return _SIGNATURES_CACHE

    max_len = 0
    for entry in raw:
        patterns = []
        for pattern in entry.get('patterns', []):
            try:
                blob = bytes.fromhex(pattern['hex'])
            except (ValueError, KeyError, TypeError):
                continue
            pos = pattern.get('pos', 0)
            patterns.append((pos, blob))
            max_len = max(max_len, pos + len(blob))
        if patterns:
            _SIGNATURES_CACHE.append((entry['name'], patterns))

    _SIGNATURES_READ_LEN = max(max_len, 16)
    return _SIGNATURES_CACHE

def determine_file_type_with_signatures(file_path, bin_path=None):
    """
    Built-in magic-byte detector driven by data/signatures.json (harvested from
    the public TrID defs). Pure-python, no subprocess.

    Args:
        file_path (str): The path to the file to analyze.
        bin_path (str): Path to the 'bin' dir; data/ is resolved beside it.

    Returns:
        list: Matched detection names, or None.
    """
    data_path = os.path.join(os.path.dirname(bin_path), 'data') if bin_path else 'data'
    signatures = _load_signatures(data_path)
    if not signatures:
        return None

    try:
        with open(file_path, 'rb') as signature_fh:
            header = signature_fh.read(_SIGNATURES_READ_LEN)
    except OSError as exc:
        logging.error(f"Could not read {file_path} for signature detection: {exc}")
        return None

    names = []
    for name, patterns in signatures:
        if all(header[pos:pos + len(blob)] == blob for pos, blob in patterns) and name not in names:
            names.append(name)

    if names:
        logging.debug(f"Signature detection: {names}")
    return names or None

def determine_file_type_with_magic(file_path, fast_check=False):
    """
    Determines the MIME type of a file using content-based identification.

    Utilizes the puremagic library to analyze the content signatures of the file,
    optionally performing a fast check by reading only the initial 2048 bytes,
    or a full check by reading the entire file.
    
    Args:
        file_path (str): The path to the file whose MIME type is to be determined.
        fast_check (bool): If True, performs a quick check using only the first 2048 bytes of the file.
                       If False, analyzes the entire file for a more comprehensive detection.

    Returns:
        list: A set of unique MIME types found in the file, if any.
    """
    try:
        # Choose the method of analysis based on fast_check
        possible_types = puremagic.magic_string(open(file_path, "rb").read(2048)) if fast_check else puremagic.magic_file(file_path)
        
        # Create a set of MIME types, excluding empty strings and ensuring uniqueness
        #logging.debug(f"Puremagic all analysis: {possible_types}")
        mime_types = {ptype.mime_type for ptype in possible_types if ptype.mime_type}

        logging.debug(f"Puremagic analysis: {mime_types}")
        return mime_types if mime_types else None
    except Exception as exc:
        if str(exc) != "Could not identify file":
            logging.error(f"An error occurred while attempting to identify the magic number for this file: {exc}")

        return None

def determine_file_type_with_die(file_path, bin_path):
    """
    Uses DIE (Detect It Easy) to analyze a file and extracts detailed information about the file type.

    Args:
        file_path (str): The path to the file to be analyzed.
        bin_path (str): The path to the directory containing the DIE executable (diec.exe).

    Returns:
        list: A dictionary containing detailed information about the file, or None if an error occurs.
    """
    command = [os.path.join(bin_path, 'detectors', 'die', 'diec.exe'), '-j', file_path]
    
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=True)

        # Parse the JSON output
        die_output = json.loads(result.stdout)
        
        # Extract names for specific types
        relevant_types = {'Sfx', 'Archive', 'Installer'}
        names = []
        for detect in die_output.get('detects', []):
            for value in detect.get('values', []):
                if value.get('type') in relevant_types:
                    names.append(value.get('name'))

        #logging.error(f"DIE complete analysis: {die_output}")
        logging.debug(f"DIE analysis: {names}")
        return names if names else None
    except subprocess.CalledProcessError as exc:
        logging.error(f"DIE analysis failed for {file_path}: {exc}")
        return None
    except json.JSONDecodeError as exc:
        logging.error(f"Failed to parse DIE output as JSON for {file_path}: {exc}")
        return None

def determine_file_type_with_binwalk(file_path, bin_path):
    """
    Uses Binwalk to analyze a file and extracts embedded file type information in JSON format.

    Args:
        file_path (str): The path to the file to analyze.
        bin_path (str): The path to the directory containing the Binwalk executable.

    Returns:
        list: A list of dictionaries from Binwalk's JSON output, or None if an error occurs.
    """
    binwalk_exe = os.path.join(bin_path, 'detectors', 'binwalk', 'binwalk.exe')
    command = [binwalk_exe, '-q', '-l', '-', file_path]
    
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=True)
        binwalk_data = json.loads(result.stdout)

        names = []
        for item in binwalk_data:
            analysis = item.get("Analysis", {})
            for entry in analysis.get("file_map", []):
                name = entry.get("name")
                if name and name not in names:
                    names.append(name)

        logging.debug(f"Binwalk analysis: {names}")
        return names if names else None
    except subprocess.CalledProcessError as exc:
        logging.error(f"Binwalk analysis failed for {file_path}: {exc}")
        return None
    except json.JSONDecodeError as exc:
        logging.error(f"Failed to parse Binwalk JSON output for {file_path}: {exc}")
        return None

def binwalk_file_map(file_path, bin_path):
    """
    Return Binwalk's file_map entries for a file: a list of dicts with at least
    'offset', 'size' and 'name'. Used by the carve mode. Returns [] on error.
    """
    binwalk_exe = os.path.join(bin_path, 'detectors', 'binwalk', 'binwalk.exe')
    command = [binwalk_exe, '-q', '-l', '-', str(file_path)]

    try:
        result = subprocess.run(command, text=True, capture_output=True, check=True)
        binwalk_data = json.loads(result.stdout)

        entries = []
        for item in binwalk_data:
            entries.extend(item.get("Analysis", {}).get("file_map", []))
        return entries
    except subprocess.CalledProcessError as exc:
        logging.error(f"Binwalk analysis failed for {file_path}: {exc}")
        return []
    except json.JSONDecodeError as exc:
        logging.error(f"Failed to parse Binwalk JSON output for {file_path}: {exc}")
        return []

def determine_file_type_with_magika(file_path, bin_path):
    """
    Uses Magika (Google's AI content-type detector) to analyze a file.

    Args:
        file_path (str): The path to the file to analyze.
        bin_path (str): The path to the directory containing the Magika executable.

    Returns:
        dict: {"mime_types": [...], "labels": [...]} with the detected content types,
              or None if an error occurs or nothing is identified.
    """
    magika_exe = os.path.join(bin_path, 'detectors', 'magika', 'magika.exe')
    command = [magika_exe, '--json', file_path]

    try:
        result = subprocess.run(command, text=True, capture_output=True, check=True)
        magika_data = json.loads(result.stdout)

        mime_types = []
        labels = []
        for item in magika_data:
            entry = item.get("result", {})
            if entry.get("status") != "ok":
                continue

            output = entry.get("value", {}).get("output", {})
            mime_type = output.get("mime_type")
            label = output.get("label")
            if mime_type and mime_type not in mime_types:
                mime_types.append(mime_type)
            if label and label not in labels:
                labels.append(label)

        logging.debug(f"Magika analysis: mime={mime_types} labels={labels}")
        if not mime_types and not labels:
            return None

        return {"mime_types": mime_types, "labels": labels}
    except subprocess.CalledProcessError as exc:
        logging.error(f"Magika analysis failed for {file_path}: {exc}")
        return None
    except json.JSONDecodeError as exc:
        logging.error(f"Failed to parse Magika JSON output for {file_path}: {exc}")
        return None
