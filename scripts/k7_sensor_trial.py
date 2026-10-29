#!/usr/bin/env python3
"""Explicit, reversible K7 sensor trial. Never imported by the application.

Requires separate user approval of this physical experiment. A confirmation
argument is an accidental-launch guard, not a replacement for that approval.
"""
from pathlib import Path
import argparse
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mchose_adapter import candidates,selector,hardware
from k7_settings import unchanged


def trial(field,read,write):
    """Toggle one known flag, read back, then restore only that flag.

    Each write delegates to the existing private snapshot and native guards.
    Never restore a full record or blindly retry after a transport failure.
    """
    original=read()
    if (original['identity'].get('vid'),original['identity'].get('pid'))!=(0x3837,0x4150):
        raise ValueError('Exact K7 Ultra identity is required')
    bit={'motion_sync':16,'ripple':4,'angle_snap':8}[field]
    before=original['sensor_config'][field]
    observed=None
    try:
        write(original,field,not before)
    finally:
        # One fresh read can determine whether restoration is necessary even
        # when a setting command's response failed. No guessed recovery writes.
        observed=read()
        if not unchanged(original['raw'],observed['raw'],{3:255,17:bit}):
            raise RuntimeError('Unexpected configuration change; no automatic restoration. Private snapshot retained.')
        if observed['identity'].get('mode')!=original['identity'].get('mode'):
            raise RuntimeError('Connection mode changed; no automatic restoration. Private snapshot retained.')
        if observed['sensor_config'][field]!=before:
            write(observed,field,before)
            restored=read()
            if not unchanged(original['raw'],restored['raw'],{3:255}):
                raise RuntimeError('Restoration is not confirmed; inspect the private snapshot before further writes.')
    if observed['sensor_config'][field]==before:raise RuntimeError('The requested toggle did not read back; no retry was made.')
    return {'field':field,'original':before,'test':not before,'readback':True,'restored':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--field',required=True,choices=['motion_sync','ripple','angle_snap'])
    parser.add_argument('--confirm',required=True,choices=['K7-SENSOR-RESTORE'])
    args=parser.parse_args()
    items=[c for c in candidates() if (c['vid'],c['pid'])==('3837','1001') and 'K7 Ultra' in c['name']]
    if len(items)!=1:raise SystemExit('A unique K7 Ultra receiver interface is required')
    target=selector(items[0])
    def read():return hardware('read',target)
    def write(state,field,value):
        return hardware('set',target,'sensor_config',{'changes':{field:value},'expected_raw':state['raw'],
                                                      'expected_mode':state['identity']['mode']})
    import json
    print(json.dumps(trial(args.field,read,write),sort_keys=True))


if __name__=='__main__':main()
