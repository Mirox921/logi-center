#!/usr/bin/env python3
"""Scoped G515 read evidence; no complete Solaar enumeration, palettes or writes."""
if __package__ in (None, ''):
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import scripts
import argparse,os,time
from pathlib import Path
from logi_center.adapters.logitech.g515_adapter import read_snapshot,battery_from_text
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
            if args[3]=='brightness_control':report['battery']=battery_from_text(text)
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


def input_evidence(input_factory=None,battery_factory=None):
    """Ordinal identity relationships, never serials, paths or arbitrary names."""
    from logi_center.adapters.external.linux_input import InputAdapter,KernelBatteryAdapter
    inputs=(input_factory or InputAdapter)().discover()
    supplies=(battery_factory or KernelBatteryAdapter)().discover()
    parents={};units={};hids={}
    def group(table,value):
        if not value:return None
        if value not in table:table[value]=len(table)+1
        return table[value]
    rows=[]
    for device in inputs:
        if device.vid!='046d' or 'g515' not in device.name.casefold():continue
        private=device.private_identity
        rows.append({'kind':device.kind,'vid':device.vid,'pid':device.pid,
            'connection':device.connection,'usb_parent':group(parents,private.get('usb_parent')),
            'hid_parent':group(hids,private.get('hid_parent')),
            'paired_identity':group(units,private.get('solaar_serial')),
            'transport_parent_count':len(private.get('usb_parents',[]))})
        for parent in private.get('usb_parents',[]):group(parents,parent)
    battery=[]
    for device in supplies:
        if device.physical not in parents:continue
        status=next((c.value for c in device.capabilities if c.name=='charging'),None)
        battery.append({'usb_parent':parents[device.physical],'charging':status})
    return {'devices':rows,'power_supplies':battery}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',default='G515 LS TKL',help='Exact known Solaar device selector; not exported')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();os.umask(0o077)
    report=collect(args.target)
    report['input_evidence']=input_evidence()
    from logi_center.core.services.drafts import atomic_json
    atomic_json(args.output,report)
    print('G515 read diagnostic:',report['state'],'—',args.output)


if __name__=='__main__':main()
