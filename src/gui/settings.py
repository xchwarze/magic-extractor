"""Typed read/write for the GUI's multi-section gui.ini (configparser).

config_io handles the CLI's single [settings] section; gui.ini has several
sections ([gui], [defaults], [history], [window]), so it gets its own small
accessor with typed getters and a persistent setter.
"""
import configparser


class GuiSettings:
    def __init__(self, path):
        self.path = path
        self.parser = configparser.ConfigParser()
        self.parser.read(path)

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

    def save(self):
        with open(self.path, "w") as fh:
            self.parser.write(fh)
