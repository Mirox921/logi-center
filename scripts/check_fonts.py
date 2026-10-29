#!/usr/bin/env python3
"""Verify bundled UI font families and Russian/Latin glyph coverage."""
import os
from pathlib import Path
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QT_QPA_PLATFORMTHEME'] = 'generic'

from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QRawFont

root = Path(__file__).resolve().parents[1]
app = QGuiApplication([])
families = {}
for filename in ('NotoSans-Regular.ttf', 'NotoSans-Bold.ttf', 'JetBrainsMonoNerdFont-Regular.ttf'):
    font_id = QFontDatabase.addApplicationFont(str(root / 'qml_ui' / 'assets' / 'fonts' / filename))
    if font_id < 0:
        raise SystemExit(f'FAIL: could not load {filename}')
    for family in QFontDatabase.applicationFontFamilies(font_id):
        families[filename] = family

required = list(range(0x410, 0x450)) + [0x401, 0x451] + list(range(0x41, 0x5B)) + list(range(0x61, 0x7B))
for filename, family in families.items():
    raw = QRawFont.fromFont(QFont(family, 12))
    missing = [f'U+{code:04X}' for code in required if not raw.supportsCharacter(code)]
    if not raw.isValid() or missing:
        raise SystemExit(f'FAIL: {family} ({filename}) has missing glyphs: {", ".join(missing[:8])}')
    print(f'PASS: {filename}: loaded family "{raw.familyName()}"; Latin A–Z/a–z and Cyrillic А–я, Ё/ё present.')
del app
