#!/usr/bin/env python3
"""Compatibility launcher for a source checkout and the user-local installation."""
from pathlib import Path
import sys

_source = Path(__file__).resolve().parent / 'src'
if _source.is_dir():
    sys.path.insert(0, str(_source))

from logi_center.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
