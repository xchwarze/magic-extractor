"""Command construction and subprocess streaming for the GUI (subprocess bridge to the CLI)."""
import os
import queue
import subprocess
import sys
import threading

EXE_NAME = "magic-extractor.exe"


def build_command(prefix, mode, source, dest, opts):
    """
    Build the full argv for one backend invocation.

    prefix : argv head (backend exe or ["python", main.py]).
    mode   : "extract", "scan", or "carve".
    source : input path.
    dest   : output dir (extract/carve); falsy -> CLI-derived.
    opts   : recursive/max_depth/bruteforce/password/fast_check/merge_output.
    """
    if mode == "scan":
        cmd = prefix + ["identify", source]
        if opts.get("fast_check", False):
            cmd.append("--fast-check")  # common arg, valid on identify too
        if opts.get("debug"):
            cmd.append("--debug")  # --debug is a common arg on every subcommand
        return cmd

    if mode == "carve":
        cmd = prefix + ["carve", source]
        if dest:
            cmd.append(dest)
        password = opts.get("password")
        if password:
            cmd.append(password_arg(password))
        if opts.get("fast_check", False):
            cmd.append("--fast-check")
        if opts.get("debug"):
            cmd.append("--debug")
        return cmd

    cmd = prefix + ["extract", source]
    if dest:
        cmd.append(dest)  # positional output_dir must precede flags

    password = opts.get("password")
    if password:
        cmd.append(password_arg(password))
    if opts.get("recursive"):
        cmd += ["-r", "--max-depth", str(opts.get("max_depth", 5))]
    if opts.get("bruteforce"):
        cmd.append("-b")
    if opts.get("delete_source"):
        cmd.append("--delete-source")
    if opts.get("merge_output"):
        cmd.append("--merge-output")
    if opts.get("fast_check", False):
        cmd.append("--fast-check")
    if opts.get("debug"):
        cmd.append("--debug")

    return cmd


def _src_root():
    # src/gui/runner.py -> src/ holds both packages (cli/ and gui/).
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _repo_root():
    # src/ -> the repository root, where VERSION lives.
    return os.path.dirname(_src_root())


def resolve_backend():
    """Locate the CLI backend. Frozen: sibling exe. Dev: python + src/cli/main.py."""
    if getattr(sys, "frozen", False):
        exe = os.path.join(os.path.dirname(sys.executable), EXE_NAME)
        if os.path.isfile(exe):
            return [exe]
        raise FileNotFoundError(f"Backend not found beside GUI: {exe}")

    main_py = os.path.join(_src_root(), "cli", "main.py")
    if os.path.isfile(main_py):
        return [sys.executable, main_py]
    raise FileNotFoundError(f"Backend not found: {main_py}")


def resolve_config_path():
    """config.ini (CLI extraction settings) beside the backend exe (frozen) or under src/cli/ (dev)."""
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "config.ini")
    return os.path.join(_src_root(), "cli", "config.ini")


def resolve_gui_config_path():
    """gui.ini (GUI-only settings) beside the GUI exe (frozen) or under src/gui/ (dev)."""
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "gui.ini")
    return os.path.join(_src_root(), "gui", "gui.ini")


def read_version():
    """
    App version, stamped into the repo-root VERSION file by the release build
    (dev checkouts keep whatever was last committed there).
    """
    path = (
        os.path.join(os.path.dirname(sys.executable), "VERSION")
        if getattr(sys, "frozen", False)
        else os.path.join(_repo_root(), "VERSION")
    )
    try:
        with open(path, encoding="utf-8") as version_fh:
            return version_fh.read().strip()
    except OSError:
        return "dev"


def display_command(argv):
    """argv for the log pane, with the password masked."""
    return ["--password=***" if arg.startswith("--password=") else arg for arg in argv]


def password_arg(password):
    """`--password=<pw>`: a separate argument starting with '-' (e.g. "-secret")
    would be read by argparse as an option and fail with "expected one argument"."""
    return f"--password={password}"


def kill_tree(process):
    """Kill the CLI and every extractor it started (terminate() alone left e.g.
    7z.exe running after Cancel)."""
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(process.pid)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    else:
        process.kill()


def run_streaming(argv, on_line, should_cancel, poll_seconds=0.2):
    """
    Run argv, streaming merged stdout+stderr line-by-line to on_line(str).
    should_cancel() is polled every poll_seconds, even while the process prints
    nothing (an extractor can be silent for minutes); on cancel the whole
    process tree is killed. Returns the exit code, or -1 if cancelled.
    """
    # CREATE_NO_WINDOW stops a console window from popping up for each child on
    # Windows when the GUI itself is windowed (--noconsole); 0 elsewhere.
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=creationflags,
    )
    lines = queue.Queue()

    def read_output():
        for line in iter(process.stdout.readline, ""):
            lines.put(line)
        lines.put(None)  # end of output

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    try:
        while True:
            if should_cancel():
                kill_tree(process)
                process.wait()
                return -1
            try:
                line = lines.get(timeout=poll_seconds)
            except queue.Empty:
                continue
            if line is None:
                break
            on_line(line.rstrip("\n"))
    finally:
        reader.join(timeout=1)
        process.stdout.close()
    return process.wait()
