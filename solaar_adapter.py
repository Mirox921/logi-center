"""Explicit single-setting probes through Solaar's scoped CLI adapter.

Startup uses local configuration only. Probes never enumerate all settings;
only boolean/choice fields with reported legal values become writable.
"""
import re
from devices import Capability
from backend import run,solaar_settings
from operations import Plan,Observation
from execution import Fault,FaultCode

def selector(record):
    for key in ['_serial','_unitId']:
        value=record.get(key)
        if isinstance(value,str) and re.fullmatch('[A-Za-z0-9]{4,64}',value):return value
    return None

def probe(record,runner=None):
    runner=runner or run;target=selector(record)
    if not target:raise Fault(FaultCode.CONFIG,'solaar','No unambiguous saved device selector is available')
    capabilities=[];faults=[]
    for key,value in record.items():
        if key.startswith('_') or not re.fullmatch('[a-z][a-z0-9_-]{0,63}',key) or isinstance(value,(dict,list)):continue
        try:
            text=runner(['solaar','config',target,key])
            setting=next((s for s in solaar_settings(text) if s['key']==key),None)
            if not setting or setting['value'].startswith('?'):continue
            choices=setting.get('choices') or []
            risky=any(token in key.replace('-','_') for token in ['reset','firmware','erase','bootloader','pairing','onboard_profiles'])
            current=setting['value'].lower() if choices==['true','false'] else setting['value']
            # RGB/map/key-remapping blobs require a separate parameter adapter.
            capabilities.append(Capability(key,'solaar',True,True,bool(choices) and not risky,bool(choices) and not risky,current,'device',choices=choices,evidence=['software_detected','read_observed'],limitation='Potentially destructive/profile-mode setting; writing is disabled.' if risky else '' if choices else 'No enumerated legal values; read-only.'))
        except Fault as fault:faults.append(fault)
    for cap in capabilities:
        if cap.writable:cap.plan=lambda value,c=cap:choice_plan(target,c,value)
    return target,capabilities,faults

def choice_plan(target,capability,value):
    if not capability.writable or value not in capability.choices:raise Fault(FaultCode.BACKEND_UNSUPPORTED,'solaar','Value is outside the probed choices')
    args=['solaar','config',target,capability.name,value]
    def reader(runner):
        settings=solaar_settings(runner(args[:4]));actual=next((s['value'] for s in settings if s['key']==capability.name),None)
        if actual is None or actual.startswith('?'):raise Fault(FaultCode.CONNECTION,'solaar','Setting readback unavailable')
        if capability.choices==['true','false']:actual=actual.lower()
        return Observation(actual,'device')
    return Plan(args,value,reader)
