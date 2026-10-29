#!/usr/bin/env python3
"""Capture the real QML Dashboard with an isolated, explicitly simulated art set."""
# Allow direct execution without installing developer tools.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import scripts  # source-package bootstrap
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def fixture_snapshot(simulation=False, simulation_adapter=None, **unused):
    if not simulation:
        raise RuntimeError('Artwork screenshots require --simulate')
    from logi_center.core.capabilities.model import Capability
    from logi_center.core.devices.devices import Device, DeviceManager
    def battery(value, charging=False):
        return [Capability('battery_status', 'simulation', True, True, value=value, source='simulation'),
                Capability('charging', 'simulation', True, True, value=charging, source='simulation')]
    rows = [
        Device('sim:review-mouse', 'MCHOSE K7 Ultra', 'mouse', 'simulation', 'review-mouse',
               vid='3837', pid='1001', physical='/fixture/usb-k7', connection='2.4g', simulated=True,
               capabilities=battery(64, True) + [Capability('dpi', 'simulation', True, True, True, value=1600, source='simulation')]),
        Device('sim:review-ace', 'MCHOSE Ace68-II', 'keyboard', 'simulation', 'review-ace',
               vid='41e4', pid='2116', connection='usb', simulated=True),
        Device('sim:review-internal-keyboard', 'Internal keyboard', 'keyboard', 'simulation', 'review-internal-keyboard',
               connection='internal', simulated=True),
        Device('sim:review-touchpad', 'Touchpad', 'mouse', 'simulation', 'review-touchpad',
               physical='/fixture/i2c-touchpad', vid='04f3', connection='internal', simulated=True),
        Device('sim:review-headset', 'Headset', 'audio', 'simulation', 'review-headset',
               connection='bluetooth', simulated=True, capabilities=battery(78)),
        Device('sim:review-hdmi', 'HDMI DisplayPort', 'audio', 'simulation', 'review-hdmi',
               connection='audio', simulated=True),
        Device('sim:review-unknown', 'Unknown device', 'input', 'simulation', 'review-unknown',
               connection='usb', simulated=True),
    ]
    rows[1].capabilities = [Capability('lighting_mode','simulation',True,True,True,value='color',source='simulation'), Capability('profiles','simulation',True,True,True,value=0,source='simulation')]
    rows[4].capabilities.append(Capability('volume','simulation',True,True,True,value=50,source='simulation'))
    rows.extend([
        Device('sim:review-bt','Bluetooth audio','audio','simulation','review-bt',connection='bluetooth',simulated=True),
        Device('sim:review-g502-control','Logitech G502 HERO','mouse','ratbagctl','review-g502-control',connection='usb',simulated=True,capabilities=[Capability('dpi','ratbagctl',True,True,True,value=1600,source='simulation')]),
        Device('sim:review-g502-info','Logitech G502 HERO','mouse','solaar','review-g502-info',connection='usb',simulated=True),
    ])
    rows[2].keyboard_layout = 'laptop'
    rows[3].input_subtype = 'touchpad'
    rows[4].audio_subtype = 'headset'
    rows[5].audio_subtype = 'display_hdmi'
    from logi_center.core.devices.device_presentation import SIMULATION_NAMES
    SIMULATION_NAMES.update({
        'review-mouse': 'MCHOSE K7 Ultra · SIM', 'review-ace': 'MCHOSE Ace68-II · SIM',
        'review-internal-keyboard': 'Встроенная клавиатура', 'review-touchpad': 'Встроенная сенсорная панель',
        'review-headset': 'Гарнитура', 'review-hdmi': 'HDMI / DisplayPort',
        'review-unknown': 'Неизвестное устройство', 'review-bt':'Bluetooth-аудио',
        'review-g502-control':'Logitech G502 HERO · SIM','review-g502-info':'Logitech G502 HERO · SIM',
    })
    manager = DeviceManager()
    manager.devices = rows
    return {'manager': manager}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=('before', 'after'), default='after')
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    if args.worker:
        from unittest.mock import patch
        from logi_center.qml_ui.main import run
        with patch('logi_center.core.discovery.device_service.collect_device_snapshot', fixture_snapshot):
            return run(['illustration-dashboard', '--simulate', '--smoke'])
    base = ROOT / 'docs/screenshots/redesign/illustrations' / args.stage
    for language in ('ru', 'en'):
        target = base / language
        if args.stage == 'before' and target.exists():
            print(f'Preserved existing baseline: {target}')
            continue
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='generic',
                   LOGI_CENTER_QML_SCREENSHOT_DIR=str(target), LOGI_CENTER_QML_LANGUAGE=language,
                   LOGI_CENTER_QML_WIDTHS='800,1000,1280,1600,1920', LOGI_CENTER_QML_CAPTURE_ALL='1',
                   LOGI_CENTER_QML_ART_METRICS='1')
        result = subprocess.run([sys.executable, __file__, '--worker'], cwd=ROOT, env=env, timeout=90)
        if result.returncode:
            return result.returncode
        if args.stage == 'after':
            metrics = json.loads((target / 'artwork-metrics.json').read_text())
            if set(metrics) != {'800','1000', '1280', '1600', '1920'}:
                raise SystemExit('FAIL: missing Dashboard occupancy measurements')
            for width, rows in metrics.items():
                if len(rows)!=10:raise SystemExit(f'FAIL: missing cards at {width}px')
                for row in rows:
                    if row['clipped']:raise SystemExit(f'FAIL: clipped silhouette at {width}px: '+row['name'])
                    if row['family']=='mouse' and not .745<=row['height_fraction']<=.845:raise SystemExit('FAIL: undersized mouse')
                    if row['family']=='keyboard' and not .835<=row['width_fraction']<=.865:raise SystemExit('FAIL: undersized keyboard')
            print(f'PASS: {language}: ten device silhouettes unclipped; mouse75–84% scene height, keyboard~85% scene width; five widths.')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
