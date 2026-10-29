#!/usr/bin/env python3
"""Run the default QML UI smoke under offscreen Qt when PySide6 is installed."""
# Allow direct execution without installing developer tools.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import scripts  # source-package bootstrap
import os
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
qml_dir = root / 'src/logi_center/qml_ui/qml'
qmllint = shutil.which('qmllint') or ('/usr/lib/qt6/bin/qmllint' if Path('/usr/lib/qt6/bin/qmllint').is_file() else None)
if qmllint:
    qml_files = sorted(str(path) for path in qml_dir.glob('*.qml'))
    lint = subprocess.run([qmllint, '-I', str(qml_dir), *qml_files],
                          text=True, capture_output=True, cwd=root)
    if lint.returncode:
        print(lint.stdout, end='')
        print(lint.stderr, end='', file=sys.stderr)
        raise SystemExit(lint.returncode)
    print('PASS: qmllint accepted the QML pages and Theme module.')

try:
    import PySide6  # noqa: F401
except ImportError:
    result = subprocess.run([sys.executable, str(root / 'app.py'), '--simulate'],
                            text=True, capture_output=True, cwd=root)
    expected = 'install PySide6' in result.stderr and result.returncode == 2
    if expected:
        print('SKIP: PySide6 is not installed; verified the default launcher reports the missing Qt dependency clearly.')
        raise SystemExit(0)
    print(result.stdout, end='')
    print(result.stderr, end='', file=sys.stderr)
    raise SystemExit(result.returncode or 1)

environment = os.environ.copy()
environment['QT_QPA_PLATFORM'] = 'offscreen'
environment['QT_QPA_PLATFORMTHEME'] = 'generic'
result = subprocess.run([sys.executable, str(root / 'app.py'), '--simulate', '--smoke'],
                        cwd=root, env=environment)
raise SystemExit(result.returncode)
