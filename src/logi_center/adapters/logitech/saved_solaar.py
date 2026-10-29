"""Local Solaar cache observations; never a substitute for live settings."""
from logi_center.core.devices.devices import Device, DeviceManager
from logi_center.core.capabilities.model import Capability
from logi_center.core.discovery.identity import identity, usb_identity

class SavedSolaarAdapter:
    name='solaar-local'
    def __init__(self,path=None):self.path=path
    def discover(self):
        from logi_center.adapters.external.backend import saved_solaar_devices
        result=[]
        for index,item in enumerate(saved_solaar_devices(self.path)):
            name=item.get('_NAME','Logitech device')
            caps=[Capability(key,self.name,None,True,False,False,value,'local_saved_settings',limitation='Saved configuration only; live feature support has not been probed.',evidence=['backend_supported']) for key,value in item.items() if not key.startswith('_')]
            result.append(Device('solaar-saved:'+identity(str(item.get('_serial') or item.get('_unitId') or str(item.get('_modelId',''))+':record:'+str(index))+name),name,'keyboard' if 'keyboard' in name.lower() or 'G515' in name else 'input',self.name,connected=None,capabilities=caps))
        return result
