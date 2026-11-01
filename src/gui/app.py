"""Universal-Extractor-style Tk window that drives the magic-extractor CLI."""
import logging
import os
import queue
import subprocess
import sys
import threading
import webbrowser
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

from gui import runner, config_io, theme, paths, history, context_menu, option_warnings, icons
from gui.icons.catalog import COMPACT, DISABLED, NORMAL
from gui import logging_setup
from gui.log_pane import LogPane, copy_to_clipboard, save_text
from gui.menu_popup import ICON_GAP, Item, show_context_menu
from gui.settings import GuiSettings
from gui.menubar import MenuBar
from gui.status import StatusLine, job_status, run_summary, source_name
from gui.tooltip import Tooltip

# CLI config.ini flags surfaced in Preferences, with human-readable labels.
CONFIG_LABELS = {
    "open_output_folder": "Open the output folder when finished",
    "check_free_space": "Check free disk space before extracting",
    "check_unicode": "Warn about non-ASCII characters in file names",
    "fix_file_extensions": "Fix wrong file extensions automatically",
    "create_log_files": "Write a magic-extractor.log in the output folder",
    "delete_to_recycle_bin": "Send deleted sources to the Recycle Bin (not permanent)",
}
CONFIG_KEYS = list(CONFIG_LABELS)

# gui.ini interface toggles surfaced in Preferences.
GUI_LABELS = {
    "auto_fill_destination": "Auto-fill the destination from the source file",
    "keep_open": "Keep the window open after a run finishes",
    "always_on_top": "Keep the window always on top",
    "debug": "Verbose debug logging (adds --debug to every command)",
    "history_enabled": "Remember the last 10 source/destination paths",
}

LOG_FILENAME = "magic-extractor.log"
WARNING_SIGN = "\u26a0"  # shown at the start of an option's warning alert
LOG_PLACEHOLDER = "Ready. Extraction and detection output will appear here."
LOCK_TIP = ("Lock the destination: it is not filled in from the source, and files are extracted into it "
            "even when it already has content (files with the same name are overwritten).")
BATCH_TIP = ("With a source filled in: adds it to the batch queue.\n"
             "With the source empty: runs the queued files.\n"
             "With the source empty and nothing queued: asks for several files and runs them. (Ctrl+B)")


class ExtractorApp:
    def __init__(self, root, initial_source=None, initial_dest=None, initial_mode=None):
        self.root = root
        self.root.title("Magic Extractor")
        # Stay hidden until geometry from gui.ini is applied, so the window does
        # not first paint at the default spot and then jump to its saved position.
        self.root.withdraw()
        self.log_queue = queue.Queue()
        # The worker thread never touches Tk: it posts lines to log_queue and
        # its final result here; _drain_log (main thread) picks both up. job_queue
        # carries what each job is doing ("start") and how it ended ("exit") for the status line.
        self.done_queue = queue.Queue()
        self.job_queue = queue.Queue()
        self._run_total = 0
        self._run_results = []  # (mode, source, exit code) of the jobs of this run that ended
        self._running = False
        self.worker = None
        self.cancel_flag = threading.Event()
        self.batch_queue = []  # list of (mode, source, dest)

        # Persisted GUI settings (gui.ini).
        self.settings = GuiSettings(runner.resolve_gui_config_path())
        self._theme_forced = False
        self._load_settings()

        # Command-line arguments win over persisted defaults.
        if initial_mode:
            self.mode.set(initial_mode)
        if initial_source:
            self.source.set(initial_source)
        if initial_dest:
            self.dest.set(initial_dest)

        self.icons = icons.ButtonIcons(self.root)
        self._build_menu()
        self._build_body()
        theme.apply(self.root, self.theme_mode)
        theme.scale_theme_fonts(self.root)  # sv-ttk fonts follow the display scaling
        self.log_pane.restyle(self.theme_mode)
        self.menubar.recolor(self.theme_mode)
        self._enable_dnd()
        self._apply_window_prefs()

        # Auto-fill the destination as the source is typed/changed.
        self.source.trace_add("write", lambda *a: self._autofill(force=False))
        if initial_source and not initial_dest:
            self._autofill(force=True)

        self._bind_keys()
        # Tk prints a failing callback to a stderr the windowed exe does not have.
        self.root.report_callback_exception = self._report_callback_exception
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._drain_log)
        self.root.deiconify()  # geometry is set; reveal at the final position

    # ---- settings --------------------------------------------------------
    def _load_settings(self):
        s = self.settings
        theme_pref = (s.get("gui", "theme", "auto") or "auto").strip().lower()
        if theme_pref not in theme.THEMES:  # e.g. "system": sv-ttk would raise
            theme_pref = "auto"
        self.theme_mode = theme.initial_mode() if theme_pref == "auto" else theme_pref
        self.keep_open = tk.BooleanVar(value=s.get_bool("gui", "keep_open", True))
        self.always_on_top = tk.BooleanVar(value=s.get_bool("gui", "always_on_top", False))

        saved_mode = s.get("defaults", "mode", "extract")
        # Bruteforce used to be a main-window mode; it now lives exclusively in
        # Run options. Migrate that old persisted value to regular extraction.
        if saved_mode == "bruteforce":
            saved_mode = "extract"
        self.mode = tk.StringVar(value=saved_mode)
        self.auto_fill = tk.BooleanVar(value=s.get_bool("defaults", "auto_fill_destination", True))
        self.source = tk.StringVar()
        self.dest = tk.StringVar()
        self.lock_dest = tk.BooleanVar(value=s.get_bool("defaults", "lock_destination", False))
        self.opt_delete = tk.StringVar(value=s.get("defaults", "delete_source", "keep"))

        self.opt_recursive = tk.BooleanVar(value=s.get_bool("defaults", "recursive", False))
        self.opt_max_depth = tk.IntVar(value=s.get_int("defaults", "max_depth", 5))
        self.opt_bruteforce = tk.BooleanVar(value=s.get_bool("defaults", "bruteforce", False))
        self.opt_password = tk.StringVar()
        self.opt_fast_check = tk.BooleanVar(value=s.get_bool("defaults", "fast_check", False))
        self.opt_debug = tk.BooleanVar(value=s.get_bool("defaults", "debug", False))

        # History (recent sources/dests).
        self.history_enabled = tk.BooleanVar(value=s.get_bool("history", "enabled", False))
        self.history_max = s.get_int("history", "max_entries", 10)
        self._src_hist = history.parse(s.get("history", "sources", "")) if self.history_enabled.get() else []
        self._dst_hist = history.parse(s.get("history", "dests", "")) if self.history_enabled.get() else []

    def _apply_window_prefs(self):
        self.root.attributes("-topmost", self.always_on_top.get())
        geometry = ""
        if self.settings.get_bool("window", "remember_geometry", True):
            geometry = self.settings.get("window", "geometry", "")
        if geometry:
            try:
                self.root.geometry(geometry)
                return
            except tk.TclError:
                pass
        self._center_on_screen()

    def _center_on_screen(self):
        self.root.update_idletasks()
        w = max(self.root.winfo_reqwidth(), 460)
        h = max(self.root.winfo_reqheight(), 360)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def _save_settings(self):
        s = self.settings
        if self._theme_forced:
            s.set("gui", "theme", self.theme_mode)
        s.set("gui", "keep_open", self.keep_open.get())
        s.set("gui", "always_on_top", self.always_on_top.get())
        s.set("history", "enabled", self.history_enabled.get())
        s.set("defaults", "mode", self.mode.get())
        s.set("defaults", "auto_fill_destination", self.auto_fill.get())
        s.set("defaults", "lock_destination", self.lock_dest.get())
        s.set("defaults", "delete_source", self.opt_delete.get())
        s.set("defaults", "recursive", self.opt_recursive.get())
        s.set("defaults", "max_depth", self._max_depth())
        s.set("defaults", "bruteforce", self.opt_bruteforce.get())
        s.set("defaults", "fast_check", self.opt_fast_check.get())
        s.set("defaults", "debug", self.opt_debug.get())
        if self.settings.get_bool("window", "remember_geometry", True):
            s.set("window", "geometry", self.root.geometry())
        self._save_gui_ini()

    def _save_gui_ini(self):
        """Save gui.ini; a failure is reported, never raised (closing must work)."""
        try:
            self.settings.save()
        except Exception as exc:
            logging.error(f"Could not save gui.ini: {exc}")
            self.log_queue.put(f"[settings] could not save gui.ini: {exc}")

    # ---- UI construction -------------------------------------------------
    # Keyboard access to every action (F10 also enters the self-drawn menu bar).
    SHORTCUTS = (
        ("<Control-o>", "_browse_source"), ("<Control-d>", "_browse_dest"),
        ("<Control-l>", "_clear_log"), ("<Control-b>", "_on_batch"),
        ("<Control-r>", "_open_run_options"), ("<Control-comma>", "_open_preferences"),
        ("<Control-t>", "_toggle_theme"), ("<F1>", "_about"), ("<Control-q>", "_on_close"),
    )

    # Settings and system changes that wait for the run to finish: dimmed in the menu bar and
    # their shortcuts ignored (a change meanwhile would not apply to the run anyway).
    RUN_LOCKED_ENTRIES = ("Run options...", "Preferences...", "Add to Explorer menu", "Remove from Explorer menu")
    RUN_LOCKED_SHORTCUTS = ("_open_run_options", "_open_preferences")

    def _shortcut(self, method):
        if self._running and method in self.RUN_LOCKED_SHORTCUTS:
            return
        getattr(self, method)()

    def _bind_keys(self):
        for sequence, method in self.SHORTCUTS:
            self.root.bind(sequence, lambda _event, m=method: self._shortcut(m))
        # Enter runs OK from the main window (not while a run is going).
        self.root.bind("<Return>", lambda _event: None if self._running else self._on_ok())

    def _build_menu(self):
        # Self-drawn menu bar: native tk.Menu bars/dropdowns are OS-rendered on
        # Windows and ignore colors, so they never go dark. MenuBar draws its own.
        self.menubar = MenuBar(
            self.root, self.theme_mode,
            icon=lambda semantic, mode: self.icons.photo(
                mode, semantic, icons.icon_size(self.root, COMPACT), gap=round(4 * icons.dpi_scale(self.root))))
        self.menubar.pack(fill="x", side="top")
        self.menubar.add_menu("File", [
            ("Open source...\tCtrl+O", self._browse_source),
            ("Open destination...\tCtrl+D", self._browse_dest),
            None,
            ("Clear log\tCtrl+L", self._clear_log),
            ("Open log file", self._open_log_file),
            ("Open log folder", self._open_log_folder),
            None,
            ("Show batch queue", self._show_batch),
            ("Clear batch queue", self._clear_batch),
            None,
            ("Exit\tCtrl+Q", self._on_close),
        ], icon="menu_file")
        self.menubar.add_menu("Edit", [
            ("Run options...\tCtrl+R", self._open_run_options),
            ("Preferences...\tCtrl+,", self._open_preferences),
            None,
            ("Toggle dark mode\tCtrl+T", self._toggle_theme),
            None,
            ("Add to Explorer menu", self._install_context_menu),
            ("Remove from Explorer menu", self._uninstall_context_menu),
        ], icon="menu_edit")
        self.menubar.add_menu("Help", [
            ("About\tF1", self._about),
        ], icon="menu_help")

    def _build_body(self):
        pad = {"padx": 10, "pady": 4}
        frm = ttk.Frame(self.root)
        frm.pack(fill="both", expand=True, padx=12, pady=10)

        # Source row
        row = ttk.Frame(frm); row.pack(fill="x", **pad)
        ttk.Label(row, text="Archive/Installer to:").pack(side="left")
        ttk.Radiobutton(row, text="extract", variable=self.mode, value="extract",
                        command=self._sync_mode).pack(side="left", padx=4)
        ttk.Radiobutton(row, text="scan", variable=self.mode, value="scan",
                        command=self._sync_mode).pack(side="left", padx=4)
        ttk.Radiobutton(row, text="carve", variable=self.mode, value="carve",
                        command=self._sync_mode).pack(side="left")

        row = ttk.Frame(frm); row.pack(fill="x", **pad)
        self.source_entry = ttk.Combobox(row, textvariable=self.source, values=self._src_hist)
        self.source_entry.pack(side="left", fill="x", expand=True)
        self.source_btn = self._icon(ttk.Button(row, text="...", width=3, command=self._browse_source),
                                     "browse_file", with_text=False)
        self.source_btn.pack(side="left", padx=4)
        Tooltip(self.source_btn, "Browse for the archive or installer (Ctrl+O)")

        # Destination row
        row = ttk.Frame(frm); row.pack(fill="x", **pad)
        ttk.Label(row, text="Destination directory:").pack(side="left")
        self.lock_chk = ttk.Checkbutton(row, text="lock", variable=self.lock_dest)
        self.lock_chk.pack(side="left", padx=4)
        Tooltip(self.lock_chk, LOCK_TIP)

        row = ttk.Frame(frm); row.pack(fill="x", **pad)
        self.dest_entry = ttk.Combobox(row, textvariable=self.dest, values=self._dst_hist)
        self.dest_entry.pack(side="left", fill="x", expand=True)
        self.dest_btn = self._icon(ttk.Button(row, text="...", width=3, command=self._browse_dest),
                                   "browse", with_text=False)
        self.dest_btn.pack(side="left", padx=4)
        Tooltip(self.dest_btn, "Browse for the destination folder (Ctrl+D)")

        # Buttons
        row = ttk.Frame(frm); row.pack(fill="x", padx=10, pady=(8, 4))
        self.ok_btn = self._icon(ttk.Button(row, text="OK", width=10, command=self._on_ok), "run")
        self.ok_btn.pack(side="left", padx=(0, 8))
        self._icon(ttk.Button(row, text="Cancel", width=10, command=self._on_cancel),
                   "dismiss").pack(side="left", padx=8)
        self.batch_btn = self._icon(ttk.Button(row, text="Batch", width=10, command=self._on_batch), "batch")
        self.batch_btn.pack(side="left", padx=8)
        Tooltip(self.batch_btn, BATCH_TIP)

        ttk.Separator(frm).pack(fill="x", pady=(8, 2), padx=10)

        # Progress bar + status line sit under the log (packed first so they keep their room)
        bottom = ttk.Frame(frm)
        bottom.pack(side="bottom", fill="x", padx=10, pady=(4, 0))
        self.progress = ttk.Progressbar(bottom, mode="determinate")
        self.progress.pack(fill="x")
        self.status = StatusLine(bottom)
        self.status.label.pack(fill="x", pady=(4, 0))
        self.status.set("Ready")

        # Log pane: read-only, scrollable, bounded (gui/log_pane.py)
        self.log_pane = LogPane(frm, LOG_PLACEHOLDER, self.theme_mode)
        self.log_pane.frame.pack(fill="both", expand=True, **pad)
        self.log = self.log_pane.text
        self.log_pane.bind_context_menu(self._show_log_menu)
        self._sync_mode()

    # ---- helpers ---------------------------------------------------------
    def _sync_mode(self):
        scan = self.mode.get() == "scan"
        state = "disabled" if scan else "normal"
        self.dest_entry.config(state=state)
        self.dest_btn.config(state=state)
        self.lock_chk.config(state=state)
        if not scan:
            self._autofill(force=False)

    def _autofill(self, force=False):
        """Fill the destination from the source. force=True overwrites an existing
        (auto-filled) value; otherwise a non-empty destination is left alone so a
        user-typed path is never clobbered."""
        if self.mode.get() == "scan" or not self.auto_fill.get() or self.lock_dest.get():
            return
        src = self.source.get().strip()
        if not src:
            return
        if self.dest.get().strip() and not force:
            return
        if self.mode.get() == "carve":
            self.dest.set(paths.default_carve_output_dir(src))
        else:
            self.dest.set(paths.default_output_dir(src))

    def _browse_source(self):
        # Tk file dialogs return forward-slash paths on Windows even though it
        # is a native Windows path; normalize so it displays and is passed
        # around using the native separator.
        path = filedialog.askopenfilename(title="Select archive/installer")
        if path:
            self.source.set(os.path.normpath(path))
            self._autofill(force=True)

    def _browse_dest(self):
        path = filedialog.askdirectory(title="Select destination directory")
        if path:
            self.dest.set(os.path.normpath(path))

    def _enable_dnd(self):
        """Register file drag-and-drop on the whole window, the source entry and the log
        (no-op without tkinterdnd2)."""
        try:
            from tkinterdnd2 import DND_FILES
        except Exception:
            return
        for target in (self.root, self.source_entry, self.log):
            try:
                target.drop_target_register(DND_FILES)
                target.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass  # root is not a TkinterDnD.Tk() — DnD unavailable

    def _on_drop(self, event):
        # tkdnd only brace-wraps a dropped path when it needs Tcl list quoting
        # (spaces, multiple files). An unbraced payload is a single raw native
        # path: running it through tk.splitlist would treat its backslashes as
        # Tcl backslash-escapes (e.g. "\temp" -> a literal tab) and corrupt it.
        data = event.data
        if "{" in data:
            dropped = self.root.tk.splitlist(data)
        else:
            # Unbraced: no path in it has a space (tkdnd braces those), so a
            # space separates several dropped paths. Split plainly, without
            # Tcl's backslash processing.
            dropped = tuple(part for part in data.split(" ") if part)
        if not dropped:
            return
        self.source.set(dropped[0])
        self._autofill(force=True)
        # Only one file fits the source box: the others wait in the batch queue.
        extra = dropped[1:]
        for path in extra:
            self.batch_queue.append((self.mode.get(), os.path.normpath(path), ""))
            self._append(f"[queued] {path}")
        if extra:
            count = len(extra)
            self._set_status(f"{count} more file{'s' if count > 1 else ''} queued. Press Batch to run them.")

    def _max_depth(self, default=5):
        """The Max depth box as an int; an empty/non-numeric box makes IntVar.get()
        raise TclError, which used to block saving settings and closing the window."""
        try:
            return max(0, int(self.opt_max_depth.get()))
        except (tk.TclError, ValueError):
            return default

    def _current_opts(self):
        return {
            "recursive": self.opt_recursive.get(),
            "max_depth": self._max_depth(),
            "bruteforce": self.opt_bruteforce.get(),
            "password": self.opt_password.get(),
            "fast_check": self.opt_fast_check.get(),
            "debug": self.opt_debug.get(),
            # A locked destination is a shared folder kept on purpose: extract
            # into it. Otherwise an existing, non-empty destination makes the
            # CLI use a new <folder>_<date-time> folder.
            "merge_output": self.lock_dest.get(),
        }

    def _resolve_delete(self):
        """Keep/Ask/Delete → boolean flag for the CLI. Ask confirms before the run."""
        mode = self.opt_delete.get()
        if mode == "delete":
            return True
        if mode == "ask":
            return messagebox.askyesno(
                "Delete source",
                "Delete each source file after a successful extraction?",
                parent=self.root)
        return False

    def _current_output_dir(self):
        dest = self.dest.get().strip()
        if dest:
            return dest
        src = self.source.get().strip()
        return paths.default_output_dir(src) if src else ""

    def _open_path(self, path):
        if not path or not os.path.exists(path):
            messagebox.showinfo("Not found", f"Not found:\n{path}", parent=self.root)
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)  # noqa: has startfile on Windows
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except OSError as exc:
            messagebox.showerror("Error", str(exc), parent=self.root)

    def _push_history(self, src, dest):
        if not self.history_enabled.get():
            return
        if src:
            self._src_hist = history.push(self._src_hist, src, self.history_max)
        if dest:
            self._dst_hist = history.push(self._dst_hist, dest, self.history_max)
        self.source_entry.config(values=self._src_hist)
        self.dest_entry.config(values=self._dst_hist)
        self.settings.set("history", "sources", history.join(self._src_hist))
        self.settings.set("history", "dests", history.join(self._dst_hist))
        self._save_gui_ini()

    LOG_BATCH = 500  # lines per main-loop tick, so a flood never freezes the UI

    def _append(self, text):
        self.log_pane.append(text)

    def _clear_log(self):
        self.log_pane.clear()

    # ---- log menu (right-click, Shift+F10, Menu key) ----------------------
    def _popup_icon(self, semantic, mode, disabled):
        """16 px icon for a popup row, its gap to the text padded into the image."""
        return self.icons.photo(mode, semantic, icons.icon_size(self.root, COMPACT),
                                DISABLED if disabled else NORMAL,
                                gap=round(ICON_GAP * icons.dpi_scale(self.root)))

    def _show_log_menu(self, x, y):
        pane = self.log_pane
        has_output = not pane.is_empty
        show_context_menu(self.root, self.theme_mode, x, y, [
            Item("Copy selection\tCtrl+C", self._copy_log_selection, "copy", bool(pane.selected_text())),
            Item("Copy all", self._copy_log_all, "copy", has_output),
            Item("Save as...", self._save_log_as, "save", has_output),
            None,
            Item("Clear\tCtrl+L", self._clear_log, "clear", has_output),
        ], icon=self._popup_icon)

    def _copy_log_selection(self):
        self._copy_log(self.log_pane.selected_text())

    def _copy_log_all(self):
        self._copy_log(self.log_pane.get_all())

    def _copy_log(self, text):
        if not text:
            return
        if copy_to_clipboard(self.root, text):
            self._set_status("Copied to the clipboard")
        else:
            message = "Could not copy: the clipboard is in use by another program"
            self._append(f"[log] {message}")
            self._set_status(message, "error")

    def _save_log_as(self):
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Save the log", defaultextension=".log",
            initialfile="magic-extractor-gui.log",
            filetypes=(("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")))
        if not path:
            return  # cancelled
        path = os.path.normpath(path)
        try:
            save_text(path, self.log_pane.get_all())
        except OSError as exc:
            logging.error(f"Could not save the log to {path}: {exc}")
            self._append(f"[log] could not save {path}: {exc}")
            self._set_status(f"Could not save the log: {exc}", "error")
        else:
            self._set_status(f"Log saved to {path}")

    def _open_log_folder(self):
        self._open_path(self._current_output_dir())

    def _open_log_file(self):
        out = self._current_output_dir()
        self._open_path(os.path.join(out, LOG_FILENAME) if out else "")

    def _drain_log(self):
        """Move queued log lines into the pane in bounded batches (one insert per
        tick) and finish a run the worker reported; reschedules itself."""
        lines = []
        try:
            while len(lines) < self.LOG_BATCH:
                lines.append(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        if lines:
            self._append("\n".join(lines))
        self._drain_jobs()
        if self.log_queue.empty():
            try:
                all_ok = self.done_queue.get_nowait()
            except queue.Empty:
                pass
            else:
                self._drain_jobs()  # whatever the worker queued before it reported done
                self._on_run_finished(all_ok)
        try:
            self.root.after(10 if not self.log_queue.empty() else 100, self._drain_log)
        except tk.TclError:
            pass  # window already destroyed

    def _drain_jobs(self):
        """Apply the job events the worker queued (main thread): the status line follows
        the job being run and the results are kept for the end-of-run summary."""
        try:
            while True:
                event = self.job_queue.get_nowait()
                if event[0] == "start":
                    _kind, index, total, mode, source = event
                    self._set_status(job_status(index, total, mode, source))
                elif event[0] == "exit":
                    _kind, _index, mode, source, code = event
                    self._run_results.append((mode, source, code))
        except queue.Empty:
            pass

    def _set_status(self, text, level="info"):
        """Show ``text`` in the status line ("info", "warning" or "error" level)."""
        status = getattr(self, "status", None)
        if status is not None:
            status.set(text, level)

    def _report_callback_exception(self, exc_type, exc, tb):
        """Tk calls this when a callback raises: log the traceback and say so in the log
        pane and the status line instead of losing it."""
        logging.error("Unhandled error in a Tk callback", exc_info=(exc_type, exc, tb))
        message = f"{exc_type.__name__}: {exc}"
        where = logging_setup.log_path()
        try:
            self._append(f"[error] internal error: {message}" + (f" (details in {where})" if where else ""))
            self._set_status(f"Internal error: {message}", "error")
        except Exception:  # the error hook itself must never raise (e.g. window being destroyed)
            logging.debug("could not show the callback error", exc_info=True)

    def _set_running(self, running):
        self._running = running
        state = "disabled" if running else "normal"
        self.ok_btn.config(state=state)
        self.batch_btn.config(state=state)
        self.menubar.set_entry_state(self.RUN_LOCKED_ENTRIES, state)
        if running:  # busy indicator: a run has no known length
            self.progress.config(mode="indeterminate")
            self.progress.start(15)
        else:
            self.progress.stop()
            self.progress.config(mode="determinate", value=0)

    # ---- context menu ----------------------------------------------------
    def _context_menu_parts(self):
        """Launcher argv the Explorer verb runs (before the "%1" file)."""
        if getattr(sys, "frozen", False):
            return [sys.executable]  # the GUI exe itself
        return [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")]

    def _install_context_menu(self):
        if not context_menu.is_supported():
            messagebox.showinfo("Windows only", "Explorer integration is Windows-only.", parent=self.root)
            return
        try:
            context_menu.install(self._context_menu_parts())
            messagebox.showinfo("Done", "Added 'Extract with Magic Extractor' to the Explorer menu.", parent=self.root)
        except OSError as exc:
            messagebox.showerror("Error", str(exc), parent=self.root)

    def _uninstall_context_menu(self):
        if not context_menu.is_supported():
            messagebox.showinfo("Windows only", "Explorer integration is Windows-only.", parent=self.root)
            return
        try:
            context_menu.uninstall()
            messagebox.showinfo("Done", "Removed from the Explorer menu.", parent=self.root)
        except OSError as exc:
            messagebox.showerror("Error", str(exc), parent=self.root)

    # ---- actions ---------------------------------------------------------
    def _run_jobs(self, jobs):
        """jobs: list of (mode, source, dest). Runs them sequentially, streaming."""
        try:
            prefix = runner.resolve_backend()
        except FileNotFoundError as exc:
            messagebox.showerror("Backend not found", str(exc), parent=self.root)
            return
        opts = self._current_opts()
        needs_extract = any(mode == "extract" for mode, _, _ in jobs)
        # Resolve the Keep/Ask/Delete prompt once, on the main thread.
        delete_flag = self._resolve_delete() if needs_extract else False
        for _, src, dest in jobs:
            self._push_history(src, dest)
        self.cancel_flag.clear()
        self._run_total = len(jobs)
        self._run_results = []
        self._set_running(True)
        self._set_status(job_status(1, len(jobs), jobs[0][0], jobs[0][1]))

        def work():
            # Runs off the main thread: only queues here, never Tk (thread-safety).
            all_ok = True
            try:
                for index, (mode, src, dest) in enumerate(jobs, 1):
                    self.job_queue.put(("start", index, len(jobs), mode, src))
                    job_opts = dict(opts)
                    if mode == "extract":
                        job_opts["delete_source"] = delete_flag
                    self.log_queue.put(f"=== {mode}: {src} ===")
                    try:
                        argv = runner.build_command(prefix, mode, src, dest, job_opts)
                        self.log_queue.put("$ " + " ".join(runner.display_command(argv)))
                        code = runner.run_streaming(argv, self.log_queue.put, self.cancel_flag.is_set)
                    except Exception as exc:  # e.g. the backend exe is blocked or missing
                        self.log_queue.put(f"[error] could not run the backend: {exc}")
                        code = -1
                    self.log_queue.put(f"[exit {code}]")
                    self.job_queue.put(("exit", index, mode, src, code))
                    all_ok = all_ok and code == 0
                    if self.cancel_flag.is_set():
                        self.log_queue.put("[cancelled]")
                        all_ok = False
                        break
            finally:
                self.done_queue.put(all_ok)  # buttons are always re-enabled

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _on_run_finished(self, all_ok=True):
        self._set_running(False)
        if self._run_total:
            text, level = run_summary(self._run_results, self._run_total, self.cancel_flag.is_set())
            self._set_status(text, level)
            self._run_total = 0
        # "keep_open" off means auto-close on success: a failed or cancelled run
        # stays open so its log can be read.
        if all_ok and not self.keep_open.get():
            self._on_close()

    def _on_ok(self):
        src = self.source.get().strip()
        if not src:
            messagebox.showwarning("No source", "Select a source file first.", parent=self.root)
            return
        self._run_jobs([(self.mode.get(), src, self.dest.get())])

    def _on_batch(self):
        """UniExtract semantics: with a source, enqueue it; empty source runs the
        queue; empty source + empty queue opens a multi-file picker and runs."""
        src = self.source.get().strip()
        if src:
            self.batch_queue.append((self.mode.get(), src, self.dest.get()))
            self._append(f"[queued] {src}")
            self._set_status(f"Queued {source_name(src)}: {len(self.batch_queue)} waiting. Press Batch to run them.")
            self.source.set("")
            if not self.lock_dest.get():
                self.dest.set("")
            return
        if self.batch_queue:
            self._run_queue()
            return
        mode = self.mode.get()
        picked = filedialog.askopenfilenames(title=f"Select files to {mode}")
        for path in picked:
            self.batch_queue.append((mode, os.path.normpath(path), ""))
        if self.batch_queue:
            self._run_queue()

    def _run_queue(self):
        jobs = list(self.batch_queue)
        self.batch_queue.clear()
        self._run_jobs(jobs)

    def _show_batch(self):
        if not self.batch_queue:
            self._append("[batch] queue empty")
            return
        self._append("[batch queue]")
        for index, (mode, src, dest) in enumerate(self.batch_queue):
            self._append(f"  {index}: {mode} {src} -> {dest or '(auto)'}")

    def _clear_batch(self):
        self.batch_queue.clear()
        self._append("[batch] queue cleared")
        self._set_status("Batch queue cleared")

    def _on_cancel(self):
        if self._running:
            self.cancel_flag.set()
            self._set_status("Cancelling...")
        else:
            self._on_close()

    def _on_close(self):
        """Close the window. A running job is cancelled first (after asking), so no
        extractor keeps running (or deletes a source) with nobody watching; a
        failing settings save never keeps the window open."""
        if self._running:
            if not messagebox.askyesno(
                    "Extraction running",
                    "An extraction is still running.\nCancel it and close the window?",
                    parent=self.root):
                return
            self.cancel_flag.set()
            if self.worker is not None:
                self.worker.join(timeout=10)  # the worker never waits on Tk
        try:
            self._save_settings()
        except Exception as exc:
            logging.error(f"Could not save the settings: {exc}")
        finally:
            self.root.destroy()

    def _icon(self, button, semantic, with_text=True):
        """Put the icon for ``semantic`` on a ttk button (text-only without assets)."""
        return self.icons.attach(button, semantic, self.theme_mode, with_text=with_text)

    def _toggle_theme(self):
        self.theme_mode = theme.toggle(self.root)
        self._theme_forced = True
        theme.scale_theme_fonts(self.root)
        self.icons.retheme(self.theme_mode)
        self.log_pane.restyle(self.theme_mode)
        self.menubar.recolor(self.theme_mode)

    # ---- dialogs ---------------------------------------------------------
    def _make_dialog(self, title):
        """A themed, non-resizable Toplevel hidden until centered; returns
        (window, padded body frame). Content goes in the body."""
        win = tk.Toplevel(self.root)
        win.withdraw()
        win.transient(self.root)
        win.resizable(False, False)
        if self.always_on_top.get():
            win.attributes("-topmost", True)  # else it hides behind an always-on-top main window
        theme.restyle_toplevel(win, self.theme_mode)
        win.title(title)
        win.bind("<Escape>", lambda _event: win.destroy())
        body = ttk.Frame(win, padding=14)
        body.pack(fill="both", expand=True)
        return win, body

    def _scrollable(self, parent):
        """
        A frame that scrolls vertically when its content is taller than ~70% of
        the screen (Preferences with every warning shown, or at 200% scaling),
        so the dialog's buttons below it always stay on screen.
        """
        outer = ttk.Frame(parent)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0, borderwidth=0,
                           bg=theme.palette(self.theme_mode)["bg"])
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)

        def fit(_event=None):
            max_height = int(self.root.winfo_screenheight() * 0.7)
            height = min(inner.winfo_reqheight(), max_height)
            canvas.configure(width=inner.winfo_reqwidth(), height=height,
                             scrollregion=(0, 0, inner.winfo_reqwidth(), inner.winfo_reqheight()))
            if inner.winfo_reqheight() > max_height:
                scrollbar.pack(side="right", fill="y")
            else:
                scrollbar.pack_forget()

        def wheel(event):
            if scrollbar.winfo_ismapped():
                canvas.yview_scroll(int(-event.delta / 120), "units")

        inner.bind("<Configure>", fit)
        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", wheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))
        return inner

    def _center_on_parent(self, win):
        """Center win over the main window, then reveal it."""
        win.update_idletasks()
        px, py = self.root.winfo_rootx(), self.root.winfo_rooty()
        pw, ph = self.root.winfo_width(), self.root.winfo_height()
        w, h = win.winfo_width(), win.winfo_height()
        win.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")
        win.deiconify()
        theme.titlebar(win, self.theme_mode)  # dark title bar once the dialog is mapped

    def _add_option_alert(self, container, key, variable):
        """
        A Bootstrap-style warning alert under an option, shown while the option
        is in a risky state (see gui/option_warnings.py) and hidden otherwise.
        """
        if key not in option_warnings.OPTION_WARNINGS:
            return
        colors = theme.alert_colors(self.theme_mode)
        # Wrap by text width (about 60 characters), not fixed pixels, so it
        # follows the font size and the display scaling.
        wrap = tkfont.nametofont("TkDefaultFont").measure("0") * 60
        alert = tk.Label(
            container, justify="left", anchor="w", wraplength=wrap, padx=8, pady=6,
            font=theme.body_font(container),
            bg=colors["bg"], fg=colors["fg"], highlightthickness=1,
            highlightbackground=colors["border"], highlightcolor=colors["border"],
        )

        def update(*_args):
            text = option_warnings.warning_for(key, variable.get())
            if text:
                alert.config(text=WARNING_SIGN + "  " + text)
                alert.pack(fill="x", padx=(22, 0), pady=(1, 6))
            else:
                alert.pack_forget()

        trace = variable.trace_add("write", update)

        def forget_trace(event):
            # the variable outlives the dialog; drop the callback with the widget
            if event.widget is container:
                try:
                    variable.trace_remove("write", trace)
                except tk.TclError:
                    pass

        container.bind("<Destroy>", forget_trace, add="+")
        update()

    def _option_check(self, parent, key, text, variable, pady=1):
        """A Checkbutton with its warning alert (if it has one) right below it."""
        row = ttk.Frame(parent)
        row.pack(fill="x", anchor="w")
        ttk.Checkbutton(row, text=text, variable=variable).pack(anchor="w", pady=pady)
        self._add_option_alert(row, key, variable)

    def _open_run_options(self):
        win, body = self._make_dialog("Run options")

        opts = ttk.LabelFrame(body, text="Extraction", padding=10)
        opts.pack(fill="x")
        self._option_check(opts, "recursive", "Recursive (extract nested archives)", self.opt_recursive, pady=2)
        row = ttk.Frame(opts); row.pack(anchor="w", pady=2)
        ttk.Label(row, text="Max depth:").pack(side="left")
        ttk.Spinbox(row, from_=1, to=99, width=5, textvariable=self.opt_max_depth).pack(side="left", padx=6)
        self._option_check(opts, "bruteforce", "Bruteforce (try every handler)", self.opt_bruteforce, pady=2)
        self._option_check(opts, "fast_check", "Fast type check (first 64 KB only)", self.opt_fast_check, pady=2)
        row = ttk.Frame(opts); row.pack(anchor="w", pady=2, fill="x")
        ttk.Label(row, text="Password:").pack(side="left")
        ttk.Entry(row, textvariable=self.opt_password, show="*").pack(side="left", padx=6, fill="x", expand=True)

        after = ttk.LabelFrame(body, text="After a successful extraction", padding=10)
        after.pack(fill="x", pady=(10, 0))
        for value, label in (("keep", "Keep the source file"),
                             ("ask", "Ask before deleting the source"),
                             ("delete", "Delete the source file")):
            ttk.Radiobutton(after, text=label, variable=self.opt_delete, value=value).pack(anchor="w", pady=1)
        self._add_option_alert(after, "delete_source", self.opt_delete)

        self._icon(ttk.Button(body, text="Close", command=win.destroy), "dismiss").pack(pady=(12, 0))
        self._center_on_parent(win)

    def _open_preferences(self):
        path = runner.resolve_config_path()
        current = config_io.read_config(path)
        cfg_vars = {k: tk.BooleanVar(value=config_io.config_bool(current, k)) for k in CONFIG_KEYS}
        win, body = self._make_dialog("Preferences")
        options = self._scrollable(body)

        extraction = ttk.LabelFrame(options, text="Extraction", padding=10)
        extraction.pack(fill="x")
        for key in CONFIG_KEYS:
            self._option_check(extraction, key, CONFIG_LABELS[key], cfg_vars[key])

        # Edit copies; the live settings only change on Save (Cancel undoes nothing).
        live = {"auto_fill_destination": self.auto_fill,
                "keep_open": self.keep_open,
                "always_on_top": self.always_on_top,
                "debug": self.opt_debug,
                "history_enabled": self.history_enabled}
        copies = {key: tk.BooleanVar(value=variable.get()) for key, variable in live.items()}
        interface = ttk.LabelFrame(options, text="Interface", padding=10)
        interface.pack(fill="x", pady=(10, 0))
        for key, variable in copies.items():
            self._option_check(interface, key, GUI_LABELS[key], variable)

        def save():
            try:
                config_io.write_config(path, {k: cfg_vars[k].get() for k in CONFIG_KEYS})
            except (OSError, ValueError) as exc:  # e.g. read-only install folder
                messagebox.showerror("Could not save the preferences", str(exc), parent=win)
                return
            for key, variable in live.items():
                variable.set(copies[key].get())
            self.root.attributes("-topmost", self.always_on_top.get())
            self._save_settings()
            win.destroy()

        win.bind("<Return>", lambda _event: save())
        buttons = ttk.Frame(body); buttons.pack(pady=(12, 0))
        self._icon(ttk.Button(buttons, text="Save", command=save), "save").pack(side="left", padx=4)
        self._icon(ttk.Button(buttons, text="Cancel", command=win.destroy), "dismiss").pack(side="left", padx=4)
        self._center_on_parent(win)

    def _about(self):
        win, body = self._make_dialog("About")
        ttk.Label(body, text="Magic Extractor", font=("", 12, "bold")).pack(anchor="w")
        ttk.Label(body, text="Universal extraction tool.").pack(anchor="w", pady=(2, 10))
        ttk.Label(body, text=f"Version: {runner.read_version()}").pack(anchor="w")
        ttk.Label(body, text="Author: DSR! (xchwarze)").pack(anchor="w")
        url = "https://github.com/xchwarze/magic-extractor"
        link = ttk.Label(body, text=url, foreground=theme.palette(self.theme_mode)["link"], cursor="hand2")
        link.pack(anchor="w", pady=(2, 0))
        link.bind("<Button-1>", lambda e: webbrowser.open(url))
        self._icon(ttk.Button(body, text="Close", command=win.destroy), "dismiss").pack(pady=(14, 0))
        self._center_on_parent(win)
