"""Windows Explorer context-menu integration (winreg, Windows-only).

Registers an "Extract with Magic Extractor" verb under HKCU for all files, whose
command launches the GUI with the clicked file — which the GUI prefills via
main.py's argv parsing. All winreg use is lazy so this module imports on any OS.
"""
import sys

KEY_PATH = r"Software\Classes\*\shell\MagicExtractor"
LABEL = "Extract with Magic Extractor"


def is_supported():
    return sys.platform == "win32"


def command_string(parts):
    """Build the registry command: each launcher part quoted, plus the "%1" file."""
    return " ".join(f'"{part}"' for part in parts) + ' "%1"'


def install(parts):
    """Create the context-menu key. Returns True on success."""
    import winreg
    command = command_string(parts)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY_PATH) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, LABEL)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY_PATH + r"\command") as cmd_key:
        winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, command)
    return True


def uninstall():
    """Remove the context-menu key. Returns True on success (or if absent)."""
    import winreg
    for sub in (KEY_PATH + r"\command", KEY_PATH):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
        except FileNotFoundError:
            pass
    return True


def is_installed():
    """True if the context-menu key exists."""
    if not is_supported():
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY_PATH):
            return True
    except OSError:
        return False
