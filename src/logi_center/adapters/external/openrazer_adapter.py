"""OpenRazer public Python API in a bounded worker. No service auto-start."""
import json
from logi_center.core.devices.devices import Device
from logi_center.core.capabilities.model import Capability
from logi_center.core.discovery.identity import identity, serial_usb_identity
from logi_center.core.services.execution import Fault,FaultCode
from logi_center.core.services.operations import Plan,Observation


def describe(device):
    settings={}
    if device.has('dpi'):
        dpi=list(device.dpi)
        settings['dpi_x']={'value':dpi[0],'minimum':1,'maximum':device.max_dpi}
        if not device.has('available_dpi'):settings['dpi_y']={'value':dpi[1],'minimum':1,'maximum':device.max_dpi}
        elif device.has('available_dpi'):settings['dpi_x']['choices']=list(device.available_dpi)
    if device.has('poll_rate'):
        settings['polling_rate']={'value':device.poll_rate,'choices':list(device.supported_poll_rates) if device.has('supported_poll_rates') else []}
    if device.has('brightness'):settings['brightness']={'value':device.brightness,'minimum':0,'maximum':100}
    if device.has('battery'):settings['battery_status']={'value':device.battery_level,'readonly':True}
    physical,vid,pid=serial_usb_identity(device.serial)
    return {'physical':physical,'vid':vid,'pid':pid,'target':identity(device.serial),'name':device.name,'kind':device.type.lower(),'settings':settings,'capabilities':[k for k,v in device.capabilities.items() if v]}


def hardware(action,target=None,field=None,value=None,factory=None):
    if factory is None:
        from openrazer.client import DeviceManager
        import dbus
        if not dbus.SessionBus().name_has_owner('org.razer'):raise Fault(FaultCode.CONNECTION,'openrazer','OpenRazer daemon is not running; it was not started automatically')
        factory=DeviceManager
    manager=factory()
    if action=='discover':return [describe(d) for d in manager.devices]
    devices=[d for d in manager.devices if identity(d.serial)==target]
    if len(devices)!=1:raise Fault(FaultCode.DISCONNECTED if not devices else FaultCode.CONFIG,'openrazer','Device absent or ambiguous')
    device=devices[0];state=describe(device)
    if action=='read':return state
    if action!='set' or field not in state['settings']:raise Fault(FaultCode.BACKEND_UNSUPPORTED,'openrazer','No implemented operation')
    setting=state['settings'][field]
    if setting.get('readonly'):raise Fault(FaultCode.BACKEND_UNSUPPORTED,'openrazer','Read-only capability')
    if type(value) is not int and not (field=='brightness' and type(value) is float):raise ValueError('Expected numeric brightness or integer device setting')
    if setting.get('choices') and value not in setting['choices']:raise ValueError('Value outside reported choices')
    if 'minimum' in setting and not setting['minimum']<=value<=setting['maximum']:raise ValueError('Value outside reported range')
    if field in ['dpi_x','dpi_y']:
        dpi=list(device.dpi);dpi[0 if field=='dpi_x' else 1]=value;device.dpi=tuple(dpi)
    elif field=='polling_rate':
        if not setting.get('choices'):raise Fault(FaultCode.BACKEND_UNSUPPORTED,'openrazer','Daemon did not report allowed rates')
        device.poll_rate=value
    elif field=='brightness':device.brightness=value
    return describe(device)


def setting_plan(target,field,value):
    def read(runner):return Observation(json.loads(runner(['logi-sdk','openrazer','read',target]))['settings'][field]['value'],'backend_cache')
    return Plan(['logi-sdk','openrazer','set',target,field,json.dumps(value)],value,read,target=target)


class OpenRazerAdapter:
    name='openrazer'
    def __init__(self,runner=None):
        from logi_center.adapters.external.backend import run
        self.run=runner or run
    def discover(self):
        result=[]
        for state in json.loads(self.run(['logi-sdk','openrazer','discover'])):
            caps=[]
            for field,setting in state['settings'].items():
                writable=not setting.get('readonly',False) and (field!='polling_rate' or bool(setting.get('choices')))
                cap=Capability(field,self.name,True,True,writable,False,setting['value'],'backend_cache',choices=setting.get('choices',[]),minimum=setting.get('minimum'),maximum=setting.get('maximum'),limitation='OpenRazer daemon/driver state; independent hardware readback unavailable. RGB effects use OpenRGB when available.')
                if writable:cap.plan=lambda value,t=state['target'],f=field:setting_plan(t,f,value)
                caps.append(cap)
            caps.append(Capability('backend_features',self.name,True,True,False,False,state['capabilities'],'backend_cache',limitation='Reported API features; only implemented editors are writable.'))
            result.append(Device('openrazer:'+state['target'],state['name'],state['kind'],self.name,state['target'],state.get('physical',''),state.get('vid',''),state.get('pid',''),capabilities=caps))
        return result
