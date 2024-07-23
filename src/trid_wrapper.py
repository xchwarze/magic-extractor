import ctypes
import logging
import struct
import sys

class TrIDLib:
    # Constants for API methods results
    SUCCESS = -1
    FAILURE = 0

    # Constants for TrID_GetInfo
    RES_NUM = 1
    RES_FILETYPE = 2
    RES_FILEEXT = 3
    RES_POINTS = 4

    def __init__(self, dll_path):
        """
        Initialize the TrIDLib wrapper and load the DLL.
        
        Args:
            dll_path (str): The path to the TrIDLib DLL.
        
        Raises:
            OSError: If the DLL cannot be loaded.
            EnvironmentError: If the system architecture is not compatible.
        """
        if struct.calcsize("P") * 8 != 32:
            logging.error("TrIDLib requires a 32-bit Python interpreter")
            raise EnvironmentError("TrIDLib requires a 32-bit Python interpreter")
        
        try:
            self.trid = ctypes.CDLL(dll_path)
        except OSError as e:
            logging.error(f"Failed to load TrIDLib DLL from {dll_path}: {e}")
            raise

    def load_definitions(self, path):
        """
        Load the file type definitions from a specified path.
        
        Args:
            path (str): The path to the definitions file.
        
        Returns:
            int: The number of definitions loaded, or -1 if there was an error.
        """
        self.trid.TrID_LoadDefsPack.argtypes = [ctypes.c_char_p]
        self.trid.TrID_LoadDefsPack.restype = ctypes.c_int
        result = self.trid.TrID_LoadDefsPack(path.encode('utf-8'))
        if result == self.FAILURE:
            logging.warning(f"No definitions were loaded from {path}")
        return result

    def submit_file(self, filename):
        """
        Submit a file to be analyzed by TrID.
        
        Args:
            filename (str): The path to the file to analyze.
        
        Returns:
            bool: True if the file was successfully submitted, False otherwise.
        """
        self.trid.TrID_SubmitFileA.argtypes = [ctypes.c_char_p]
        self.trid.TrID_SubmitFileA.restype = ctypes.c_int
        result = self.trid.TrID_SubmitFileA(filename.encode('utf-8'))
        return result == self.SUCCESS

    def analyze(self):
        """
        Perform the file type analysis on the previously submitted file.
        
        Returns:
            bool: True if analysis was successful, False otherwise.
        """
        self.trid.TrID_Analyze.restype = ctypes.c_int
        result = self.trid.TrID_Analyze()
        return result == self.SUCCESS

    def get_info(self, info_type, info_idx):
        """
        Get various kinds of information or results.
        
        Args:
            info_type (int): The type of information requested.
            info_idx (int): The index for certain types of information.
        
        Returns:
            str or int: The information requested, depending on the type.
        """
        trid_res = ctypes.create_string_buffer(4096)
        self.trid.TrID_GetInfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p]
        self.trid.TrID_GetInfo.restype = ctypes.c_int
        result = self.trid.TrID_GetInfo(info_type, info_idx, trid_res)
        return trid_res.value.decode('utf-8') if result > 0 else None
