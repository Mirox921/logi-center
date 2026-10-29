"""File entry point for bounded workers, independent of cwd/PYTHONPATH."""
from pathlib import Path
import runpy
import sys


def main():
    modules = {
        'sdk': 'logi_center.adapters.external.sdk_worker',
        'solaar': 'logi_center.adapters.logitech.solaar_write',
    }
    if len(sys.argv) < 2 or sys.argv[1] not in modules:
        raise SystemExit('Unknown Logi Center worker')
    module = modules[sys.argv.pop(1)]
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    runpy.run_module(module, run_name='__main__')


if __name__ == '__main__':
    main()
