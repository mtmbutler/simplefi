import os
import sys
from pathlib import Path

import yaml
from django.core.management import execute_from_command_line

from simplefi import __version__


def manage():
    """A function-ized version of manage.py for a setuptools entry point."""
    # Look for a conf file to set environment variables
    conf_path = os.path.join(Path.home(), "simplefi.yaml")
    try:
        with open(conf_path) as f:
            conf = yaml.safe_load(f)
        os.environ.update(conf)
    except FileNotFoundError:
        print(f"No config file found at: {conf_path}")

    if "--version" in sys.argv or "-v" in sys.argv:
        print(__version__)
    else:
        execute_from_command_line(sys.argv)
