"""One-shot K7 Ultra RGB target test with private snapshot and restoration.

The trial briefly selects M HUB's native static-red effect on the validated
K7 receiver, then restores the exact original 15-byte RGB record. It does not
modify DPI, buttons, profiles or firmware. The person observing the mouse and
dock must note which physical light changes; HID readback is not optical proof.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drafts import atomic_json  # noqa: E402
from mchose_adapter import Transport, candidates, identity  # noqa: E402


def rgb_record(device):
    record = bytes(device.exchange(0x11, 0x1b))
    if len(record) < 15:
        raise ValueError('K7 RGB record is shorter than the documented 15 fields')
    return record[:15]


def trial(device, original, seconds=3, pause=time.sleep, settle=time.sleep):
    """Send exactly one test effect and one restore; no blind write retries."""
    if len(original) != 15:
        raise ValueError('Expected the complete K7 RGB record')
    proposed = bytearray(original)
    proposed[0] = 1             # enable
    proposed[1] = 6             # native static effect, per M HUB K7 path
    proposed[3] = 100           # brightness, within M HUB 0..100 UI range
    proposed[8:11] = b'\xff\x00\x00'  # first RGB triplet
    write_started = False
    try:
        write_started = True
        device.exchange(0x11, 0x2b, bytes(proposed), reply=False)
        settle(.08)
        applied = rgb_record(device)
        if any(applied[i] != proposed[i] for i in (0, 1, 3, 8, 9, 10)):
            raise RuntimeError('RGB readback differed; restoring original mode')
        pause(seconds)
        return applied
    finally:
        if write_started:
            device.exchange(0x11, 0x2b, original, reply=False)
            settle(.08)
            restored = rgb_record(device)
            if restored != original:
                raise RuntimeError('Original RGB record did not read back exactly; inspect the dock before another trial')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=int, default=3)
    parser.add_argument('--confirm', required=True,
                        help='type K7-STATIC-RED-RESTORE to acknowledge the temporary RGB change')
    args = parser.parse_args(argv)
    if args.confirm != 'K7-STATIC-RED-RESTORE' or not 1 <= args.seconds <= 10:
        parser.error('confirmation or duration invalid')
    found = [item for item in candidates() if (item['vid'], item['pid']) == ('3837', '1001')]
    if len(found) != 1 or 'K7 Ultra' not in found[0]['name']:
        parser.error('exactly one K7 Ultra receiver is required')
    item = found[0]
    with Transport(item['node']) as device:
        state = device.read()  # validates connected logical K7 identity
        if (state['identity']['vid'], state['identity']['pid']) != (0x3837, 0x4150):
            raise RuntimeError('K7 logical identity mismatch; no RGB write sent')
        original = rgb_record(device)
        path = (Path.home()/'.local/state/logi-center/backups'/
                ('mchose-'+identity(item['physical']))/(str(time.time_ns())+'-rgb.json'))
        atomic_json(path, {'format':'k7-ultra-observed-rgb','version':1,'source':'device',
                           'created_at':datetime.now(timezone.utc).isoformat(),
                           'rgb_record':list(original),'config':state})
        print('Private pre-write snapshot saved. Observe the mouse and dock during the red interval.', flush=True)
        trial(device, original, args.seconds)
    print(json.dumps({'sent':'static red','readback':'matched','restored':'original RGB record',
                      'optical_result':'requires observation'}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
