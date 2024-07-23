import os
import subprocess
import logging
from extractor import BaseExtractor

class ExeHandler(BaseExtractor):
    """
    Handler class for .exe files that utilizes TrID for analysis.
    """

    # Common constants
    TOOL_FOLDER = 'TrID'

    def extract(self):
        """
        Uses TrID to analyze .exe files and logs the most probable file type.

        Returns:
        bool: True if the analysis was successful, False otherwise.
        """
        # Construct the full path to the file
        file_path = str(os.path.abspath(self.cli_args.file_path))

        # Validate and prepare the output directory (not actually needed for analysis, but for consistency)
        extract_directory = self.validate_output_directory()

        # Construct the command to execute using the path to TrID executable
        command_list = [
            os.path.join(self.bin_path, self.TOOL_FOLDER, 'trid.exe'),
            '-n:1',   # Only show the most probable result
            file_path
        ]

        # Running the command using the base class utility method
        try:
            output = self.run_command(command_list)
            if output:
                # Log the last line of the output, which contains the most probable file type
                last_line = output.strip().split('\n')[-1]
                logging.info(f"TrID analysis completed: '{last_line}'")
                return True
            else:
                logging.error("Failed to analyze .exe file with no output.")
                return False
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to analyze .exe file with error code {e.returncode}")
            return False
        except Exception as e:
            logging.error(f"An error occurred during .exe file analysis: {e}")
            return False

        # Optionally clean up if necessary (not typically required for analysis)
        self.clean_up_directory(extract_directory, remove_dir=True)

# Usage example within main or similar context
if __name__ == "__main__":
    # Assume cli_args and bin_path are defined elsewhere
    handler = ExeHandler(cli_args, bin_path)
    success = handler.extract()
    if success:
        logging.info("Analysis of .exe completed successfully.")
    else:
        logging.error("Analysis of .exe failed.")
