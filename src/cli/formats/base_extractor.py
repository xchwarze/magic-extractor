import os
import uuid
import shutil
import tempfile
import contextlib
import subprocess
import logging
import warnings

# Prefix of the per-attempt staging folders extract_atomically() creates.
STAGING_PREFIX = '.mx_staging_'


def default_output_dir(file_path):
    """<folder of the file>/<file name without extension>_extracted."""
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    return os.path.join(os.path.dirname(file_path), base_name + '_extracted')


def _free_name(path):
    """path, or "<stem> (n)<ext>" for the first n that does not exist yet."""
    stem, ext = os.path.splitext(path)
    counter = 1
    while os.path.exists(path):
        path = f"{stem} ({counter}){ext}"
        counter += 1
    return path


def _same_path(first, second):
    return os.path.normcase(os.path.abspath(first)) == os.path.normcase(os.path.abspath(second))


def merge_move(source, destination, protect=None):
    """
    Move source to destination and return the path it ended up at. Folders are
    merged and a file replaces a file (like an extractor's overwrite-all), but
    a file never replaces a folder or the other way round, and nothing ever
    replaces ``protect`` (the archive being extracted, when it sits in the
    output folder): the incoming one gets a free "<name> (n)" instead.
    """
    if os.path.isdir(source) and os.path.isdir(destination):
        for name in os.listdir(source):
            merge_move(os.path.join(source, name), os.path.join(destination, name), protect)
        os.rmdir(source)
        return destination
    if os.path.exists(destination):
        if (os.path.isdir(source) != os.path.isdir(destination)
                or (protect is not None and _same_path(destination, protect))):
            destination = _free_name(destination)
        else:
            os.remove(destination)
    shutil.move(source, destination)
    return destination


def staging_owner_pid(name):
    """PID encoded in a staging folder name (.mx_staging_<pid>_<uuid>), or None."""
    if not name.startswith(STAGING_PREFIX):
        return None
    pid = name[len(STAGING_PREFIX):].split('_', 1)[0]
    return int(pid) if pid.isdigit() else None


def pid_alive(pid):
    """Whether a process with this PID is running (never signals it)."""
    if os.name == 'nt':
        import ctypes
        process_query_limited_information, still_active = 0x1000, 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == still_active
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def remove_stale_staging(folder):
    """
    Remove staging folders left by a run that was killed (e.g. GUI Cancel:
    taskkill skips the cleanup), i.e. whose owner process is gone. Folders of
    a run still in progress (or of an unknown owner) are kept.
    """
    try:
        names = os.listdir(folder)
    except OSError:
        return
    for name in names:
        pid = staging_owner_pid(name)
        if pid is None or pid == os.getpid() or pid_alive(pid):
            continue
        logging.info(f"Removing leftover staging folder of an interrupted run: {name}")
        shutil.rmtree(os.path.join(folder, name), ignore_errors=True)


def _is_ascii(text):
    return all(ord(char) < 128 for char in text)


def _short_folder(folder):
    """The 8.3 form of an existing folder (Windows), or the folder unchanged."""
    if os.name != 'nt':
        return folder
    import ctypes
    buffer = ctypes.create_unicode_buffer(32768)
    if ctypes.windll.kernel32.GetShortPathNameW(folder, buffer, len(buffer)):
        return buffer.value
    return folder


@contextlib.contextmanager
def ascii_path(path):
    """
    Yield a pure-ASCII path to the existing file `path`, for old tools that
    only take ANSI command lines (unace, uharc fail on e.g. "архив.ace").

    A non-ASCII path becomes a hard link (or, across volumes, a copy) with an
    ASCII name in a temporary folder, removed afterwards. The file's own 8.3
    short name is not enough: those tools resolve it back to the long name
    through the ANSI API and then cannot open it; a short *folder* is fine.
    """
    path = os.path.abspath(path)
    if _is_ascii(path):
        yield path
        return
    work_dir = tempfile.mkdtemp(prefix='mx_ascii_')
    try:
        extension = os.path.splitext(path)[1]
        name = 'source' + (extension if _is_ascii(extension) else '')
        link = os.path.join(work_dir, name)
        try:
            os.link(path, link)
        except OSError:
            shutil.copy2(path, link)
        safe = os.path.join(_short_folder(work_dir), name)
        if not _is_ascii(safe):
            logging.warning(f"No ASCII path available for an ANSI-only tool: {safe}")
        logging.debug(f"Using an ASCII-named link for an ANSI-only tool: {safe}")
        yield safe
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


@contextlib.contextmanager
def ascii_folder(folder):
    """
    Yield a pure-ASCII path to write into instead of the existing `folder`,
    for old tools that work in their current directory through the ANSI API
    (unace extracts nothing when it is e.g. "выход"): the folder itself if
    ASCII, else its 8.3 short form, else a temporary ASCII folder whose
    content is moved into `folder` afterwards.
    """
    folder = os.path.abspath(folder)
    if _is_ascii(folder):
        yield folder
        return
    short = _short_folder(folder)
    if _is_ascii(short):
        yield short
        return
    work_dir = tempfile.mkdtemp(prefix='mx_ascii_out_')
    try:
        yield work_dir
        for name in os.listdir(work_dir):
            merge_move(os.path.join(work_dir, name), os.path.join(folder, name))
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


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
        # Top-level names the last extract_atomically() put in the output folder
        # (None: unknown, e.g. extract() called directly). Post-processing and
        # recursion only look at these, never at what was already there.
        self.extracted_names = None

    def extract(self):
        """
        Method to extract files. Must be overridden by specific extractor implementations.
        """
        raise NotImplementedError("Each subclass must implement the 'extract' method.")

    def extract_atomically(self):
        """
        Run extract() in a fresh, empty staging folder created for this attempt
        inside the output folder, and move what it extracted into the output
        folder only if it succeeded. A failed attempt is discarded whole, so it
        never leaves partial output behind for the next candidate, and every
        tool works in the same context (a new empty folder) whatever it does
        with existing folders. A tool that reports success but extracted
        nothing counts as a failure.

        Returns:
            bool: True if the extraction succeeded and was moved into place.
        """
        final_dir = self.extract_directory
        # <pid> lets a later run recognise and remove it if this one gets killed.
        staging = os.path.join(final_dir, f'{STAGING_PREFIX}{os.getpid()}_{uuid.uuid4().hex}')
        os.makedirs(staging)
        self.extract_directory = staging
        try:
            if not self.extract():
                return False
            extracted = os.listdir(staging)
            if not extracted:
                logging.error(f"{type(self).__name__} reported success but extracted nothing")
                return False
            self.extracted_names = [
                os.path.basename(merge_move(os.path.join(staging, name), os.path.join(final_dir, name),
                                            protect=self.target_file))
                for name in extracted
            ]
            return True
        except OSError as exc:
            logging.error(f"{type(self).__name__}: could not move the extracted files into place: {exc}")
            return False
        finally:
            self.extract_directory = final_dir
            shutil.rmtree(staging, ignore_errors=True)

    def iter_extracted(self):
        """
        Yield (path, is_dir) for every file and folder this extraction produced:
        only the names extract_atomically() moved in, recursively, never other
        content of a shared output folder (--merge-output).
        """
        names = self.extracted_names
        if names is None:
            names = os.listdir(self.extract_directory)
        for name in names:
            top = os.path.join(self.extract_directory, name)
            if not os.path.isdir(top):
                if os.path.exists(top):
                    yield top, False
                continue
            yield top, True
            for folder, dirs, files in os.walk(top):
                for sub_name in dirs:
                    yield os.path.join(folder, sub_name), True
                for sub_name in files:
                    yield os.path.join(folder, sub_name), False

    def extracted_files(self):
        """Paths of the files this extraction produced (see iter_extracted)."""
        return [path for path, is_dir in self.iter_extracted() if not is_dir]

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
        """Give extensionless extracted files a content-based extension.

        Only files that have no extension are named (a carved/opaque blob whose
        type puremagic recognizes). Files that already carry an extension are left
        alone — overwriting one would break e.g. .docx/.jar/.tar.gz, which are
        containers puremagic reports as .zip/.gz.
        """
        try:
            import puremagic
        except ImportError:
            logging.error("puremagic not available; cannot fix file extensions")
            return

        for path in self.extracted_files():
            name = os.path.basename(path)
            # only name files that LACK an extension; never overwrite a real
            # one (renaming e.g. .docx/.jar -> .zip would break the file)
            if os.path.splitext(name)[1]:
                continue
            try:
                # puremagic's python_scanner ast.parse()s candidate .py content to
                # confirm it's real Python; that surfaces SyntaxWarnings for whatever
                # the EXTRACTED (third-party) file itself does with backslashes, not
                # anything of ours — parsing still succeeds, so it's just noise here.
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", SyntaxWarning)
                    guessed_ext = puremagic.from_file(path)
            except Exception:
                continue  # unknown / unreadable content, leave as is

            if not guessed_ext:
                continue
            new_path = path + guessed_ext
            if os.path.exists(new_path):
                continue  # don't clobber an existing file
            try:
                os.rename(path, new_path)
                logging.info(f"Fixed extension: {name} -> {os.path.basename(new_path)}")
            except OSError as exc:
                logging.error(f"Failed to rename {path}: {exc}")

    def warn_non_ascii_names(self):
        """Warn about extracted names that are not plain ASCII (portability hazard)."""
        for path, _is_dir in self.iter_extracted():
            try:
                os.path.basename(path).encode('ascii')
            except UnicodeEncodeError:
                logging.warning(f"Non-ASCII name in output: {path}")

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
            output_dir = default_output_dir(self.cli_args.file_path)
            logging.debug(f"No output directory provided. Using default: {output_dir}")

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if not os.access(output_dir, os.W_OK):
            logging.error(f"Output directory {output_dir} is not writable")
            raise PermissionError(f"Output directory {output_dir} is not writable")

        logging.debug(f"Output directory {output_dir} is validated and ready.")
        return str(os.path.abspath(output_dir))

    def run_command(self, command, workdir=None, timeout=None):
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
            # errors='replace': a tool printing bytes the console code page can't
            # decode must not turn a successful extraction into a failure.
            # stdin closed: a tool that prompts (e.g. for a missing password)
            # fails at once instead of waiting forever on a hidden prompt.
            result = subprocess.run(command, cwd=workdir, text=True, errors='replace',
                                    capture_output=True, check=True, env=os.environ,
                                    stdin=subprocess.DEVNULL, timeout=timeout)

            logging.debug(f"Command executed successfully with output: {result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as error:
            logging.error(f"Command failed with {error.returncode}: {error.stderr}")
            raise  # Re-raise the exception to be handled by the caller

    def run_extraction(self, command, workdir=None, label=None, failure_markers=(), timeout=None):
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
            timeout (float): seconds before the tool is killed (None: no limit),
                         for tools that can block on a modal error dialog.
            failure_markers (iterable): stdout texts that mean failure even with
                         exit code 0. Some tools (unace, kgb2_console) exit 0
                         on a file they cannot open; without this the handler
                         reports success with nothing extracted and the next
                         candidate never runs.

        Returns:
            bool: True on success, False on failure.
        """
        label = label or type(self).__name__
        try:
            output = self.run_command(command, workdir=workdir, timeout=timeout) or ''
            for marker in failure_markers:
                if marker in output:
                    logging.error(f"{label}: extraction failed: {marker}")
                    return False
            return True
        except subprocess.CalledProcessError as exc:
            logging.error(f"{label}: extraction failed (exit {exc.returncode}): {exc.stderr}")
            return False
        except subprocess.TimeoutExpired:
            logging.error(f"{label}: killed after {timeout:.0f}s without finishing")
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

    def run_listing(self, command, label=None, failure_markers=()):
        """
        Run a listing command and return its stdout, or None on failure.

        Same failure rules as run_extraction (non-zero exit, unrunnable tool,
        or a failure marker in stdout), for handlers whose list_contents() is
        a single command.
        """
        label = label or type(self).__name__
        try:
            output = self.run_command(command) or ''
        except subprocess.CalledProcessError as exc:
            logging.error(f"{label}: listing failed (exit {exc.returncode}): {exc.stderr}")
            return None
        except Exception as exc:
            logging.error(f"{label}: could not run lister: {exc}")
            return None
        for marker in failure_markers:
            if marker in output:
                logging.error(f"{label}: listing failed: {marker}")
                return None
        return output

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
