#!/usr/bin/env python3
"""Capture the QML design system at responsive sizes and compare amber/lime."""
# Allow direct execution without installing developer tools.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import scripts  # source-package bootstrap
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'screenshots' / 'redesign' / 'design-language'
BEFORE = OUT / 'before'
AFTER = OUT / 'after'
PALETTE = OUT / 'palette-comparison'
WIDTHS = '640,800,1000,1280,1600,1920'


def run_variant(name, *, qml_root=None, widths=WIDTHS, capture_all=True, language='ru'):
    destination = Path(tempfile.mkdtemp(prefix=f'logi-center-{name}-'))
    env = os.environ.copy()
    env.update({
        'QT_QPA_PLATFORM': 'offscreen',
        'QT_QPA_PLATFORMTHEME': 'generic',
        'LOGI_CENTER_QML_SCREENSHOT_DIR': str(destination),
        'LOGI_CENTER_QML_WIDTHS': widths,
        'LOGI_CENTER_QML_CAPTURE_ALL': '1' if capture_all else '0',
        'LOGI_CENTER_QML_LANGUAGE': language,
    })
    if qml_root:
        env['LOGI_CENTER_QML_ROOT'] = str(qml_root)
    command = [sys.executable, str(ROOT / 'app.py'), '--ui', 'qml', '--simulate', '--smoke']
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=90)
    print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr)
    if result.returncode:
        raise SystemExit(result.returncode)
    return destination


def copy_screenshots(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if item.is_file() and item.suffix == '.png':
            shutil.copy2(item, destination / item.name)


def make_lime_variant(base):
    variant = base / 'lime-ui'
    (variant / 'qml').mkdir(parents=True)
    shutil.copytree(ROOT / 'src/logi_center/qml_ui/qml', variant / 'qml', dirs_exist_ok=True)
    shutil.copytree(ROOT / 'assets', variant / 'assets', dirs_exist_ok=True)
    # Developer-only palette comparison: the released product has only amber.
    for folder in (variant / 'qml', variant / 'assets'):
        for path in folder.rglob('*'):
            if path.is_file() and path.suffix.lower() in ('.qml', '.svg'):
                value = path.read_text(encoding='utf-8')
                value = value.replace('#f3aa32', '#c4d844').replace('#4b3519', '#394019')
                path.write_text(value, encoding='utf-8')
    return variant / 'qml'


def main():
    if BEFORE.exists():
        shutil.rmtree(BEFORE)
    BEFORE.mkdir(parents=True)
    legacy = ROOT / 'docs' / 'screenshots' / 'redesign' / 'device-artwork' / 'before'
    for width in (640, 800, 1000, 1280, 1600, 1920):
        source = legacy / f'dashboard-{width}.png'
        if source.is_file():
            shutil.copy2(source, BEFORE / source.name)
    if (legacy / 'dashboard-1000-en.png').is_file():
        shutil.copy2(legacy / 'dashboard-1000-en.png', BEFORE / 'dashboard-1000-en.png')
    if (legacy / 'device-detail-1000.png').is_file():
        shutil.copy2(legacy / 'device-detail-1000.png', BEFORE / 'device-detail-1000.png')
    print(f'Baseline screenshots copied: {len(list(BEFORE.glob("*.png")))}')

    for language in ('ru', 'en'):
        destination = run_variant(f'amber-{language}', widths=WIDTHS, language=language)
        copy_screenshots(destination, AFTER / language)
        shutil.rmtree(destination)

    lime_qml = make_lime_variant(Path(tempfile.mkdtemp(prefix='logi-center-palette-')))
    lime = run_variant('lime-preview', qml_root=lime_qml, widths='1000', capture_all=False, language='ru')
    PALETTE.mkdir(parents=True, exist_ok=True)
    amber_file = AFTER / 'ru' / 'dashboard-1000.png'
    if amber_file.is_file():
        shutil.copy2(amber_file, PALETTE / 'amber-dashboard-1000.png')
    if (lime / 'dashboard-1000.png').is_file():
        shutil.copy2(lime / 'dashboard-1000.png', PALETTE / 'lime-dashboard-1000.png')
    shutil.rmtree(lime)
    shutil.rmtree(lime_qml.parent.parent, ignore_errors=True)
    print(f'After screenshots: {AFTER}')
    print(f'Accent comparison: {PALETTE}')
    print('PASS: screenshots are from the QML application using the isolated --simulate adapter.')


if __name__ == '__main__':
    main()
