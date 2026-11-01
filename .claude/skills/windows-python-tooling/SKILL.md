---
name: windows-python-tooling
description: >
  Use whenever creating, modifying, reviewing, or packaging Python tools that target Windows.
  Enforces robust Windows filesystem, subprocess, Unicode, configuration, frozen-build,
  error-handling, and compatibility practices for CLI and GUI tools.
---

# Windows Python Tooling

## Purpose

Produce reliable Python tools for Windows that behave correctly both from source and as frozen executables.

Apply this skill to:

- filesystem operations;
- subprocess execution;
- Windows paths;
- config/history files;
- Explorer integration;
- frozen builds;
- temp files;
- logging;
- Unicode;
- registry access;
- CLI/GUI shared backends.

---

# Baseline

Assume:

- Python 3.13.
- Windows is the primary target.
- Tools may have both CLI and Tkinter GUI entry points.
- PyInstaller may produce `--onefile` binaries.
- `sys.frozen` must be handled correctly.
- External dependencies may be optional.
- User-facing config/data should live outside PyInstaller's temporary extraction directory.

Do not introduce cross-platform abstractions that complicate Windows-only code without concrete value.

---

# Paths

Use `pathlib.Path` for application paths and filesystem operations.

Prefer:

```python
from pathlib import Path
```

Avoid manual string concatenation for paths.

Do not assume:

- current working directory equals executable directory;
- paths contain only ASCII;
- paths contain no spaces;
- file extensions use a specific case;
- a path fits legacy `MAX_PATH` assumptions.

Always distinguish:

- source/project directory;
- executable directory;
- temporary extraction directory;
- user-selected input/output paths.

For frozen apps, use `sys.executable` when locating files that live beside the executable.

Do not write persistent config beside `sys._MEIPASS`.

---

# Frozen execution

Code that depends on runtime location must explicitly handle frozen builds.

Use a small centralized helper for paths.

Typical distinction:

```python
if getattr(sys, "frozen", False):
    app_dir = Path(sys.executable).resolve().parent
else:
    app_dir = Path(__file__).resolve().parent
```

Do not scatter `sys.frozen` checks throughout the codebase.

Never assume `__file__` points beside the installed executable in a frozen build.

---

# Subprocesses

Use `subprocess.run()` or `subprocess.Popen()` with argument lists.

Prefer:

```python
subprocess.run(
    [str(executable), "--flag", str(path)],
    check=False,
)
```

Avoid building shell command strings manually.

Use `shell=True` only when Windows shell behavior is explicitly required.

When launching tools:

- preserve spaces in paths;
- preserve Unicode;
- capture output intentionally;
- choose text/binary mode explicitly;
- handle return codes;
- avoid deadlocks from unmanaged pipes.

Do not suppress stderr unless there is a concrete UX reason.

---

# Exit codes

CLI tools must return meaningful exit codes.

Recommended convention:

- `0`: success;
- non-zero: failure.

Do not treat printed error text as sufficient failure signaling.

Library/backend functions should normally raise exceptions or return structured results; the CLI entry point maps those outcomes to exit codes.

---

# Unicode

Assume filenames, arguments, stdout, stderr, registry values, and config values may contain Unicode.

Do not encode/decode manually unless interacting with a binary protocol or API that requires it.

Prefer Python `str` and Windows Unicode APIs.

Never assume cp1252.

---

# File writes

For important config/state files, prefer atomic replacement when practical.

Pattern:

1. write temporary file;
2. flush/close;
3. replace destination.

Use `encoding="utf-8"` explicitly for project-owned text files unless another format is required.

Do not silently overwrite user data unless the operation is explicitly destructive.

---

# Temporary files

Use `tempfile`.

Do not create random temp paths manually.

Ensure cleanup is deterministic when possible.

Do not place persistent state in temporary directories.

---

# Config and state

Separate:

- defaults;
- persisted GUI settings;
- history/state;
- runtime arguments.

Do not mix configuration parsing with UI code.

Centralize config I/O.

Config parsing must tolerate:

- missing files;
- malformed values;
- unknown keys;
- older config versions.

Prefer safe fallback behavior over startup failure for non-critical settings.

---

# Logging

Use `logging` for diagnostic information.

Do not scatter `print()` statements through backend code.

CLI output and logs are different concerns.

A GUI may redirect logs to a `Text` widget, file, stderr, or multiple handlers.

Avoid logging the same error repeatedly at several layers.

---

# Exceptions

Catch exceptions only where you can:

- recover;
- enrich context;
- convert to user-facing error state;
- map to exit codes;
- perform cleanup.

Do not use broad:

```python
except Exception:
    pass
```

unless there is a deliberate best-effort boundary and the failure is truly non-critical.

Best-effort Windows integration should fail quietly only when explicitly designed that way.

---

# Optional dependencies

Third-party integrations should degrade gracefully when optional.

Use guarded imports:

```python
try:
    import optional_dependency
except ImportError:
    optional_dependency = None
```

Do not let an optional visual/integration dependency prevent core functionality from starting.

Keep fallback behavior explicit and testable.

---

# Windows APIs

Use standard library modules first:

- `winreg`;
- `ctypes`;
- `subprocess`;
- `pathlib`.

Wrap Win32-specific code behind small functions/modules.

Do not leak raw Win32 constants and ctypes setup throughout unrelated code.

Check return values where the API exposes meaningful failure.

Use best-effort semantics only for cosmetic integrations.

---

# Registry

Registry operations must:

- use `winreg`;
- be scoped to the correct hive;
- avoid admin rights when user-level registration is sufficient;
- quote executable/path arguments correctly;
- support paths with spaces;
- remove only keys owned by the application.

Do not modify unrelated registry keys.

---

# Explorer integration

When building context-menu commands:

- quote executable paths;
- quote `%1` correctly;
- preserve Unicode;
- test paths containing spaces;
- avoid relying on current working directory.

Prefer user-level registration when possible.

---

# File associations and shell commands

Treat command-line quoting as a correctness issue.

Never build shell command strings by naive concatenation.

Test:

- executable path with spaces;
- input path with spaces;
- Unicode path;
- special characters where relevant.

---

# Architecture

Prefer this separation:

```text
cli.py / gui.py
      ↓
application/service layer
      ↓
backend/domain logic
      ↓
filesystem/process/platform adapters
```

Do not duplicate business logic between CLI and GUI.

The GUI and CLI should call the same backend operations.

---

# Threading and GUI integration

Never block the Tkinter main loop with long-running backend work.

Use worker threads/processes where appropriate.

UI updates must return to the Tk main thread.

Backend code must not depend on Tkinter.

---

# Performance

Do not optimize blindly.

For batch/file tools:

- avoid reading entire huge files when streaming works;
- avoid unnecessary copies;
- avoid repeated process launches;
- cache stable discovery results when useful.

Prefer correctness and observability over micro-optimizations.

---

# Security

Do not execute user-provided strings as shell commands.

Do not use `eval()` for config or data parsing.

Do not trust file extensions as proof of file type.

Validate destructive operations carefully.

Avoid writing to privileged directories unless explicitly required.

---

# Mandatory verification

Before completion, test all applicable cases:

- [ ] Source execution works.
- [ ] Frozen execution works.
- [ ] Input path with spaces works.
- [ ] Unicode path works.
- [ ] Missing config is handled.
- [ ] Invalid config falls back safely.
- [ ] External executable missing is handled.
- [ ] Non-zero subprocess exit is handled.
- [ ] CLI exit code is correct.
- [ ] GUI does not block on long work.
- [ ] Persistent files are written to the intended directory.
- [ ] Optional dependencies degrade gracefully.

If a case was not actually tested, state that explicitly.

---

# Review priorities

## Critical

- data loss;
- wrong file written/deleted;
- broken frozen execution;
- command injection;
- shell quoting bug;
- GUI deadlock/freeze;
- corrupted config/state.

## Important

- wrong exit code;
- bad path handling;
- Unicode issue;
- duplicated CLI/GUI backend logic;
- brittle `sys.frozen` behavior;
- swallowed errors.

## Minor

- inconsistent helper naming;
- duplicated path conversion;
- non-critical logging noise.

Fix Critical and Important issues before completion.

---

# Final rule

Prefer explicit Windows behavior, centralized platform handling, shared backend logic, and observable failure over convenience shortcuts.
