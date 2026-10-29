#!/usr/bin/env python3
"""Functional QML simulation over shared mock services; no real hardware I/O."""
from pathlib import Path
import subprocess,sys
if __name__=='__main__':
    raise SystemExit(subprocess.call([sys.executable,str(Path(__file__).with_name('qml_functional_smoke.py')),*sys.argv[1:]]))
