#!/usr/bin/env python3
"""Compatibility entry point for the offline layered Cairo 2D pipeline."""
# Allow direct execution without installing developer tools.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import scripts  # source-package bootstrap
from scripts.artwork.illustrations.render_all import main

if __name__=='__main__':main()
