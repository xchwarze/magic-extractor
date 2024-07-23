import configparser

class Config:
    """A singleton class to manage application configuration."""
    _instance = None  # Private attribute to store the unique instance
    config_file_path = 'config.ini'  # Path to the configuration file

    def __new__(cls):
        """Overrides the __new__ method to ensure a single instance."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance.load_config()
        return cls._instance

    def load_config(self):
        """Loads the configuration from the .ini file."""
        self.config = configparser.ConfigParser()
        self.config.read(self.config_file_path)
        self.settings = {section: dict(self.config.items(section)) for section in self.config.sections()}

    def get(self, section, key, fallback=None, type=None):
        """Gets a specific configuration value with optional type casting."""
        value = self.settings.get(section, {}).get(key, fallback)
        if type is not None and value is not None:
            if type == bool:
                return value.lower() in ('true', '1', 't', 'y', 'yes', 'on')
            return type(value)
        return value

    def set(self, section, key, value):
        """Sets a specific configuration value, prepares to save back to the file."""
        if section not in self.config:
            self.config.add_section(section)

        self.config.set(section, key, str(value))
        self.settings[section][key] = value

    def save(self):
        """Writes changes back to the .ini file."""
        with open(self.config_file_path, 'w') as config_file:
            self.config.write(config_file)
