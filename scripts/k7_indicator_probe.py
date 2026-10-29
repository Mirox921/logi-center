"""Read-only K7 Ultra link, charge, DPI and receiver RGB observations.

Run while placing/removing the mouse on its dock or pressing its DPI button.
Only documented GET_FEATURE requests are sent; no setting command is issued.
"""
# Allow direct execution without installing developer tools.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import scripts  # source-package bootstrap
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from logi_center.adapters.mchose.mchose_adapter import Transport, candidates, decode  # noqa: E402


def snapshot(device):
    identity = device.exchange(0x11, 0x06)
    result = {'mouse_link': False, 'battery': None, 'charging': None,
              'profile': None, 'dpi': None, 'dpi_stage': None, 'rgb_effect_id': None}
    # The RGB record belongs to the K7 receiver interface. Its physical LED
    # target is deliberately not inferred here.
    rgb = device.exchange(0x11, 0x1b)
    if len(rgb) >= 15:
        result['rgb_effect_id'] = rgb[1]
    if len(identity) < 11 or not any(identity[:4]) or not identity[8] & 8:
        return result
    vid = int.from_bytes(identity[:2], 'little')
    pid = int.from_bytes(identity[2:4], 'little')
    if (vid, pid) != (0x3837, 0x4150):
        raise ValueError('Receiver reports a different mouse; K7 probe stopped')
    result['mouse_link'] = True
    result['battery'] = identity[9] if identity[9] <= 100 else None
    result['charging'] = bool(identity[10]) if identity[10] in (0, 1) else None
    state = decode(device.exchange(0x12, 0x67),
                   {'mode': identity[8] & 7, 'battery': result['battery'],
                    'charging': result['charging']})
    result.update(profile=state['profiles'] + 1, dpi=state['dpi'],
                  dpi_stage=state['stage'] + 1)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=1, help='1–30 observations')
    parser.add_argument('--interval', type=float, default=2, help='seconds between observations, at least 0.5')
    args = parser.parse_args(argv)
    if not 1 <= args.samples <= 30 or args.interval < .5:
        parser.error('samples must be 1–30 and interval at least 0.5 s')
    found = [item for item in candidates() if (item['vid'], item['pid']) == ('3837', '1001')]
    if len(found) != 1:
        parser.error(f'expected one K7 Ultra receiver, found {len(found)}')
    for index in range(args.samples):
        try:
            with Transport(found[0]['node']) as device:
                state = snapshot(device)
            print(json.dumps(state, ensure_ascii=False, sort_keys=True), flush=True)
        except Exception as error:
            print(json.dumps({'error': str(error)}, ensure_ascii=False), flush=True)
            return 1
        if index + 1 < args.samples:
            time.sleep(args.interval)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
