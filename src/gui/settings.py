"""Typed read/write for the GUI's multi-section gui.ini (configparser).

config_io handles the CLI's single [settings] section; gui.ini has several
sections ([gui], [defaults], [history], [window]), so it gets its own small
accessor with typed getters and a persistent setter.

Values are stored verbatim (no '%' interpolation: history paths may contain
'%'), the file is read and written as UTF-8 (paths such as "архив.zip"), and
saving rewrites only the changed values in place, so the commented gui.ini
that ships with the release keeps its comments.
"""
import configparser
import logging
import os
import re
import tempfile

_SECTION = re.compile(r"^\s*\[([^\]]+)\]\s*$")
_KEY = re.compile(r"^\s*([^=:;#\s][^=:]*?)\s*[=:]")


class GuiSettings:
    def __init__(self, path):
        self.path = path
        self.parser = configparser.ConfigParser(interpolation=None)
        self._changed = {}  # (section, key) -> value set since load
        try:
            self.parser.read(path, encoding="utf-8-sig")
        except (configparser.Error, UnicodeDecodeError) as exc:
            # A malformed gui.ini must not stop the GUI from starting.
            logging.warning(f"Ignoring unreadable {path}: {exc}")
            self.parser = configparser.ConfigParser(interpolation=None)

    def get(self, section, key, fallback=None):
        return self.parser.get(section, key, fallback=fallback)

    def get_bool(self, section, key, fallback=False):
        try:
            return self.parser.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_int(self, section, key, fallback=0):
        try:
            return self.parser.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def set(self, section, key, value):
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        self.parser.set(section, key, str(value))
        self._changed[(section, key)] = str(value)

    def _render(self, original_lines):
        """original_lines with every changed value updated in place (comments and
        layout kept); keys/sections that are missing are appended."""
        pending = dict(self._changed)
        output, section = [], None

        def flush(current):
            for (sect, key), value in list(pending.items()):
                if sect == current:
                    output.append(f"{key} = {value}\n")
                    del pending[(sect, key)]

        for line in original_lines:
            header = _SECTION.match(line)
            if header:
                flush(section)
                section = header.group(1).strip()
                output.append(line)
                continue
            key_match = _KEY.match(line)
            if key_match and section is not None:
                key = key_match.group(1).strip().lower()
                if (section, key) in pending:
                    newline = "\n" if line.endswith("\n") else ""
                    output.append(f"{key_match.group(1).strip()} = {pending.pop((section, key))}{newline}")
                    continue
            output.append(line)
        flush(section)
        for sect in dict.fromkeys(sect for sect, _key in pending):
            if output and output[-1].strip():
                output.append("\n")
            output.append(f"[{sect}]\n")
            flush(sect)
        return output

    def save(self):
        """Write the changed values atomically (temporary file + replace), so a
        failure never leaves gui.ini truncated. Raises OSError on failure."""
        try:
            with open(self.path, encoding="utf-8-sig") as fh:
                lines = fh.readlines()
        except FileNotFoundError:
            lines = []
        except (OSError, UnicodeDecodeError):
            lines = []  # unreadable: write a fresh file with the current values
            self._changed = {(s, k): v for s in self.parser.sections() for k, v in self.parser.items(s)}
        content = "".join(self._render(lines))
        folder = os.path.dirname(os.path.abspath(self.path))
        fd, temp_path = tempfile.mkstemp(prefix=".gui-", suffix=".ini", dir=folder)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            os.replace(temp_path, self.path)
        except BaseException:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
