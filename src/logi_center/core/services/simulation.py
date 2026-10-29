"""Explicit developer-only adapters. Never connect simulations to real CLI writes."""
from logi_center.core.devices.devices import Device, DeviceManager
from logi_center.core.capabilities.model import Capability
from logi_center.core.services.operations import Plan,Observation,perform
from logi_center.core.services.execution import Fault,FaultCode

class SimulationAdapter:
    name='simulation'
    def __init__(self):self.values={};self.disconnected=set()
    def discover(self):
        scenarios=[('simple-mouse','Simple mouse','mouse',[('buttons',3)]),('gaming-mouse','Gaming mouse','mouse',[('buttons',11),('dpi',800),('lighting','44aaff'),('macros',[])]),('rgb-keyboard','RGB keyboard','keyboard',[('lighting','ffffff'),('programmable_keys',[])]),('plain-keyboard','Standard keyboard','keyboard',[('standard_input',True)]),('usb-headset','USB headset','audio',[('volume',50),('microphone_mute',False)]),('wireless-headset','Wireless headset','audio',[('volume',50),('battery_status',78)]),('partial','Partial backend','mouse',[('dpi',800),('battery_status',None)]),('disconnect','Disconnect during write','mouse',[('dpi',800)])]
        scenarios += [('logitech','Logitech mouse fixture','mouse',[('dpi',800),('buttons',11)]),('mchose','MCHOSE K7 family fixture','mouse',[('dpi',1600),('polling_rate',1000),('debounce',4)]),('razer','Razer mouse fixture','mouse',[('dpi_x',800),('brightness',70)]),('corsair','Corsair keyboard fixture','keyboard',[('lighting','55aaff')]),('steelseries','SteelSeries mouse fixture','mouse',[('polling_rate',1000)]),('wireless-charging-mouse','Wireless mouse charging fixture','mouse',[('battery_status',64),('charging',True)]),('unsupported','Unsupported input fixture','input',[('standard_input',True)])]
        devices=[]
        for ident,name,kind,settings in scenarios:
            caps=[]
            for setting,value in settings:
                self.values.setdefault((ident,setting),value)
                writable=setting not in ['battery_status','charging','standard_input','buttons']
                caps.append(Capability(setting,self.name,True,True,writable,True,self.values[ident,setting],'simulation',limitation='Simulated data; not hardware evidence.',evidence=['simulation']))
            connection = 'bluetooth' if ident == 'wireless-headset' else '2.4g' if ident == 'wireless-charging-mouse' else 'usb'
            devices.append(Device('sim:'+ident,name,kind,self.name,ident,connection=connection,connected=ident not in self.disconnected,capabilities=caps,simulated=True))
        return devices
    def apply(self,target,setting,value):
        def runner(args):
            if target=='disconnect':self.disconnected.add(target);raise Fault(FaultCode.DISCONNECTED,self.name,'Simulated unplug')
            if target=='partial':raise Fault(FaultCode.BACKEND_UNSUPPORTED,self.name,'Simulated backend limitation')
            if target in self.disconnected:raise Fault(FaultCode.DISCONNECTED,self.name,'Simulation offline')
            self.values[target,setting]=value;return ''
        return perform(Plan(['simulation',target,setting],value,lambda run:Observation(self.values[target,setting],'simulation')),runner)
