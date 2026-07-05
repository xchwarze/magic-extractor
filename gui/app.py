"""Universal-Extractor-style Tk window that drives the magic-extractor CLI."""
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from gui import runner, config_io, theme

CONFIG_KEYS = [
    "open_output_folder", "check_free_space", "check_unicode",
    "fix_file_extensions", "create_log_files",
]


class ExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Magic Extractor")
        self.log_queue = queue.Queue()
        self.worker = None
        self.cancel_flag = threading.Event()

        # State
        self.theme_mode = theme.initial_mode()
        self.mode = tk.StringVar(value="extract")
        self.source = tk.StringVar()
        self.dest = tk.StringVar()
        self.lock_dest = tk.BooleanVar(value=False)
        # per-run options
        self.opt_recursive = tk.BooleanVar(value=False)
        self.opt_max_depth = tk.IntVar(value=5)
        self.opt_bruteforce = tk.BooleanVar(value=False)
        self.opt_password = tk.StringVar()
        self.opt_fast_check = tk.BooleanVar(value=True)

        self._build_menu()
        self._build_body()
        theme.apply(self.root, self.theme_mode)
        theme.restyle_text(self.log, self.theme_mode)
        self.root.after(100, self._drain_log)

    # ---- UI construction -------------------------------------------------
    def _build_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open source...", command=self._browse_source)
        file_menu.add_command(label="Open destination...", command=self._browse_dest)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Run options...", command=self._open_run_options)
        edit_menu.add_command(label="Preferences...", command=self._open_preferences)
        edit_menu.add_separator()
        edit_menu.add_command(label="Toggle dark mode", command=self._toggle_theme)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._about)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)

    def _build_body(self):
        pad = {"padx": 6, "pady": 3}
        frm = ttk.Frame(self.root)
        frm.pack(fill="both", expand=True, padx=8, pady=8)

        # Source row
        row = ttk.Frame(frm); row.pack(fill="x", **pad)
        ttk.Label(row, text="Archive/Installer to:").pack(side="left")
        ttk.Radiobutton(row, text="extract", variable=self.mode, value="extract",
                        command=self._sync_mode).pack(side="left", padx=4)
        ttk.Radiobutton(row, text="scan", variable=self.mode, value="scan",
                        command=self._sync_mode).pack(side="left")

        row = ttk.Frame(frm); row.pack(fill="x", **pad)
        ttk.Entry(row, textvariable=self.source).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="...", width=3, command=self._browse_source).pack(side="left", padx=4)

        # Destination row
        row = ttk.Frame(frm); row.pack(fill="x", **pad)
        ttk.Label(row, text="Destination directory:").pack(side="left")
        self.lock_chk = ttk.Checkbutton(row, text="lock", variable=self.lock_dest)
        self.lock_chk.pack(side="left", padx=4)

        row = ttk.Frame(frm); row.pack(fill="x", **pad)
        self.dest_entry = ttk.Entry(row, textvariable=self.dest)
        self.dest_entry.pack(side="left", fill="x", expand=True)
        self.dest_btn = ttk.Button(row, text="...", width=3, command=self._browse_dest)
        self.dest_btn.pack(side="left", padx=4)

        # Buttons
        row = ttk.Frame(frm); row.pack(fill="x", **pad)
        self.ok_btn = ttk.Button(row, text="OK", width=10, command=self._on_ok)
        self.ok_btn.pack(side="left", padx=4)
        ttk.Button(row, text="Cancel", width=10, command=self._on_cancel).pack(side="left", padx=4)
        self.batch_btn = ttk.Button(row, text="Batch", width=10, command=self._on_batch)
        self.batch_btn.pack(side="left", padx=4)

        # Log pane
        self.log = tk.Text(frm, height=14, state="disabled", wrap="none")
        self.log.pack(fill="both", expand=True, **pad)
        self._sync_mode()

    # ---- helpers ---------------------------------------------------------
    def _sync_mode(self):
        scan = self.mode.get() == "scan"
        state = "disabled" if scan else "normal"
        self.dest_entry.config(state=state)
        self.dest_btn.config(state=state)
        self.lock_chk.config(state=state)

    def _browse_source(self):
        path = filedialog.askopenfilename(title="Select archive/installer")
        if path:
            self.source.set(path)
            if not self.lock_dest.get():
                self.dest.set("")  # let the CLI derive <name>_extracted

    def _browse_dest(self):
        path = filedialog.askdirectory(title="Select destination directory")
        if path:
            self.dest.set(path)

    def _current_opts(self):
        return {
            "recursive": self.opt_recursive.get(),
            "max_depth": self.opt_max_depth.get(),
            "bruteforce": self.opt_bruteforce.get(),
            "password": self.opt_password.get(),
            "fast_check": self.opt_fast_check.get(),
        }

    def _append(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

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

    # ---- actions ---------------------------------------------------------
    def _run_jobs(self, sources):
        try:
            prefix = runner.resolve_backend()
        except FileNotFoundError as exc:
            messagebox.showerror("Backend not found", str(exc))
            return
        mode = self.mode.get()
        dest = self.dest.get()
        opts = self._current_opts()
        self.cancel_flag.clear()
        self._set_running(True)

        def work():
            for src in sources:
                self.log_queue.put(f"=== {mode}: {src} ===")
                argv = runner.build_command(prefix, mode, src, dest, opts)
                self.log_queue.put("$ " + " ".join(argv))
                code = runner.run_streaming(argv, self.log_queue.put, self.cancel_flag.is_set)
                self.log_queue.put(f"[exit {code}]")
                if self.cancel_flag.is_set():
                    self.log_queue.put("[cancelled]")
                    break
            self.root.after(0, lambda: self._set_running(False))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _on_ok(self):
        src = self.source.get().strip()
        if not src:
            messagebox.showwarning("No source", "Select a source file first.")
            return
        self._run_jobs([src])

    def _on_batch(self):
        paths = filedialog.askopenfilenames(title="Select files to extract")
        if paths:
            self.mode.set("extract")
            self._sync_mode()
            self._run_jobs(list(paths))

    def _on_cancel(self):
        if self.worker and self.worker.is_alive():
            self.cancel_flag.set()
        else:
            self.root.quit()

    def _toggle_theme(self):
        self.theme_mode = theme.toggle(self.root)
        theme.restyle_text(self.log, self.theme_mode)

    # ---- dialogs ---------------------------------------------------------
    def _open_run_options(self):
        win = tk.Toplevel(self.root)
        theme.restyle_toplevel(win, self.theme_mode)
        win.title("Run options")
        ttk.Checkbutton(win, text="Recursive", variable=self.opt_recursive).pack(anchor="w", padx=8, pady=2)
        row = ttk.Frame(win); row.pack(anchor="w", padx=8, pady=2)
        ttk.Label(row, text="Max depth:").pack(side="left")
        ttk.Spinbox(row, from_=1, to=99, width=5, textvariable=self.opt_max_depth).pack(side="left", padx=4)
        ttk.Checkbutton(win, text="Bruteforce (try every handler)", variable=self.opt_bruteforce).pack(anchor="w", padx=8, pady=2)
        ttk.Checkbutton(win, text="Fast type check", variable=self.opt_fast_check).pack(anchor="w", padx=8, pady=2)
        row = ttk.Frame(win); row.pack(anchor="w", padx=8, pady=2)
        ttk.Label(row, text="Password:").pack(side="left")
        ttk.Entry(row, textvariable=self.opt_password, show="*").pack(side="left", padx=4)
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=6)

    def _open_preferences(self):
        path = runner.resolve_config_path()
        current = config_io.read_config(path)
        vars_ = {k: tk.BooleanVar(value=current.get(k, "False") == "True") for k in CONFIG_KEYS}
        win = tk.Toplevel(self.root)
        theme.restyle_toplevel(win, self.theme_mode)
        win.title("Preferences")
        for key in CONFIG_KEYS:
            ttk.Checkbutton(win, text=key, variable=vars_[key]).pack(anchor="w", padx=8, pady=2)

        def save():
            config_io.write_config(path, {k: vars_[k].get() for k in CONFIG_KEYS})
            win.destroy()

        ttk.Button(win, text="Save", command=save).pack(pady=6)

    def _about(self):
        messagebox.showinfo("About", "Magic Extractor GUI\nWrapper for the magic-extractor CLI.")
