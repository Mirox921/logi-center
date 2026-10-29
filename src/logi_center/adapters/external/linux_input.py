"""Read-only Linux input and power-supply discovery."""
from pathlib import Path
import struct,re
from logi_center.core.devices.devices import Device, DeviceManager
from logi_center.core.capabilities.model import Capability
from logi_center.core.discovery.identity import identity, usb_identity

def parse_key_mask(text,word_bits=None):
    bits=word_bits or struct.calcsize('L')*8
    return sum(int(word,16)<<(index*bits) for index,word in enumerate(reversed(text.split())))


class InputAdapter:
    name='linux-input'
    def __init__(self,root='/sys/class/input'):self.root=Path(root)
    def discover(self):
        records=[]
        for event in sorted(self.root.glob('event*')):
            node=event/'device'
            try:
                name=(node/'name').read_text().strip();bits=parse_key_mask((node/'capabilities/key').read_text())
            except (OSError,ValueError):continue
            keyboard=all(bits&(1<<key) for key in [14,30,57]);mouse=bool(bits&(1<<272));touchpad=bool(bits&(1<<325))
            if touchpad:continue
            if not keyboard and not mouse:continue
            physical,vid,pid=usb_identity(node)
            usb_parent=bool(physical)
            # Receiver slots/interface paths stay intact; stripping /inputN:slot
            # would incorrectly merge two devices behind one receiver.
            try:input_phys=(node/'phys').read_text().strip()
            except OSError:input_phys=''
            if not physical:
                for parent in [node.resolve(),*node.resolve().parents]:
                    try:uevent=(parent/'uevent').read_text()
                    except OSError:continue
                    if 'HID_ID=' in uevent:
                        physical=str(parent);break
                try:vid=(node/'id/vendor').read_text().strip();pid=(node/'id/product').read_text().strip()
                except OSError:pass
            if physical and input_phys:physical+='|'+input_phys
            ident=physical or str(node.resolve())
            try:bus=(node/'id/bustype').read_text().strip()
            except OSError:bus=''
            if bus=='0005' or '/bluetooth' in str(node.resolve()):connection='bluetooth'
            elif bus=='0003' or usb_parent:connection='usb'
            elif bus in ['0011','0018','0019'] or any(marker in str(node.resolve()).casefold() for marker in ['/i2c-','/serio','/serial']):connection='internal'
            elif not vid:connection='internal'
            else:connection='unknown'
            cap=Capability('standard_input',self.name,True,True,False,False,'keyboard' if keyboard else 'mouse','kernel',limitation='Kernel input detection does not imply RGB or remapping support.',evidence=['software_detected','read_observed'])
            device=Device(self.name+':'+identity(ident),name,'keyboard' if keyboard else 'mouse',self.name,physical=physical,vid=vid,pid=pid,connection=connection,capabilities=[cap])
            # HID/input uniq identifies the paired peripheral, not receiver PID.
            try:unique=(node/'uniq').read_text().strip()
            except OSError:unique=''
            if vid=='046d' and re.fullmatch('[0-9a-fA-F]{8,32}',unique) and len(set(unique))>1:
                device.private_identity['solaar_serial']=unique.casefold()
            records.append(device)
        return DeviceManager.merge(records)


class KernelBatteryAdapter:
    name='kernel-battery'
    def __init__(self,root='/sys/class/power_supply'):self.root=Path(root)
    def discover(self):
        # Enrich only an exact kernel parent, never join batteries by model name.
        records=[]
        for directory in self.root.glob('*'):
            try:
                fields=dict(line.split('=',1) for line in (directory/'uevent').read_text().splitlines() if '=' in line)
                if fields.get('POWER_SUPPLY_SCOPE')!='Device':continue
                parent=(directory/'device').resolve()
                if not parent.exists():continue
                physical,vid,pid=usb_identity(parent)
                physical=physical or str(parent)
                value=fields.get('POWER_SUPPLY_CAPACITY','')
                value=int(value) if value.isdigit() and 0<=int(value)<=100 else fields.get('POWER_SUPPLY_CAPACITY_LEVEL','Unknown')
                caps=[Capability('battery_status',self.name,True,True,value=value,source='kernel'),Capability('charging',self.name,True,True,value=fields.get('POWER_SUPPLY_STATUS')=='Charging',source='kernel')]
                records.append(Device(self.name+':'+identity(physical),fields.get('POWER_SUPPLY_MODEL_NAME','Peripheral'),'battery',self.name,physical=physical,vid=vid,pid=pid,connected=None,capabilities=caps))
            except OSError:continue
        return records
    def associate(self,records):
        for battery in [d for d in records if d.backend==self.name]:
            peers=[d for d in records if 'linux-input' in d.backends and d.kind in ['mouse','keyboard'] and d.physical.split('|',1)[0]==battery.physical]
            candidates={(d.physical,d.kind) for d in peers}
            if len(candidates)==1:battery.physical,battery.kind=next(iter(candidates))
