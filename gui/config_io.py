"""Read/write the CLI's config.ini [settings] section directly (configparser).

Editing config.ini avoids the extract subparser's `type=bool` footgun, where
bool("False") is True on the command line.
"""
import configparser

SECTION = "settings"

# What the CLI does when a key is missing from config.ini: it treats a missing
# boolean as off, except delete_to_recycle_bin (main.py falls back to True).
CLI_DEFAULTS = {"delete_to_recycle_bin": True}
TRUE_VALUES = ("true", "1", "t", "y", "yes", "on")  # same set as cli/config.py


def config_bool(values, key):
    """
    A [settings] boolean the way the CLI reads it: case-insensitive, missing ->
    the CLI's own default. (Comparing to the literal "True" showed lowercase or
    missing values as unchecked, and saving then wrote them back as False.)
    """
    if key not in values:
        return CLI_DEFAULTS.get(key, False)
    return str(values[key]).strip().lower() in TRUE_VALUES


def read_config(path):
    """Return the [settings] section as {key: str}; {} if the file/section is absent."""
    parser = configparser.ConfigParser()
    parser.read(path)
    if not parser.has_section(SECTION):
        return {}
    return dict(parser.items(SECTION))


def write_config(path, values):
    """Update keys under [settings], preserving other keys/sections; create as needed."""
    parser = configparser.ConfigParser()
    parser.read(path)
    if not parser.has_section(SECTION):
        parser.add_section(SECTION)
    for key, value in values.items():
        parser.set(SECTION, key, str(value))
    with open(path, "w") as fh:
        parser.write(fh)
