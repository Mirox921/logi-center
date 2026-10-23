"""Optional loopback OpenRGB SDK provider. SDK state is cache, not hardware proof."""
import json
from pathlib import Path
from devices import Device,Capability,identity,usb_identity,serial_usb_identity
from execution import Fault,FaultCode
from operations import Plan,Observation


def key(device):
    metadata=device.metadata
    # Keep full identity private. Never route by mutable controller index alone.
    return identity('|'.join(str(x) for x in [device.name,metadata.location,metadata.serial,device.type]))


def active_mode(device):
    index=device.active_mode
    return device.modes[index] if type(index) is int and 0<=index<len(device.modes) else None

def describe(device):
    modes=[{'name':m.name,'id':m.id,'index':i,'flags':int(m.flags),'color_mode':int(m.color_mode),'brightness':m.brightness,'minimum':m.brightness_min,'maximum':m.brightness_max} for i,m in enumerate(device.modes)]
    active=next((m for m in modes if m['index']==device.active_mode),None)
    active_object=active_mode(device)
    palette=active_object.colors if active_object is not None and int(active_object.color_mode)==2 else device.colors
    colors=[[c.red,c.green,c.blue] for c in (palette or [])]
    physical,vid,pid=serial_usb_identity(device.metadata.serial)
    result={'physical':physical,'vid':vid,'pid':pid,'target':key(device),'name':device.name,'kind':{5:'keyboard',6:'mouse',8:'headset'}.get(int(device.type),'rgb'),'location':device.metadata.location,'modes':modes,'lighting_mode':active['name'] if active else None,'brightness':active['brightness'] if active else None,'lighting':colors[0] if colors and all(c==colors[0] for c in colors) else None,'zones':[{'name':z.name,'leds':len(z.leds),'setting':'lighting_zone_'+identity(str(i)+'|'+z.name)} for i,z in enumerate(device.zones)]}
    for meta,zone in zip(result['zones'],device.zones):
        colors=[[c.red,c.green,c.blue] for c in zone.colors]
        result[meta['setting']]=colors[0] if colors and all(c==colors[0] for c in colors) else None
    return result


def hardware(action,target=None,field=None,value=None,factory=None):
    if factory is None:
        from openrgb import OpenRGBClient
        factory=OpenRGBClient
    client=factory(address='127.0.0.1',port=6742,name='Logi Center')
    try:
        items=[describe(d) for d in client.devices]
        if action=='discover':return items
        indices=[i for i,item in enumerate(items) if item['target']==target]
        if len(indices)!=1:raise Fault(FaultCode.DISCONNECTED if not indices else FaultCode.CONFIG,'openrgb','Controller absent or identity ambiguous')
        device=client.devices[indices[0]];state=items[indices[0]]
        if action=='read':return state
        if action!='set':raise ValueError('Unknown SDK operation')
        if field=='lighting_mode':
            if [m['name'] for m in state['modes']].count(value)!=1:raise ValueError('Unsupported or ambiguous RGB mode')
            device.set_mode(value,save=False)
        elif field=='brightness':
            mode=active_mode(device)
            if mode is None or not int(mode.flags)&16 or mode.brightness_min is None or mode.brightness_max is None:raise Fault(FaultCode.BACKEND_UNSUPPORTED,'openrgb','Active mode has no brightness control')
            if type(value) is not int or not min(mode.brightness_min,mode.brightness_max)<=value<=max(mode.brightness_min,mode.brightness_max):raise ValueError('Brightness outside mode range')
            mode.brightness=value;device.set_mode(mode,save=False)
        elif field=='lighting' or field.startswith('lighting_zone_'):
            mode=active_mode(device)
            if mode is None or not int(mode.flags)&(32|64) or int(mode.color_mode) not in [1,2]:raise Fault(FaultCode.BACKEND_UNSUPPORTED,'openrgb','Active mode has no editable colors')
            if not isinstance(value,list) or len(value)!=3 or any(type(c) is not int or not 0<=c<=255 for c in value):raise ValueError('Expected RGB channels 0..255')
            from openrgb.utils import RGBColor
            if field=='lighting':device.set_color(RGBColor(*value))
            else:
                zones=[z for z,m in zip(device.zones,state['zones']) if m['setting']==field]
                if len(zones)!=1 or int(mode.color_mode)!=1:raise Fault(FaultCode.BACKEND_UNSUPPORTED,'openrgb','Zone editing requires an active per-LED mode')
                zones[0].set_color(RGBColor(*value))
        else:raise Fault(FaultCode.BACKEND_UNSUPPORTED,'openrgb','No implemented operation')
        # Re-fetch avoids the client's optimistic set_mode fallback. Still daemon cache.
        client.update();return describe(client.devices[indices[0]])
    finally:client.disconnect()


def setting_plan(target,field,value):
    command=['logi-sdk','openrgb','set',target,field,json.dumps(value)]
    def read(runner):return Observation(json.loads(runner(['logi-sdk','openrgb','read',target]))[field],'backend_cache')
    return Plan(command,value,read,target=target)


class OpenRGBAdapter:
    name='openrgb'
    def __init__(self,runner=None):
        from backend import run
        self.run=runner or run
    def discover(self):
        records=[]
        for state in json.loads(self.run(['logi-sdk','openrgb','discover'])):
            caps=[];target=state['target'];mode=next((m for m in state['modes'] if m['name']==state['lighting_mode']),None)
            for field in ['lighting_mode','brightness','lighting','zones']+[z['setting'] for z in state['zones']]:
                value=state[field]
                if value is None and field not in ['lighting'] and not field.startswith('lighting_zone_'):continue
                writable=field=='lighting_mode' or field=='brightness' and mode is not None and bool(mode['flags']&16) and mode['minimum'] is not None and mode['maximum'] is not None or field=='lighting' and mode is not None and bool(mode['flags']&(32|64)) and mode['color_mode'] in [1,2]
                if field.startswith('lighting_zone_'):writable=mode is not None and mode['color_mode']==1 and bool(mode['flags']&32)
                cap=Capability(field,self.name,True,True,writable,False,value,'backend_cache',choices=[m['name'] for m in state['modes']] if field=='lighting_mode' else [],minimum=min(mode['minimum'],mode['maximum']) if field=='brightness' and mode and mode['minimum'] is not None and mode['maximum'] is not None else None,maximum=max(mode['minimum'],mode['maximum']) if field=='brightness' and mode and mode['minimum'] is not None and mode['maximum'] is not None else None,limitation='OpenRGB SDK server state; no independent hardware readback. Loopback only; no server is started.')
                if field.startswith('lighting_zone_'):cap.label=next(z['name'] for z in state['zones'] if z['setting']==field)
                if value is None:cap.limitation+=' No uniform current color; the picker selects a desired color only.'
                if writable:cap.plan=lambda value,t=target,f=field:setting_plan(t,f,value)
                caps.append(cap)
            # Only an existing full local sysfs path can establish physical identity.
            location=state['location'];physical=state.get('physical','');vid=state.get('vid','');pid=state.get('pid','')
            if location.startswith('/sys/') and Path(location).exists():physical,vid,pid=usb_identity(location)
            records.append(Device('openrgb:'+target,state['name'],state['kind'],self.name,target,physical,vid,pid,'unknown',True,caps))
        return records
