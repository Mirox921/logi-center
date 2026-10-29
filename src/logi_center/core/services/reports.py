"""Allowlisted public diagnostic schema; no values, macros or private identities."""
from datetime import datetime,timezone
import re
from logi_center.core.services.execution import redact

def public_name(text):
    text=redact(text)
    text=re.sub(r"(?i)\b(?:s/n|sn|serial(?: number)?)\s*[:=#-]\s*[\w-]+","[serial]",text)
    text=re.sub(r"\b(?=[A-Za-z0-9_-]{8,}\b)(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]+\b","[identifier]",text)
    text=re.sub(r'\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b','[address]',text)
    text=re.sub(r'\b[0-9A-Fa-f]{8,}\b','[identifier]',text)
    text=re.sub(r'\S+@\S+','[address]',text)
    text=re.sub(r'(?:~|/)[^\s]+','[path]',text)
    return text[:160]

def build_report(manager,components=()):
    devices=[]
    for index,device in enumerate(manager.devices):
        caps=[]
        for cap in device.capabilities:
            # Never export values, endpoint names, arbitrary choices, macros or drafts.
            choices=[v for v in cap.choices if type(v) in [int,float,bool] or v in ['off','on','cycle','breathing']][:128]
            caps.append({'setting':cap.name.rsplit(':',1)[-1] if ':' in cap.name else public_name(cap.name),'backend':cap.backend,'supported':cap.supported,'readable':cap.readable,'writable':cap.writable,'verifiable':cap.verifiable,'source':cap.source,'observed_at':cap.observed_at,'minimum':cap.minimum,'maximum':cap.maximum,'step':cap.step,'choices':choices,'evidence':list(cap.evidence),'last_operation':{k:v for k,v in cap.last_operation.items() if k in ['state','source','at']},'limitation':public_name(cap.limitation)})
        devices.append({'report_id':index+1,'model':public_name(device.name) if device.kind!='audio' or device.backend=='headsetcontrol' else 'Audio endpoint','kind':device.kind,'vid':device.vid if re.fullmatch('[0-9a-fA-F]{4}',device.vid) else '', 'pid':device.pid if re.fullmatch('[0-9a-fA-F]{4}',device.pid) else '', 'connection':device.connection,'connected':device.connected,'backends':device.backends,'simulated':device.simulated,'capabilities':caps,'faults':[{'component':f.component,'code':f.code.value} for f in device.faults]})
    return {'format':'logi-center-public-diagnostics','version':1,'created_at':datetime.now(timezone.utc).isoformat(),'devices':devices,'components':[{'component':public_name(c['component']),'state':c['state'],'description':public_name(c['description'])} for c in components],'discovery_faults':[{'component':f.component,'code':f.code.value} for f in manager.faults],'privacy':'No serials, bus paths, endpoint identifiers, user IDs, setting values, macros, drafts or recordings are included. Review before sharing.'}
