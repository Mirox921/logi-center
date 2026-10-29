#!/usr/bin/env python3
"""Scoped G515 read evidence; no complete Solaar enumeration, palettes or writes."""
if __package__ in (None, ''):
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import scripts
import argparse,os,time
from pathlib import Path
from logi_center.adapters.logitech.g515_adapter import read_snapshot
from logi_center.core.services.execution import Fault


def collect(target='G515 LS TKL',runner=None):
    from logi_center.adapters.external.backend import run
    from logi_center.adapters.logitech.g515_adapter import READ_KEYS
    report={'format':'logi-center-g515-read-evidence','version':1,'reads':[]}
    def scoped(args,**kwargs):
        if len(args)!=4 or args[:2]!=['solaar','config'] or args[3] not in READ_KEYS:
            raise ValueError('Only allowlisted single-setting reads are permitted')
        started=time.monotonic();row={'setting':args[3]};report['reads'].append(row)
        try:
            text=(runner or run)(args,**kwargs)
            row.update(state='returned',stdout_bytes=len(text.encode('utf-8')))
            return text
        except Fault as error:
            row.update(state='failed',code=error.code.value);raise
        finally:row['elapsed_ms']=round((time.monotonic()-started)*1000,1)
    try:
        snapshot=read_snapshot(target,runner=scoped)
    except Fault as error:
        report.update(state='failed',error={'component':error.component,'code':error.code.value});return report
    saved=snapshot['saved'];sources=snapshot['sources']
    report.update(state='read_complete' if snapshot['reachable'] else 'cache_only',
        rgb_capabilities=snapshot.get('rgb_capabilities'),
        rgb_control={'value':saved.get('rgb_control'),'source':sources.get('rgb_control','unavailable')},
        brightness={'value':saved.get('brightness_control'),'source':sources.get('brightness_control','unavailable')},
        errors=[{'component':e.component,'code':e.code.value} for e in snapshot['errors']],
        effect_source=sources.get('rgb_zone_1','unavailable'),persistence='unverified')
    # Effects are settings, not proof of LED output. Exclude arbitrary strings,
    # colors, palettes, keys, config records and every device selector.
    effect=saved.get('rgb_zone_1',{})
    report['effect']={}
    if isinstance(effect,dict):
        for key in ('ID','period','intensity','saturation','direction','speed'):
            try:value=int(str(effect[key]),0)
            except (KeyError,TypeError,ValueError):continue
            if 0<=value<=65535:report['effect'][key]=value
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',default='G515 LS TKL',help='Exact known Solaar device selector; not exported')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();os.umask(0o077)
    report=collect(args.target)
    from logi_center.core.services.drafts import atomic_json
    atomic_json(args.output,report)
    print('G515 read diagnostic:',report['state'],'—',args.output)


if __name__=='__main__':main()
