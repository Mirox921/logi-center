#!/usr/bin/env python3
"""QML load, navigation and lint check; no real hardware writes."""
from pathlib import Path
import subprocess,sys
if __name__=='__main__':
    raise SystemExit(subprocess.call([sys.executable,str(Path(__file__).with_name('qml_smoke.py'))]))
