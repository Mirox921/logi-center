"""rivalcfg profile-driven safe scalar subset; never treat defaults as readback."""
import json,os
from pathlib import Path
from logi_center.core.devices.devices import Device
from logi_center.core.capabilities.model import Capability
from logi_center.core.discovery.identity import identity, usb_identity
from logi_center.core.services.execution import Fault,FaultCode
from logi_center.core.services.operations import Plan


def inventory(profiles,enumerate_hid):
    result=[]
    for (vid,pid),profile in profiles.items():
        endpoints=[i for i in enumerate_hid(vid,pid) if i.get('interface_number')==profile['endpoint']]
        for item in endpoints:
            path=item['path'].decode() if isinstance(item['path'],bytes) else item['path']
            settings={}
            for name,setting in profile.get('settings',{}).items():
                # No reset/save/profile/button commands. Multistage DPI replacement
                # needs a dedicated preview before it can be exposed safely.
                if name not in ['sensitivity','sensitivity1','sensitivity2','polling_rate','angle_snapping']:continue
                kind=setting.get('value_type');choices=list(setting.get('choices',{})) if kind=='choice' else []
                bounds=setting.get('input_range') if kind=='range' else None
                settings[name]={'choices':choices,'bounds':bounds,'writable':bool(choices or bounds),'label':setting.get('label',name)}
            result.append({'target':identity(path+'|'+str((Path('/sys/class/hidraw')/path.rsplit('/',1)[-1]/'device').resolve())),'path':path,'name':profile['name'],'vid':f'{vid:04x}','pid':f'{pid:04x}','settings':settings,'ambiguous':len(endpoints)!=1})
    return result


def hardware(action,target=None,field=None,value=None):
    # Disable upstream debug/dry profiles so real and simulated hardware cannot mix.
    for name in ['RIVALCFG_PROFILE','RIVALCFG_DRY','RIVALCFG_DEBUG_NO_COMMAND_DELAY']:os.environ.pop(name,None)
    from rivalcfg import devices,mouse
    import hid
    records=inventory(devices.PROFILES,hid.enumerate)
    if action=='discover':return records
    matches=[r for r in records if r['target']==target]
    if len(matches)!=1:raise Fault(FaultCode.DISCONNECTED,'rivalcfg','Exact HID interface is absent')
    record=matches[0]
    if action=='read':return record
    if action!='set' or field not in record['settings']:raise Fault(FaultCode.BACKEND_UNSUPPORTED,'rivalcfg','No implemented operation')
    setting=record['settings'][field]
    if record['ambiguous']:raise Fault(FaultCode.CONFIG,'rivalcfg','Public factory cannot select between identical units; writes disabled')
    if not setting['writable']:raise Fault(FaultCode.BACKEND_UNSUPPORTED,'rivalcfg','Setting requires a dedicated editor')
    choices=setting['choices'];bounds=setting['bounds']
    if choices and value not in choices:raise ValueError('Value outside profile choices')
    if bounds and (type(value) is not int or not bounds[0]<=value<=bounds[1] or (value-bounds[0])%bounds[2]):raise ValueError('Value outside profile range/step')
    # Re-enumeration above prevents routing a stale selector by VID/PID alone.
    with mouse.get_mouse(int(record['vid'],16),int(record['pid'],16)) as device:getattr(device,'set_'+field)(value)
    return None


class RivalcfgAdapter:
    name='rivalcfg'
    def __init__(self,runner=None):
        from logi_center.adapters.external.backend import run
        self.run=runner or run
    def discover(self):
        result=[]
        for state in json.loads(self.run(['logi-sdk','rivalcfg','discover'])):
            caps=[]
            for field,setting in state['settings'].items():
                bounds=setting['bounds'];writable=setting['writable'] and not state['ambiguous']
                cap=Capability(field,self.name,True,False,writable,False,None,'unavailable',choices=setting['choices'],minimum=bounds[0] if bounds else None,maximum=bounds[1] if bounds else None,limitation='Write-only API: current settings are not read; profile defaults are not current values. Identical units disable writes.',label=setting['label'])
                if bounds:cap.step=bounds[2]
                if writable:cap.plan=lambda value,t=state['target'],f=field:Plan(['logi-sdk','rivalcfg','set',t,f,json.dumps(value)],value,target=t)
                caps.append(cap)
            physical,vid,pid=usb_identity('/sys/class/hidraw/'+state['path'].rsplit('/',1)[-1]+'/device')
            result.append(Device('rivalcfg:'+state['target'],state['name'],'mouse',self.name,state['target'],physical,state['vid'],state['pid'],'usb',True,caps))
        return result
