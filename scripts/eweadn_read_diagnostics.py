#!/usr/bin/env python3
"""Bounded S9 page-read trace. No configuration setters, raw reports or identities."""
if __package__ in (None, ''):
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import scripts
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from logi_center.adapters.eweadn.eweadn_adapter import candidates,selector
from logi_center.core.services.execution import _stop

DEADLINE=20
PREFIX='LOGI_EWEADN_TRACE '


def trace_events(text):
    if isinstance(text,bytes):text=text.decode('utf-8',errors='replace')
    events=[]
    allowed={'event','elapsed_ms','page','chunk','offset','attempt','required','size','reason','count','code','expected','actual'}
    for line in (text or '').splitlines():
        if not line.startswith(PREFIX):continue
        try:row=json.loads(line[len(PREFIX):])
        except ValueError:continue
        if isinstance(row,dict):events.append({k:v for k,v in row.items() if k in allowed})
    return events[-1024:]


def collect(device_index=1,inventory=None,popen=subprocess.Popen):
    items=candidates() if inventory is None else inventory
    report={'format':'logi-center-eweadn-read-trace','version':1,'worker_deadline_s':DEADLINE,
            'configuration_interfaces':len(items),'interfaces':[{'vid':i['vid'],'pid':i['pid']} for i in items]}
    if not 1<=device_index<=len(items):
        report['state']='no_matching_interface';return report
    import logi_center
    worker=Path(logi_center.__file__).resolve().parent/'_worker.py'
    args=[sys.executable,str(worker),'sdk','eweadn','diagnose',selector(items[device_index-1])]
    started=time.monotonic()
    process=popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    try:
        out,err=process.communicate(timeout=DEADLINE)
        report['events']=trace_events(err)
        report['worker_exit_code']=process.returncode
        try:reply=json.loads(out)
        except ValueError:reply={}
        if reply.get('ok') is True:
            report['state']=reply['value'].get('state','invalid_reply')
        else:report['state']=reply.get('code','worker_failed')
    except subprocess.TimeoutExpired as error:
        report['events']=trace_events(error.stderr)
        _stop(process)
        report['state']='worker_deadline'
    except BaseException:
        _stop(process);raise
    report['elapsed_ms']=round((time.monotonic()-started)*1000,1)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device',type=int,default=1,help='1-based matching interface index, not a hidraw path')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    os.umask(0o077)
    report=collect(args.device)
    from logi_center.core.services.drafts import atomic_json
    atomic_json(args.output,report)
    print('S9 read diagnostic:',report['state'],'—',args.output)


if __name__=='__main__':main()
