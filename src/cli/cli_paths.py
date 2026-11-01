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
