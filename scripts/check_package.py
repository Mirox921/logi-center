#!/usr/bin/env python3
"""Exercise a built wheel outside the checkout with isolated simulated devices."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheel', type=Path)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='logi-wheel-') as folder:
        target=Path(folder)/'site';target.mkdir()
        with zipfile.ZipFile(args.wheel) as wheel:
            names=wheel.namelist()
            assert not any(name.startswith(('tests/', 'scripts/')) for name in names)
            assert all(not Path(name).is_absolute() and '..' not in Path(name).parts for name in names)
            wheel.extractall(target)
        env=dict(os.environ, PYTHONPATH=str(target), QT_QPA_PLATFORM='offscreen',
                 QT_QPA_PLATFORMTHEME='generic', QT_QUICK_BACKEND='software')
        for flags in (['--version'], ['--simulate', '--smoke']):
            subprocess.run([sys.executable, '-m', 'logi_center', *flags],
                           cwd=folder, env=env, check=True, timeout=60)
        worker=target/'logi_center/_worker.py'
        result=subprocess.run([sys.executable, str(worker), 'sdk', 'unknown-test-adapter', 'discover'],
                              cwd=folder, env=dict(env, PYTHONPATH=''), check=True,
                              capture_output=True, text=True, timeout=10)
        import json
        assert json.loads(result.stdout)['code']=='backend_unsupported'
    print('PASS: wheel CLI, QML/resources and isolated worker outside the checkout; no hardware I/O.')


if __name__ == '__main__':
    main()
