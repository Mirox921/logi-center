#!/usr/bin/env python3
"""Reproduce isolated header screenshots and actual SVG small-size review."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def logo_sheet(destination):
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QGuiApplication, QImage, QPainter, QColor, QFont
    from PySide6.QtSvg import QSvgRenderer
    app = QGuiApplication.instance() or QGuiApplication([])
    svg = QSvgRenderer(str(ROOT / 'qml_ui/assets/brand/logi-mark.svg'))
    if not svg.isValid():
        raise RuntimeError('Brand SVG is invalid')
    image = QImage(600, 240, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(image)
    p.setFont(QFont('monospace', 11))
    for row, bg in enumerate(('#171713', '#f4f0e7')):
        p.fillRect(0, row * 120, 600, 120, QColor(bg))
        p.setPen(QColor('#f4f0e7' if row == 0 else '#171713'))
        for column, size in enumerate((16, 24, 32, 40)):
            x = 40 + column * 140
            svg.render(p, QRectF(x, row * 120 + 20, size, size))
            p.drawText(x, row * 120 + 95, f'{size}px')
    p.end()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(destination)):
        raise RuntimeError('Could not save logo contact sheet')
    print('Logo review:', destination.relative_to(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=('before', 'after'), default='after')
    parser.add_argument('--logo', action='store_true')
    args = parser.parse_args()
    target = ROOT / 'docs/screenshots/redesign/header' / args.stage
    if args.logo:
        logo_sheet(target / 'logo-sizes.png')
        return 0
    for language in ('ru', 'en'):
        folder = target / language
        if args.stage == 'before' and folder.exists():
            print('Preserved baseline:', folder.relative_to(ROOT))
            continue
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='generic',
            LOGI_CENTER_QML_SCREENSHOT_DIR=str(folder), LOGI_CENTER_QML_LANGUAGE=language,
            LOGI_CENTER_QML_WIDTHS='800,1000,1280,1600,1920', LOGI_CENTER_QML_CAPTURE_ALL='1',
            LOGI_CENTER_QML_CAPTURE_HEADER='1')
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/illustration_dashboard.py'), '--worker'],
            cwd=ROOT, env=env, timeout=90)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
