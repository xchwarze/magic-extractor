"""Read/write the CLI's config.ini [settings] section directly (configparser).

Editing config.ini avoids the extract subparser's `type=bool` footgun, where
bool("False") is True on the command line.
"""
import configparser

SECTION = "settings"


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
