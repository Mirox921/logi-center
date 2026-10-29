"""Read-only ckb-next daemon inventory. Never commandeer its command FIFO."""
from pathlib import Path
from logi_center.core.devices.devices import Device
from logi_center.core.capabilities.model import Capability
from logi_center.core.discovery.identity import identity
from logi_center.core.services.execution import Fault,FaultCode

class CkbAdapter:
    name='ckb-next'
    def __init__(self,root='/dev/input'):self.root=Path(root)
    def discover(self):
        records=[]
        for node in self.root.glob('ckb[1-9]*'):
            if not node.is_dir():continue
            try:
                name=(node/'model').read_text().strip();features=(node/'features').read_text().split();pid=(node/'productid').read_text().strip()
                token=identity((node/'serial').read_text().strip() or str(node))
            except PermissionError:raise Fault(FaultCode.PERMISSION,self.name,'Daemon device metadata is inaccessible') from None
            except FileNotFoundError:continue
            caps=[Capability('backend_features',self.name,True,True,False,False,features,'backend_cache',limitation='Detection only. Writing the FIFO can conflict with ckb-next GUI/profile activation; use OpenRGB for lighting when it provides this device.')]
            records.append(Device('ckb-next:'+token,name,'input',self.name,token,vid='1b1c',pid=pid,connection='usb',capabilities=caps))
        return records
