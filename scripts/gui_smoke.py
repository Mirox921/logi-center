#!/usr/bin/env python3
"""QML load, navigation and lint check; no real hardware writes."""
# Allow direct execution without installing developer tools.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import scripts  # source-package bootstrap
from pathlib import Path
import subprocess,sys
if __name__=='__main__':
    raise SystemExit(subprocess.call([sys.executable,str(Path(__file__).with_name('qml_smoke.py'))]))
