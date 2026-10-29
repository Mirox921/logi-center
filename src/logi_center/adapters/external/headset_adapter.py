"""HeadsetControl discovery with explicit writable capability limits."""
import json
from logi_center.core.discovery.identity import usb_id
from logi_center.core.devices.devices import Device, DeviceManager
from logi_center.core.capabilities.model import Capability
from logi_center.core.discovery.identity import identity, usb_identity

class HeadsetAdapter:
    name='headsetcontrol'
    def __init__(self,runner=None):
        from logi_center.adapters.external.backend import run
        self.run=runner or run
    def discover(self):
        doc=json.loads(self.run(['headsetcontrol','-o','json']));result=[]
        for index,item in enumerate(doc.get('devices',[])):
            vid=usb_id(item.get('id_vendor'));pid=usb_id(item.get('id_product'))
            target=vid+':'+pid;capabilities=[]
            # PRO X USB sound card (the wired headset) is reported by some
            # HeadsetControl versions with CAP_BATTERY_STATUS but no battery.
            # A positive hardware reading always takes precedence over this
            # narrow product exception.
            battery=item.get('battery',{})
            wired_pro_x=(vid,pid)==('046d','0aaa') and battery.get('status')=='BATTERY_UNAVAILABLE'
            if wired_pro_x:
                capabilities.append(Capability('battery_present',self.name,True,False,False,False,False,'model_spec'))
            for cap in item.get('capabilities',[]):
                if not isinstance(cap,str):continue
                name=cap.removeprefix('CAP_').lower()
                if wired_pro_x and name=='battery_status':continue
                battery=item.get('battery',{}) if name=='battery_status' else {}
                level=battery.get('level');readable=type(level) is int and 0<=level<=100 and battery.get('status') in ['BATTERY_AVAILABLE','BATTERY_CHARGING']
                source='device' if readable else 'unavailable'
                capabilities.append(Capability(name,self.name,True,readable,name=='sidetone' and bool(vid and pid),False,level if readable else None,source,minimum=0 if name=='sidetone' else None,maximum=128 if name=='sidetone' else None,limitation='Other reported features are diagnostic-only until a parameter-specific adapter is implemented.',evidence=['software_detected']))
                if name=='battery_status':
                    status=battery.get('status')
                    charging_known=status in ['BATTERY_AVAILABLE','BATTERY_CHARGING']
                    capabilities.append(Capability('charging',self.name,True,charging_known,False,False,status=='BATTERY_CHARGING' if charging_known else None,'device' if charging_known else 'unavailable',limitation='Charging state is reported separately from percentage.'))
            result.append(Device('headset:'+target+':'+str(index),item.get('device','USB headset'),'audio',self.name,target,vid=vid,pid=pid,connection='usb',connected=True if item.get('status','success')=='success' else None,capabilities=capabilities))
        from logi_center.core.services.operations import plan_for
        for device in result:
            for cap in device.capabilities:
                if cap.name=='sidetone' and cap.writable:cap.plan=lambda value,t=device.target:plan_for(['headsetcontrol','-d',t,'-s',str(value)])
        # The CLI selects by VID/PID: ambiguous identical units must not be written.
        for d in result:
            if sum(other.target==d.target for other in result)>1:
                for cap in d.capabilities:cap.writable=False;cap.limitation='Multiple identical units; backend selector is ambiguous.'
        return result
