"""Filesystem locations used by the CLI, including frozen builds."""

import os
import sys


if getattr(sys, "frozen", False):
    BASE_PATH = os.path.dirname(sys.executable)
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

BIN_PATH = os.path.join(BASE_PATH, "bin")
DATA_PATH = os.path.join(BASE_PATH, "data")
CONFIG_PATH = os.path.join(BASE_PATH, "config.ini")
# Release builds ship VERSION beside the exe; from source it is at the repo root.
VERSION_PATH = (
    os.path.join(BASE_PATH, "VERSION")
    if getattr(sys, "frozen", False)
    else os.path.join(os.path.dirname(os.path.dirname(BASE_PATH)), "VERSION")
)


def read_version():
    """The release version, or "dev" when there is no VERSION file."""
    try:
        with open(VERSION_PATH, encoding="utf-8") as version_fh:
            return version_fh.read().strip() or "dev"
    except OSError:
        return "dev"
