"""Command construction and subprocess streaming for the GUI (subprocess bridge to the CLI)."""
import os
import subprocess
import sys

EXE_NAME = "magic-extractor.exe"


def build_command(prefix, mode, source, dest, opts):
    """
    Build the full argv for one backend invocation.

    prefix : argv head (backend exe or ["python", main.py]).
    mode   : "extract" or "scan".
    source : input path.
    dest   : output dir (extract only); falsy -> omitted so the CLI derives it.
    opts   : recursive/max_depth/bruteforce/password/fast_check.
    """
    if mode == "scan":
        cmd = prefix + ["identify", source]
        if not opts.get("fast_check", True):
            cmd.append("--no-fast-check")  # common arg, valid on identify too
        if opts.get("debug"):
            cmd.append("--debug")  # --debug is a common arg on every subcommand
        return cmd

    cmd = prefix + ["extract", source]
    if dest:
        cmd.append(dest)  # positional output_dir must precede flags

    password = opts.get("password")
    if password:
        cmd += ["--password", password]
    if opts.get("recursive"):
        cmd += ["-r", "--max-depth", str(opts.get("max_depth", 5))]
    if opts.get("bruteforce"):
        cmd.append("-b")
    if opts.get("delete_source"):
        cmd.append("--delete-source")
    if not opts.get("fast_check", True):
        cmd.append("--no-fast-check")
    if opts.get("debug"):
        cmd.append("--debug")

    return cmd


def _repo_root():
    # gui/runner.py -> repo root is one directory up from gui/.
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_backend():
    """Locate the CLI backend. Frozen: sibling exe. Dev: python + cli/main.py."""
    if getattr(sys, "frozen", False):
        exe = os.path.join(os.path.dirname(sys.executable), EXE_NAME)
        if os.path.isfile(exe):
            return [exe]
        raise FileNotFoundError(f"Backend not found beside GUI: {exe}")

    main_py = os.path.join(_repo_root(), "cli", "main.py")
    if os.path.isfile(main_py):
        return [sys.executable, main_py]
    raise FileNotFoundError(f"Backend not found: {main_py}")


def resolve_config_path():
    """config.ini (CLI extraction settings) beside the backend exe (frozen) or under cli/ (dev)."""
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "config.ini")
    return os.path.join(_repo_root(), "cli", "config.ini")


def resolve_gui_config_path():
    """gui.ini (GUI-only settings) beside the GUI exe (frozen) or under gui/ (dev)."""
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "gui.ini")
    return os.path.join(_repo_root(), "gui", "gui.ini")


def run_streaming(argv, on_line, should_cancel):
    """
    Run argv, streaming merged stdout+stderr line-by-line to on_line(str).
    Polls should_cancel(); terminates the process if it returns True.
    Returns the process exit code (or -1 if cancelled).
    """
    # CREATE_NO_WINDOW stops a console window from popping up for each child on
    # Windows when the GUI itself is windowed (--noconsole); 0 elsewhere.
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        creationflags=creationflags,
    )
    try:
        for line in iter(process.stdout.readline, ""):
            if should_cancel():
                process.terminate()
                return -1
            on_line(line.rstrip("\n"))
    finally:
        process.stdout.close()
    return process.wait()
