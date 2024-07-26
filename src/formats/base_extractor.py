import os
import shutil
import subprocess
import logging

class BaseExtractor:
    """
    Base class for all format-specific extractors.
    Includes common utility methods used across all extractors and utilizes the global logging instance.
    """

    # Common constants
    TOOL_FOLDER = 'extractors'

    def __init__(self, cli_args, bin_path):
        """
        Initialize the extractor with command-line arguments and the binary tools directory.
        
        Args:
            cli_args (Namespace): Command-line arguments containing configuration and debug settings.
            bin_path (str): Path to the directory containing binary tools.
        """
        self.cli_args = cli_args
        self.extractors_path = os.path.join(bin_path, self.TOOL_FOLDER)
        self.target_file = str(os.path.abspath(cli_args.file_path))
        self.extract_directory = None

    def extract(self):
        """
        Method to extract files. Must be overridden by specific extractor implementations.
        """
        raise NotImplementedError("Each subclass must implement the 'extract' method.")

    def pre_extract_actions(self):
        """
        Perform any necessary actions before starting the extraction process.
        This method is implemented in subclasses to handle tasks such as setting up temporary directories,
        validating input files, or logging initial extraction details.
        Subclasses should ensure that all prerequisites for extraction are met before proceeding.
        """
        # Validate and prepare the output directory
        self.extract_directory = self.validate_output_directory()

    def post_extract_actions(self):
        """
        Conduct any required actions after the extraction process completes.
        This method can be implemented optionally in subclasses to perform clean-up, validation of extracted data,
        or to move files to a final destination. It could also handle error checking and compilation of extraction logs.
        This method is optional and may contain minimal or no implementation depending on specific subclass requirements.
        """
        pass  # Optional implementation by subclasses

    def validate_output_directory(self):
        """
        Validates if the specified output directory exists and is writable. If no directory is provided,
        it creates a default one based on the input file's name from cli_args.
        """
        output_dir = self.cli_args.output_dir

        if output_dir is None:
            file_path = self.cli_args.file_path
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_dir = os.path.join(os.path.dirname(file_path), base_name + '_extracted')
            logging.debug(f"No output directory provided. Using default: {output_dir}")

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if not os.access(output_dir, os.W_OK):
            logging.error(f"Output directory {output_dir} is not writable")
            raise PermissionError(f"Output directory {output_dir} is not writable")

        logging.debug(f"Output directory {output_dir} is validated and ready.")
        return str(os.path.abspath(output_dir))

    def run_command(self, command, workdir=None):
        """
        Execute a system command in a subprocess and return the output.
        Raises an exception if the command fails.

        Args:
        command (list): List of command strings to be executed.
        workdir (str): Directory in which to execute the command.
        
        Returns:
        str: The stdout from the command execution.

        Raises:
        subprocess.CalledProcessError: If the command fails.
        """
        try:
            logging.debug(f"Executing command: {' '.join(command)} in {workdir}")
            result = subprocess.run(command, cwd=workdir, text=True, capture_output=True, check=True, env=os.environ)

            logging.debug(f"Command executed successfully with output: {result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as error:
            logging.error(f"Command failed with {error.returncode}: {error.stderr}")
            raise  # Re-raise the exception to be handled by the caller

    def clean_up_directory(self, path, remove_dir=False):
        """
        Remove all files and directories within the specified directory.
        
        Args:
        path (str): Path to the directory to clean up.
        remove_dir (bool): Whether to remove the directory itself after cleaning up its contents.
        """
        logging.debug(f"Cleaned up directory {path}")
        shutil.rmtree(path)            
        if not remove_dir:
            os.makedirs(path)

    def has_free_space(self, path, required_space):
        """
        Check if there is enough disk space available at the specified path.
        
        Args:
        path (str): The path where disk space is to be checked.
        required_space (int): The minimum required free space in bytes.

        Returns:
        bool: True if there is enough space, False otherwise.
        """
        try:
            statvfs = os.statvfs(path)
            free_space = statvfs.f_frsize * statvfs.f_bavail
            if free_space > required_space:
                logging.debug(f"Sufficient disk space available: {free_space} bytes available in {path}.")
                return True
            else:
                logging.warning(f"Insufficient disk space: {free_space} bytes available, but {required_space} bytes needed in {path}.")
                return False
        except Exception as exc:
            logging.error(f"Failed to check disk space in {path}: {exc}")
            return False

    def move_files(self, source_directory, destination_directory):
        """
        Move files from source directory to destination directory, handling both files and directories.

        Args:
        source_directory (str): Source directory path.
        destination_directory (str): Destination directory path.
        """
        try:
            for item in os.listdir(source_directory):
                source_path = os.path.join(source_directory, item)
                destination_path = os.path.join(destination_directory, item)
                if os.path.isdir(source_path):
                    shutil.move(source_path, destination_path)
                    logging.debug(f"Directory moved from {source_path} to {destination_path}")
                else:
                    shutil.copy2(source_path, destination_path)
                    logging.debug(f"File moved from {source_path} to {destination_path}")
        except Exception as exc:
            logging.error(f"Error moving files from {source_directory} to {destination_directory}: {exc}")

    def delete_temp_files(self, directory_path):
        """
        Clean up temporary files in a specified directory.

        Args:
        directory_path (str): Path to the directory where files and subdirectories will be deleted.
        """
        try:
            for root, dirs, files in os.walk(directory_path, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    os.remove(file_path)
                    logging.debug(f"Deleted file: {file_path}")
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    os.rmdir(dir_path)
                    logging.debug(f"Deleted directory: {dir_path}")
        except Exception as exc:
            logging.error(f"Failed to delete temporary files in {directory_path}: {exc}")
