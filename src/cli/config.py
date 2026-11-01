import configparser
import logging
import os
import tempfile

TRUE_VALUES = ('true', '1', 't', 'y', 'yes', 'on')
FALSE_VALUES = ('false', '0', 'f', 'n', 'no', 'off')


class Config:
    """A singleton class to manage application configuration."""
    _instance = None  # Private attribute to store the unique instance

    def __new__(cls, config_path='config.ini'):
        """Overrides the __new__ method to ensure a single instance.

        config_path should be an absolute path (resolved against the base path
        by the caller) so the config is found regardless of the working
        directory or whether the app is frozen. Honored on first instantiation.
        """
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance.config_file_path = config_path
            cls._instance.load_config()
        return cls._instance

    def load_config(self):
        """
        Loads the configuration from the .ini file. A UTF-8 BOM (written by
        e.g. PowerShell 5.1) is accepted; a malformed file is reported and the
        built-in defaults are used instead of crashing every subcommand.
        """
        self.config = configparser.ConfigParser()
        try:
            self.config.read(self.config_file_path, encoding='utf-8-sig')
        except (configparser.Error, UnicodeDecodeError) as exc:
            logging.warning(f"Ignoring unreadable config {self.config_file_path}: {exc}")
            self.config = configparser.ConfigParser()
        self.settings = {section: dict(self.config.items(section)) for section in self.config.sections()}

    def get(self, section, key, fallback=None, type=None):
        """
        Gets a specific configuration value with optional type casting. A
        boolean that is neither a known true nor false word (a typo such as
        "Ture", or empty) yields the fallback, never a silent False: e.g.
        delete_to_recycle_bin must not turn into permanent deletion.
        """
        value = self.settings.get(section, {}).get(key, fallback)
        if type is not None and value is not None:
            if type == bool:
                if isinstance(value, bool):
                    return value
                word = str(value).strip().lower()
                if word in TRUE_VALUES:
                    return True
                if word in FALSE_VALUES:
                    return False
                logging.warning(f"[{section}] {key} = {value!r} is not true/false; using {fallback!r}")
                return fallback
            return type(value)
        return value

    def set(self, section, key, value):
        """Sets a specific configuration value, prepares to save back to the file."""
        if section not in self.config:
            self.config.add_section(section)

        self.config.set(section, key, str(value))
        self.settings.setdefault(section, {})[key] = value

    def save(self):
        """
        Writes changes back to the .ini file, atomically (a temporary file in
        the same folder, then replace), so a failure never leaves it half
        written. Returns True on success; logs and returns False otherwise
        (e.g. --update-defaults from a read-only install folder).
        """
        folder = os.path.dirname(os.path.abspath(self.config_file_path))
        temp_path = None
        try:
            fd, temp_path = tempfile.mkstemp(prefix='.config-', suffix='.ini', dir=folder)
            with os.fdopen(fd, 'w', encoding='utf-8') as config_file:
                self.config.write(config_file)
            os.replace(temp_path, self.config_file_path)
            return True
        except OSError as exc:
            logging.error(f"Could not save {self.config_file_path}: {exc}")
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            return False
