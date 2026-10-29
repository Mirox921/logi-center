"""Read-only Linux input and power-supply discovery."""
from pathlib import Path
import struct,re
from logi_center.core.devices.devices import Device, DeviceManager
from logi_center.core.capabilities.model import Capability
from logi_center.core.discovery.identity import identity, usb_identity

def parse_key_mask(text,word_bits=None):
    bits=word_bits or struct.calcsize('L')*8
    return sum(int(word,16)<<(index*bits) for index,word in enumerate(reversed(text.split())))


def hid_parent(node):
    for parent in [node.resolve(),*node.resolve().parents]:
        try:
            if 'HID_ID=' in (parent/'uevent').read_text():return parent
        except OSError:continue
    return None


def reconcile_logitech_inputs(records,aliases=()):
    """Join transport views only with an exact, non-placeholder unit identity.

    A USB receiver is not a peripheral identity. Keep ambiguous identical units
    apart; one wired and one receiver view with the same unit may be combined.
    """
    keyboards=[d for d in records if d.backend=='linux-input' and d.kind=='keyboard'
               and d.vid=='046d' and 'g515' in d.name.casefold() and not d.simulated]
    for device in keyboards:
        serial=device.private_identity.get('solaar_serial')
        units=[group for group in aliases if serial and serial in group]
        if len(units)==1:
            device.private_identity['unit_aliases']=sorted(units[0])
    groups={}
    for device in keyboards:
        serial=device.private_identity.get('solaar_serial')
        if not serial:continue
        tokens=device.private_identity.get('unit_aliases',[serial])
        groups.setdefault(tuple(tokens),[]).append(device)
    for tokens,peers in groups.items():
        if len(peers)>2 or len({d.connection for d in peers})!=len(peers):continue
        primary=next((d for d in peers if d.connection=='usb'),peers[0])
        if len(peers)==2 and {d.connection for d in peers}!={'usb','wireless'}:continue
        parents=sorted({p for d in peers for p in
            [d.private_identity.get('usb_parent',d.physical.split('|',1)[0]),*d.private_identity.get('usb_parents',[])]})
        physical='logitech-unit:'+identity('|'.join(tokens))
        for device in peers:
            device.physical=physical;device.id='linux-input:'+identity(physical+':keyboard')
            device.connection=primary.connection
            device.private_identity.update(usb_parents=parents,
                active_usb_parent=primary.private_identity.get('active_usb_parent') or primary.private_identity.get('usb_parent',primary.physical.split('|',1)[0]))


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
            elif vid=='046d' and pid=='c547':connection='wireless'
            elif bus=='0003' or usb_parent:connection='usb'
            elif bus in ['0011','0018','0019'] or any(marker in str(node.resolve()).casefold() for marker in ['/i2c-','/serio','/serial']):connection='internal'
            elif not vid:connection='internal'
            else:connection='unknown'
            cap=Capability('standard_input',self.name,True,True,False,False,'keyboard' if keyboard else 'mouse','kernel',limitation='Kernel input detection does not imply RGB or remapping support.',evidence=['software_detected','read_observed'])
            device=Device(self.name+':'+identity(ident),name,'keyboard' if keyboard else 'mouse',self.name,physical=physical,vid=vid,pid=pid,connection=connection,capabilities=[cap])
            # Several evdev collections of one HID device are not peripherals.
            hid=hid_parent(node)
            if hid is not None and vid=='046d' and 'g515' in name.casefold():
                device.private_identity['hid_parent']=str(hid)
                if keyboard:
                    device.physical=physical.split('|',1)[0]+'|hid:'+identity(hid)+':keyboard'
                    device.id=self.name+':'+identity(device.physical)
            device.private_identity['usb_parent']=physical.split('|',1)[0]
            # HID/input uniq identifies the paired peripheral, not receiver PID.
            try:unique=(node/'uniq').read_text().strip()
            except OSError:unique=''
            if not unique and vid=='046d' and connection=='usb' and usb_parent:
                try:unique=(Path(physical.split('|',1)[0])/'serial').read_text().strip()
                except OSError:pass
            if vid=='046d' and re.fullmatch('[0-9a-fA-F]{8,32}',unique) and len(set(unique))>1:
                device.private_identity['solaar_serial']=unique.casefold()
            records.append(device)
        # Wired keyboards expose a pointer collection for firmware shortcuts.
        # Require the exact USB parent and keyboard name, never model alone.
        for pointer in [d for d in records if d.vid=='046d' and d.kind=='mouse' and 'g515' in d.name.casefold()]:
            peers=[d for d in records if d.kind=='keyboard' and d.vid==pointer.vid
                   and d.private_identity.get('usb_parent')==pointer.private_identity.get('usb_parent')
                   and pointer.name.casefold()==d.name.casefold()+' mouse']
            if len({d.physical for d in peers})==1:pointer.kind='interface'
        reconcile_logitech_inputs(records)
        records.sort(key=lambda d:bool(d.private_identity.get('active_usb_parent') and
            d.private_identity.get('usb_parent')!=d.private_identity['active_usb_parent']))
        return DeviceManager.merge(records)


class KernelBatteryAdapter:
    name='kernel-battery'
    association_priority=20
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
                status=fields.get('POWER_SUPPLY_STATUS','')
                charging=True if status=='Charging' else False if status in ('Discharging','Not charging','Full') else None
                caps=[Capability('battery_status',self.name,True,True,value=value,source='kernel'),Capability('charging',self.name,True,charging is not None,value=charging,source='kernel' if charging is not None else 'unavailable')]
                records.append(Device(self.name+':'+identity(physical),fields.get('POWER_SUPPLY_MODEL_NAME','Peripheral'),'battery',self.name,physical=physical,vid=vid,pid=pid,connected=None,capabilities=caps,
                    private_identity={'usb_parent':physical}))
            except OSError:continue
        return records
    def associate(self,records):
        for battery in [d for d in records if d.backend==self.name]:
            peers=[d for d in records if 'linux-input' in d.backends and d.kind in ['mouse','keyboard']
                   and (d.physical.split('|',1)[0]==battery.physical or battery.physical in d.private_identity.get('usb_parents',[]))]
            candidates={(d.physical,d.kind) for d in peers}
            if len(candidates)==1:
                # A plugged cable's supply wins over a receiver's stale status.
                active={d.private_identity.get('active_usb_parent') for d in peers}
                if any(active) and battery.physical not in active:continue
                battery.physical,battery.kind=next(iter(candidates))
