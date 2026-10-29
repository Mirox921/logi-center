"""libratbag inventory and capability projection over existing commands."""
import re
from logi_center.core.services.execution import Fault, FaultCode
from logi_center.core.devices.devices import Device, DeviceManager
from logi_center.core.capabilities.model import Capability
from logi_center.core.discovery.identity import identity, usb_identity

class RatbagAdapter:
    name='ratbagctl'
    def __init__(self,runner=None,detailed=False,model_lookup=None):
        from logi_center.adapters.external.backend import run
        self.run=runner or run;self.detailed=detailed;self.model_lookup=model_lookup
    def discover(self):
        from logi_center.adapters.external.backend import mouse_list,read_mouse
        records=[]
        inventory=mouse_list(self.run(['ratbagctl','list']))
        models={}
        if inventory and self.model_lookup:
            try:models=self.model_lookup()
            except Exception:pass  # Optional daemon metadata; keep records distinct.
        for index,(target,name) in enumerate(inventory):
            if sum(item[0]==target for item in inventory)>1:
                records.append(Device('ratbag:ambiguous:'+target+':'+str(index),name,'mouse',self.name,target,connected=None,faults=[Fault(FaultCode.CONFIG,self.name,'Backend selector collision; writes disabled')]))
                continue
            if not self.detailed:
                unique_name=sum(item[1]==name for item in inventory)==1
                vid,pid=models.get(name,('','')) if unique_name else ('','')
                records.append(Device('ratbag:'+target,name,'mouse',self.name,target,vid=vid,pid=pid));continue
            try:
                data=read_mouse(target,runner=self.run);caps=mouse_capabilities(data,target)
                model=re.search(r'Model:\s*(\S+)',data['text']);parts=model[1].split(':') if model else []
                vid,pid=(parts[1:3] if len(parts)>=3 else ('',''))
                records.append(Device('ratbag:'+target,name,'mouse',self.name,target,vid=vid,pid=pid,capabilities=caps))
            except Exception as error:
                from logi_center.core.services.diagnostics import fault_for
                records.append(Device('ratbag:'+target,name,'mouse',self.name,target,connected=None,faults=[fault_for(error,self.name)]))
        return records


def mouse_capabilities(data,target=""):
    active=next((p for p in data.get('profiles',[]) if p['index']==data.get('active')),None)
    if active is None:return []
    result=[]
    def add(name,value,writable,choices=(),limitation=''):
        result.append(Capability(name,'ratbagctl',True,True,writable,False,value,'backend_cache',choices=list(choices),limitation=limitation or 'ratbagd properties may be cached; physical writes are unverified.',evidence=['software_detected','read_observed']))
    if data.get('dpis') and active.get('resolutions'):add('dpi',[r['dpi'] for r in active['resolutions']],True,data['dpis'])
    if data.get('rates'):add('polling_rate',active.get('rate'),True,data['rates'])
    if len(data.get('profiles',[]))>1:add('profiles',data.get('active'),True,[p['index'] for p in data['profiles']])
    if active.get('buttons'):
        types=data.get('button_types',{});add('buttons',len(active['buttons']),bool(types))
        add('macros',None,any(4 in t for t in types.values()),limitation='Editing requires ActionTypes=macro on each selected button; unknown is read-only.')
    if active.get('leds'):add('lighting',len(active['leds']),any(data.get('led_modes',{}).values()))
    if target:
        from logi_center.core.services.operations import plan_for
        base=['ratbagctl',target,'profile',str(active['index'])]
        resolution=next((r for r in active.get('resolutions',[]) if r['active']),None)
        for cap in result:
            if cap.name=='dpi' and resolution:
                cap.value=resolution['dpi'];cap.plan=lambda value,b=base,r=resolution:plan_for([*b,'resolution',str(r['index']),'dpi','set',str(value)])
            elif cap.name=='polling_rate':cap.plan=lambda value,b=base:plan_for([*b,'rate','set',str(value)])
            elif cap.name=='profiles':cap.plan=lambda value,t=target:plan_for(['ratbagctl',t,'profile','active','set',str(value)])
    return result
