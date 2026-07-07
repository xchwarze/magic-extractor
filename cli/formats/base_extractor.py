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
    # Rough multiplier applied to the archive size to estimate extracted size.
    FREE_SPACE_FACTOR = 3

    # --- Detection scope --------------------------------------------------
    # Each handler declares the indicators that route files to it. A generator
    # (tools/generate_data.py) collects these into data/handlers.json and
    # data/signatures.json. Override in subclasses.

    @classmethod
    def detection_mimes(cls):
        """MIME types (from puremagic / Magika) that route to this handler."""
        return []

    @classmethod
    def detection_names(cls):
        """Detector strings (from DIE / binwalk / Magika) that route to this handler."""
        return []

    @classmethod
    def detection_signatures(cls):
        """
        Custom magic-byte signatures for formats the engines miss. Each entry:
        {'name': <detection name>, 'patterns': [{'pos': int, 'hex': str}, ...]}.
        The name is auto-added to detection_names by the generator.
        """
        return []

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

    def list_contents(self):
        """
        List the archive contents without extracting. Returns a listing string,
        or None if this handler does not support listing.
        """
        logging.info(f"Listing is not supported by {type(self).__name__}.")
        return None

    def pre_extract_actions(self):
        """
        Perform any necessary actions before starting the extraction process.
        This method is implemented in subclasses to handle tasks such as setting up temporary directories,
        validating input files, or logging initial extraction details.
        Subclasses should ensure that all prerequisites for extraction are met before proceeding.
        """
        # Validate and prepare the output directory
        self.extract_directory = self.validate_output_directory()

        if getattr(self.cli_args, 'check_free_space', False):
            self.ensure_free_space()

    def ensure_free_space(self):
        """Warn if the output volume likely lacks room for the extraction."""
        try:
            required = os.path.getsize(self.target_file) * self.FREE_SPACE_FACTOR
        except OSError as exc:
            logging.error(f"Could not size {self.target_file} for free-space check: {exc}")
            return

        if not self.has_free_space(self.extract_directory, required):
            logging.warning(f"May lack free space (need ~{required} bytes) in {self.extract_directory}")

    def post_extract_actions(self):
        """
        Conduct any required actions after the extraction process completes.
        This method can be implemented optionally in subclasses to perform clean-up, validation of extracted data,
        or to move files to a final destination. It could also handle error checking and compilation of extraction logs.
        This method is optional and may contain minimal or no implementation depending on specific subclass requirements.
        """
        if getattr(self.cli_args, 'fix_file_extensions', False):
            self.fix_extensions()
        if getattr(self.cli_args, 'check_unicode', False):
            self.warn_non_ascii_names()
        if getattr(self.cli_args, 'create_log_files', False):
            self.write_log_file()
        if getattr(self.cli_args, 'open_output_folder', False):
            self.open_output_folder()

    def fix_extensions(self):
        """Rename extracted files whose detected content type disagrees with their extension."""
        try:
            import puremagic
        except ImportError:
            logging.error("puremagic not available; cannot fix file extensions")
            return

        for root, _dirs, files in os.walk(self.extract_directory):
            for name in files:
                path = os.path.join(root, name)
                try:
                    guessed_ext = puremagic.from_file(path)
                except Exception:
                    continue  # unknown / unreadable content, leave as is

                if not guessed_ext:
                    continue
                current_ext = os.path.splitext(name)[1].lower()
                if guessed_ext.lower() == current_ext:
                    continue

                new_path = os.path.splitext(path)[0] + guessed_ext
                if os.path.exists(new_path):
                    continue  # don't clobber an existing file
                try:
                    os.rename(path, new_path)
                    logging.info(f"Fixed extension: {name} -> {os.path.basename(new_path)}")
                except OSError as exc:
                    logging.error(f"Failed to rename {path}: {exc}")

    def warn_non_ascii_names(self):
        """Warn about extracted names that are not plain ASCII (portability hazard)."""
        for root, dirs, files in os.walk(self.extract_directory):
            for name in dirs + files:
                try:
                    name.encode('ascii')
                except UnicodeEncodeError:
                    logging.warning(f"Non-ASCII name in output: {os.path.join(root, name)}")

    def write_log_file(self):
        """Write a small per-run log of the extraction to the output directory."""
        log_path = os.path.join(self.extract_directory, 'magic-extractor.log')
        try:
            with open(log_path, 'w', encoding='utf-8') as log_fh:
                log_fh.write(f"Source : {self.target_file}\n")
                log_fh.write(f"Handler: {type(self).__name__}\n")
                log_fh.write(f"Output : {self.extract_directory}\n")
        except OSError as exc:
            logging.error(f"Failed to write log file {log_path}: {exc}")

    def open_output_folder(self):
        """Open the output directory in the system file manager."""
        try:
            if hasattr(os, 'startfile'):
                os.startfile(self.extract_directory)  # Windows
            else:
                subprocess.run(['xdg-open', self.extract_directory], check=False)
        except Exception as exc:
            logging.error(f"Failed to open output folder {self.extract_directory}: {exc}")

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

    def run_extraction(self, command, workdir=None, label=None):
        """
        Run an extractor command and reduce its result to a bool.

        Success is a zero exit code (run_command returns normally); a non-zero
        exit raises CalledProcessError and a missing/unrunnable binary raises
        OSError — both are reported and mapped to False. Handlers whose extract()
        is a single command should `return self.run_extraction(cmd)` instead of
        repeating the try/except boilerplate. Handlers that need to do more on
        success (post-processing) or try several binaries keep their own logic.

        Args:
            command (list): The command to execute.
            workdir (str): Directory in which to run it.
            label (str): Human-readable tool/format name for the error log
                         (defaults to the handler class name).

        Returns:
            bool: True on success, False on failure.
        """
        label = label or type(self).__name__
        try:
            self.run_command(command, workdir=workdir)
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"{label}: extraction failed (exit {exc.returncode}): {exc.stderr}")
            return False
        except OSError as exc:
            logging.error(f"{label}: could not run extractor: {exc}")
            return False
        except Exception as exc:
            # Parity with the old per-handler `except Exception` net: e.g. a tool
            # emitting bytes the console codec can't decode makes subprocess.run
            # raise UnicodeDecodeError (a ValueError). Don't crash the whole run.
            logging.error(f"{label}: unexpected error running extractor: {exc}")
            return False

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
            free_space = shutil.disk_usage(path).free
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
