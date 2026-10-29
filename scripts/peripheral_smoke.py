#!/usr/bin/env python3
"""Read-only QML device navigation. Never apply settings or record audio."""
from pathlib import Path
import subprocess,sys
if __name__=='__main__':
    raise SystemExit(subprocess.call([sys.executable,str(Path(__file__).with_name('qml_readonly_smoke.py')),*sys.argv[1:]]))
