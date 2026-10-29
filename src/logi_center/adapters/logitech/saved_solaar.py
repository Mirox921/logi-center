"""Local Solaar cache observations; never a substitute for live settings."""
from logi_center.core.devices.devices import Device, DeviceManager
from logi_center.core.capabilities.model import Capability
from logi_center.core.discovery.identity import identity, usb_identity
import re

class SavedSolaarAdapter:
    name='solaar-local'
    association_priority=10
    def __init__(self,path=None):self.path=path
    def associate(self,records):
        from logi_center.adapters.external.linux_input import reconcile_logitech_inputs
        groups=[set(d.private_identity.get('unit_aliases',[])) for d in records if d.backend==self.name]
        # Overlapping saved records are ambiguous, even if names coincide.
        groups=[g for g in groups if g and sum(bool(g & other) for other in groups)==1]
        reconcile_logitech_inputs(records,groups)
        records.sort(key=lambda d:(d.backend!='linux-input',bool(d.private_identity.get('active_usb_parent') and
            d.private_identity.get('usb_parent')!=d.private_identity['active_usb_parent'])))
        for cached in [d for d in records if d.backend==self.name]:
            serial=cached.private_identity.get('solaar_serial')
            if not serial:continue
            copies=[d for d in records if d.backend==self.name and d.private_identity.get('solaar_serial')==serial]
            aliases=set(cached.private_identity.get('unit_aliases',[serial]))
            peers=[d for d in records if d.backend=='linux-input' and d.vid=='046d' and d.kind==cached.kind
                   and d.connected is True and not d.simulated and d.physical
                   and d.private_identity.get('solaar_serial') in aliases]
            if len(copies)==1 and len({d.physical for d in peers})==1:
                cached.physical=peers[0].physical
                cached.target=serial;cached.targets={self.name:[serial]}
    def discover(self):
        from logi_center.adapters.external.backend import saved_solaar_devices
        result=[]
        for index,item in enumerate(saved_solaar_devices(self.path)):
            name=item.get('_NAME','Logitech device')
            caps=[Capability(key,self.name,None,True,False,False,value,'local_saved_settings',limitation='Saved configuration only; live feature support has not been probed.',evidence=['backend_supported']) for key,value in item.items()
                  if isinstance(key,str) and re.fullmatch('[a-z][a-z0-9_-]{0,63}',key) and not re.fullmatch('[0-9a-f]{8,}',key)]
            device=Device('solaar-saved:'+identity(str(item.get('_serial') or item.get('_unitId') or str(item.get('_modelId',''))+':record:'+str(index))+name),name,'keyboard' if 'keyboard' in name.lower() or 'G515' in name else 'input',self.name,connected=None,capabilities=caps)
            serial=str(item.get('_serial',''))
            if re.fullmatch('[0-9a-fA-F]{8,32}',serial) and len(set(serial))>1:
                device.private_identity['solaar_serial']=serial.casefold()
            aliases={str(item.get(key,'')).casefold() for key in ('_serial','_unitId')}
            device.private_identity['unit_aliases']=sorted(s for s in aliases
                if re.fullmatch('[0-9a-f]{8,32}',s) and len(set(s))>1)
            result.append(device)
        return result
