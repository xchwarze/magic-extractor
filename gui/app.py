"""Universal-Extractor-style Tk window that drives the magic-extractor CLI."""
import os
import queue
import subprocess
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from gui import runner, config_io, theme, paths, history, context_menu
from gui.settings import GuiSettings
from gui.menubar import MenuBar

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
}

LOG_FILENAME = "magic-extractor.log"
LOG_PLACEHOLDER = "Ready. Extraction and detection output will appear here."


class ExtractorApp:
    def __init__(self, root, initial_source=None, initial_dest=None, initial_mode=None):
        self.root = root
        self.root.title("Magic Extractor")
        # Stay hidden until geometry from gui.ini is applied, so the window does
        # not first paint at the default spot and then jump to its saved position.
        self.root.withdraw()
        self.log_queue = queue.Queue()
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

        self._build_menu()
        self._build_body()
        theme.apply(self.root, self.theme_mode)
        theme.restyle_text(self.log, self.theme_mode)
        self.menubar.recolor(self.theme_mode)
        self._enable_dnd()
        self._apply_window_prefs()

        # Auto-fill the destination as the source is typed/changed.
        self.source.trace_add("write", lambda *a: self._autofill(force=False))
        if initial_source and not initial_dest:
            self._autofill(force=True)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._drain_log)
        self.root.deiconify()  # geometry is set; reveal at the final position

    # ---- settings --------------------------------------------------------
    def _load_settings(self):
        s = self.settings
        theme_pref = (s.get("gui", "theme", "auto") or "auto").lower()
        self.theme_mode = theme.initial_mode() if theme_pref == "auto" else theme_pref
        self.keep_open = tk.BooleanVar(value=s.get_bool("gui", "keep_open", True))
        self.always_on_top = tk.BooleanVar(value=s.get_bool("gui", "always_on_top", False))

        self.mode = tk.StringVar(value=s.get("defaults", "mode", "extract"))
        self.auto_fill = tk.BooleanVar(value=s.get_bool("defaults", "auto_fill_destination", True))
        self.source = tk.StringVar()
        self.dest = tk.StringVar()
        self.lock_dest = tk.BooleanVar(value=s.get_bool("defaults", "lock_destination", False))
        self.opt_delete = tk.StringVar(value=s.get("defaults", "delete_source", "keep"))

        self.opt_recursive = tk.BooleanVar(value=s.get_bool("defaults", "recursive", False))
        self.opt_max_depth = tk.IntVar(value=s.get_int("defaults", "max_depth", 5))
        self.opt_bruteforce = tk.BooleanVar(value=s.get_bool("defaults", "bruteforce", False))
        self.opt_password = tk.StringVar()
        self.opt_fast_check = tk.BooleanVar(value=s.get_bool("defaults", "fast_check", True))
        self.opt_debug = tk.BooleanVar(value=s.get_bool("defaults", "debug", False))

        # History (recent sources/dests).
        self.history_enabled = s.get_bool("history", "enabled", False)
        self.history_max = s.get_int("history", "max_entries", 10)
        self._src_hist = history.parse(s.get("history", "sources", "")) if self.history_enabled else []
        self._dst_hist = history.parse(s.get("history", "dests", "")) if self.history_enabled else []

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
        s.set("defaults", "mode", self.mode.get())
        s.set("defaults", "auto_fill_destination", self.auto_fill.get())
        s.set("defaults", "lock_destination", self.lock_dest.get())
        s.set("defaults", "delete_source", self.opt_delete.get())
        s.set("defaults", "recursive", self.opt_recursive.get())
        s.set("defaults", "max_depth", self.opt_max_depth.get())
        s.set("defaults", "bruteforce", self.opt_bruteforce.get())
        s.set("defaults", "fast_check", self.opt_fast_check.get())
        s.set("defaults", "debug", self.opt_debug.get())
        if self.settings.get_bool("window", "remember_geometry", True):
            s.set("window", "geometry", self.root.geometry())
        try:
            s.save()
        except OSError:
            pass

    # ---- UI construction -------------------------------------------------
    def _build_menu(self):
        # Self-drawn menu bar: native tk.Menu bars/dropdowns are OS-rendered on
        # Windows and ignore colors, so they never go dark. MenuBar draws its own.
        self.menubar = MenuBar(self.root, self.theme_mode)
        self.menubar.pack(fill="x", side="top")
        self.menubar.add_menu("File", [
            ("Open source...", self._browse_source),
            ("Open destination...", self._browse_dest),
            None,
            ("Clear log", self._clear_log),
            ("Open log file", self._open_log_file),
            ("Open log folder", self._open_log_folder),
            None,
            ("Show batch queue", self._show_batch),
            ("Clear batch queue", self._clear_batch),
            None,
            ("Exit", self._on_close),
        ])
        self.menubar.add_menu("Edit", [
            ("Run options...", self._open_run_options),
            ("Preferences...", self._open_preferences),
            None,
            ("Toggle dark mode", self._toggle_theme),
            None,
            ("Add to Explorer menu", self._install_context_menu),
            ("Remove from Explorer menu", self._uninstall_context_menu),
        ])
        self.menubar.add_menu("Help", [
            ("About", self._about),
        ])

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
                        command=self._sync_mode).pack(side="left")

        row = ttk.Frame(frm); row.pack(fill="x", **pad)
        self.source_entry = ttk.Combobox(row, textvariable=self.source, values=self._src_hist)
        self.source_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="...", width=3, command=self._browse_source).pack(side="left", padx=4)

        # Destination row
        row = ttk.Frame(frm); row.pack(fill="x", **pad)
        ttk.Label(row, text="Destination directory:").pack(side="left")
        self.lock_chk = ttk.Checkbutton(row, text="lock", variable=self.lock_dest)
        self.lock_chk.pack(side="left", padx=4)

        row = ttk.Frame(frm); row.pack(fill="x", **pad)
        self.dest_entry = ttk.Combobox(row, textvariable=self.dest, values=self._dst_hist)
        self.dest_entry.pack(side="left", fill="x", expand=True)
        self.dest_btn = ttk.Button(row, text="...", width=3, command=self._browse_dest)
        self.dest_btn.pack(side="left", padx=4)

        # Buttons
        row = ttk.Frame(frm); row.pack(fill="x", padx=10, pady=(8, 4))
        self.ok_btn = ttk.Button(row, text="OK", width=10, command=self._on_ok)
        self.ok_btn.pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Cancel", width=10, command=self._on_cancel).pack(side="left", padx=8)
        self.batch_btn = ttk.Button(row, text="Batch", width=10, command=self._on_batch)
        self.batch_btn.pack(side="left", padx=8)

        ttk.Separator(frm).pack(fill="x", pady=(8, 2), padx=10)

        # Log pane
        self.log = tk.Text(frm, height=14, state="disabled", wrap="none",
                           relief="flat", borderwidth=1, padx=8, pady=6)
        self.log.pack(fill="both", expand=True, **pad)
        self.log.tag_config("hint", foreground="#888888")
        self._log_empty = True
        self._show_placeholder()
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
        self.dest.set(paths.default_output_dir(src))

    def _browse_source(self):
        path = filedialog.askopenfilename(title="Select archive/installer")
        if path:
            self.source.set(path)
            self._autofill(force=True)

    def _browse_dest(self):
        path = filedialog.askdirectory(title="Select destination directory")
        if path:
            self.dest.set(path)

    def _enable_dnd(self):
        """Register file drag-and-drop on the source entry + log (no-op without tkinterdnd2)."""
        try:
            from tkinterdnd2 import DND_FILES
        except Exception:
            return
        for target in (self.source_entry, self.log):
            try:
                target.drop_target_register(DND_FILES)
                target.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass  # root is not a TkinterDnD.Tk() — DnD unavailable

    def _on_drop(self, event):
        # tk.splitlist handles brace-wrapped, space-containing, multi-file payloads.
        dropped = self.root.tk.splitlist(event.data)
        if not dropped:
            return
        self.source.set(dropped[0])
        self._autofill(force=True)

    def _current_opts(self):
        return {
            "recursive": self.opt_recursive.get(),
            "max_depth": self.opt_max_depth.get(),
            "bruteforce": self.opt_bruteforce.get(),
            "password": self.opt_password.get(),
            "fast_check": self.opt_fast_check.get(),
            "debug": self.opt_debug.get(),
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
        if not self.history_enabled:
            return
        if src:
            self._src_hist = history.push(self._src_hist, src, self.history_max)
        if dest:
            self._dst_hist = history.push(self._dst_hist, dest, self.history_max)
        self.source_entry.config(values=self._src_hist)
        self.dest_entry.config(values=self._dst_hist)
        self.settings.set("history", "sources", history.join(self._src_hist))
        self.settings.set("history", "dests", history.join(self._dst_hist))
        try:
            self.settings.save()
        except OSError:
            pass

    def _show_placeholder(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.insert("1.0", LOG_PLACEHOLDER, ("hint",))
        self.log.config(state="disabled")
        self._log_empty = True

    def _append(self, text):
        self.log.config(state="normal")
        if self._log_empty:
            self.log.delete("1.0", "end")  # drop the placeholder on first real line
            self._log_empty = False
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _clear_log(self):
        self._show_placeholder()

    def _open_log_folder(self):
        self._open_path(self._current_output_dir())

    def _open_log_file(self):
        out = self._current_output_dir()
        self._open_path(os.path.join(out, LOG_FILENAME) if out else "")

    def _drain_log(self):
        try:
            while True:
                self._append(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        self.root.after(100, self._drain_log)

    def _set_running(self, running):
        state = "disabled" if running else "normal"
        self.ok_btn.config(state=state)
        self.batch_btn.config(state=state)

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
        self._set_running(True)

        def work():
            for mode, src, dest in jobs:
                job_opts = dict(opts)
                if mode == "extract":
                    job_opts["delete_source"] = delete_flag
                self.log_queue.put(f"=== {mode}: {src} ===")
                argv = runner.build_command(prefix, mode, src, dest, job_opts)
                self.log_queue.put("$ " + " ".join(argv))
                code = runner.run_streaming(argv, self.log_queue.put, self.cancel_flag.is_set)
                self.log_queue.put(f"[exit {code}]")
                if self.cancel_flag.is_set():
                    self.log_queue.put("[cancelled]")
                    break
            self.root.after(0, self._on_run_finished)

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _on_run_finished(self):
        self._set_running(False)
        if not self.keep_open.get():
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
            self.source.set("")
            if not self.lock_dest.get():
                self.dest.set("")
            return
        if self.batch_queue:
            self._run_queue()
            return
        picked = filedialog.askopenfilenames(title="Select files to extract")
        for path in picked:
            self.batch_queue.append(("extract", path, ""))
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

    def _on_cancel(self):
        if self.worker and self.worker.is_alive():
            self.cancel_flag.set()
        else:
            self._on_close()

    def _on_close(self):
        self._save_settings()
        self.root.destroy()

    def _toggle_theme(self):
        self.theme_mode = theme.toggle(self.root)
        self._theme_forced = True
        theme.restyle_text(self.log, self.theme_mode)
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
        body = ttk.Frame(win, padding=14)
        body.pack(fill="both", expand=True)
        return win, body

    def _center_on_parent(self, win):
        """Center win over the main window, then reveal it."""
        win.update_idletasks()
        px, py = self.root.winfo_rootx(), self.root.winfo_rooty()
        pw, ph = self.root.winfo_width(), self.root.winfo_height()
        w, h = win.winfo_width(), win.winfo_height()
        win.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")
        win.deiconify()
        theme.titlebar(win, self.theme_mode)  # dark title bar once the dialog is mapped

    def _open_run_options(self):
        win, body = self._make_dialog("Run options")

        opts = ttk.LabelFrame(body, text="Extraction", padding=10)
        opts.pack(fill="x")
        ttk.Checkbutton(opts, text="Recursive (extract nested archives)", variable=self.opt_recursive).pack(anchor="w", pady=2)
        row = ttk.Frame(opts); row.pack(anchor="w", pady=2)
        ttk.Label(row, text="Max depth:").pack(side="left")
        ttk.Spinbox(row, from_=1, to=99, width=5, textvariable=self.opt_max_depth).pack(side="left", padx=6)
        ttk.Checkbutton(opts, text="Bruteforce (try every handler)", variable=self.opt_bruteforce).pack(anchor="w", pady=2)
        ttk.Checkbutton(opts, text="Fast type check", variable=self.opt_fast_check).pack(anchor="w", pady=2)
        row = ttk.Frame(opts); row.pack(anchor="w", pady=2, fill="x")
        ttk.Label(row, text="Password:").pack(side="left")
        ttk.Entry(row, textvariable=self.opt_password, show="*").pack(side="left", padx=6, fill="x", expand=True)

        after = ttk.LabelFrame(body, text="After a successful extraction", padding=10)
        after.pack(fill="x", pady=(10, 0))
        for value, label in (("keep", "Keep the source file"),
                             ("ask", "Ask before deleting the source"),
                             ("delete", "Delete the source file")):
            ttk.Radiobutton(after, text=label, variable=self.opt_delete, value=value).pack(anchor="w", pady=1)

        ttk.Button(body, text="Close", command=win.destroy).pack(pady=(12, 0))
        self._center_on_parent(win)

    def _open_preferences(self):
        path = runner.resolve_config_path()
        current = config_io.read_config(path)
        cfg_vars = {k: tk.BooleanVar(value=current.get(k, "False") == "True") for k in CONFIG_KEYS}
        win, body = self._make_dialog("Preferences")

        extraction = ttk.LabelFrame(body, text="Extraction", padding=10)
        extraction.pack(fill="x")
        for key in CONFIG_KEYS:
            ttk.Checkbutton(extraction, text=CONFIG_LABELS[key], variable=cfg_vars[key]).pack(anchor="w", pady=1)

        interface = ttk.LabelFrame(body, text="Interface", padding=10)
        interface.pack(fill="x", pady=(10, 0))
        ttk.Checkbutton(interface, text=GUI_LABELS["auto_fill_destination"], variable=self.auto_fill).pack(anchor="w", pady=1)
        ttk.Checkbutton(interface, text=GUI_LABELS["keep_open"], variable=self.keep_open).pack(anchor="w", pady=1)
        ttk.Checkbutton(interface, text=GUI_LABELS["always_on_top"], variable=self.always_on_top).pack(anchor="w", pady=1)
        ttk.Checkbutton(interface, text=GUI_LABELS["debug"], variable=self.opt_debug).pack(anchor="w", pady=1)

        def save():
            config_io.write_config(path, {k: cfg_vars[k].get() for k in CONFIG_KEYS})
            self.root.attributes("-topmost", self.always_on_top.get())
            self._save_settings()
            win.destroy()

        buttons = ttk.Frame(body); buttons.pack(pady=(12, 0))
        ttk.Button(buttons, text="Save", command=save).pack(side="left", padx=4)
        ttk.Button(buttons, text="Cancel", command=win.destroy).pack(side="left", padx=4)
        self._center_on_parent(win)

    def _about(self):
        win, body = self._make_dialog("About")
        ttk.Label(body, text="Magic Extractor", font=("", 12, "bold")).pack(anchor="w")
        ttk.Label(body, text="Universal extraction tool.").pack(anchor="w", pady=(2, 10))
        ttk.Label(body, text="Author: DSR! (xchwarze)").pack(anchor="w")
        url = "https://github.com/xchwarze/magic-extractor"
        link = ttk.Label(body, text=url, foreground="#4da3ff", cursor="hand2")
        link.pack(anchor="w", pady=(2, 0))
        link.bind("<Button-1>", lambda e: webbrowser.open(url))
        ttk.Button(body, text="Close", command=win.destroy).pack(pady=(14, 0))
        self._center_on_parent(win)
