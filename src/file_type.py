import puremagic
import logging
import subprocess
import os
import json
from trid_wrapper import TrIDLib

#####################################
# I could use these 3 detection methods:
#   * puremagic https://github.com/cdgriffith/puremagic
#   * TrID https://mark0.net/soft-trid-e.html
#   * DIE https://github.com/horsicq/Detect-It-Easy/
#####################################
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
        mime_types = {ptype.mime_type for ptype in possible_types if ptype.mime_type}

        logging.debug(f"Puremagic analysis: {mime_types}")  
        return mime_types if mime_types else None
    except Exception as exc:
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

def determine_file_type_with_trid(file_path, bin_path):
    """
    Uses TrID to analyze a file and extracts the description of the file type from the output.

    Args:
        file_path (str): The path to the .exe file to be analyzed.
        bin_path (str): The path to the bin_path folder.

    Returns:
        list: A list of descriptions of the file types identified by TrID, or None if an error occurs.
    """
    command = [os.path.join(bin_path, 'detectors', 'trid', 'trid.exe'), '-n:5', file_path]
    
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=True)
        
        # Extract descriptions from the output
        descriptions = []
        lines = result.stdout.strip().split('\n')
        
        # Parse each line that contains percentage and description
        for line in lines:
            if '%' in line:  # Check if the line contains a percentage which indicates a file type line
                description_without_percentage = " ".join(line.split()[2:])
                description = " ".join(description_without_percentage.split()[:-1])
                descriptions.append(description)

        logging.debug(f"TrID analysis: {descriptions}")
        return descriptions if descriptions else None
    except subprocess.CalledProcessError as exc:
        logging.error(f"TrID analysis failed for {file_path}: {exc}")
        return None

def determine_file_type_with_trid_dll(file_path, bin_path):
    """
    Uses the TrIDLib instance to analyze a file and extracts the most likely file type based on the analysis.
    This function initializes the TrIDLib with the correct DLL and definitions path, and then performs
    file type analysis based on TrID's ability to match file signatures against known definitions.

    Args:
        file_path (str): The path to the file to be analyzed.
        bin_path (str): The path to the directory containing the TrIDLib DLL and definitions.

    Returns:
        str: The most likely file type or extension based on TrIDLib analysis, or None if an error occurs.
    """
    # Construct paths to the TrID DLL and definitions file
    dll_path = os.path.join(bin_path, 'detectors', 'trid', 'TrIDLib.dll')
    definitions_path = os.path.join(bin_path, 'detectors', 'trid', 'triddefs.trd')

    # Create an instance of TrIDLib using the specified DLL path
    try:
        trid_lib = TrIDLib(dll_path)
        trid_lib.load_definitions(definitions_path)
    except Exception as exc:
        logging.error(f"Failed to initialize TrIDLib or load definitions: {exc}")
        return None

    # Submit the file for analysis
    if trid_lib.submit_file(file_path) != TrIDLib.TRID_OK:
        logging.error(f"Could not open or read file {file_path} for analysis.")
        return None

    # Perform the analysis
    if trid_lib.analyze() != TrIDLib.TRID_OK:
        logging.error(f"Analysis failed for {file_path}.")
        return None

    # Get the file type information; assuming '2' is the correct info type for getting file type descriptions
    file_type_description = trid_lib.get_info(TrIDLib.TRID_GET_RES_FILETYPE, 0)
    if file_type_description is not None and file_type_description != "":
        logging.info(f"Detected file type for {file_path}: {file_type_description}")
        return file_type_description
    else:
        logging.error(f"No file type information could be retrieved for {file_path}.")

    return None
