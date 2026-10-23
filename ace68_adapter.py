"""Ace68-II identification, isolated from the MCHOSE mouse protocol.

Only exact 41e4:2116 interface 01 and its 64-byte unnumbered I/O descriptor
are accepted. sysfs bcdDevice is a USB release identifier, not firmware proof.
"""
from pathlib import Path
import re,hashlib
from devices import Device,Capability,usb_identity,identity

VID='41e4';PID='2116'
LAYOUT=[['Esc',*list('1234567890'),'-','=','Backspace','`'],['Tab',*list('QWERTYUIOP'),'[',']','\\','Del'],['Caps',*list('ASDFGHJKL'),';',"'",'Enter','PgUp'],['LShift',*list('ZXCVBNM'),',','.','/','RShift','↑','PgDn'],['LCtrl','Super','LAlt','Space','RAlt','Fn','RCtrl','←','↓','→']]
FEATURES=['actuation','rapid_trigger','release_point','dead_zone','socd','dks','mod_tap','toggle_key','key_remap','macros','layers','lighting','profiles','polling_rate']

def candidates(root='/sys/class/hidraw'):
    result=[]
    for node in sorted(Path(root).glob('hidraw*')):
        try:
            text=(node/'device/uevent').read_text();descriptor=(node/'device/report_descriptor').read_bytes()
            match=re.search(r'HID_ID=[0-9A-Fa-f]+:([0-9A-Fa-f]+):([0-9A-Fa-f]+)',text)
            if not match or (int(match[1],16),int(match[2],16))!=(int(VID,16),int(PID,16)):continue
            parent=(node/'device').resolve();interface=next(p for p in [parent,*parent.parents] if (p/'bInterfaceNumber').exists())
            if (interface/'bInterfaceNumber').read_text().strip()!='01':continue
            # Exact descriptor shape of this revision; no mouse feature reports.
            if descriptor!=bytes.fromhex('05010900a101150026ff001900290895407508810219012908954075089102c0'):continue
            physical,vid,pid=usb_identity(parent)
            if not physical:continue
            release=(Path(physical)/'bcdDevice').read_text().strip()
            name=(Path(physical)/'product').read_text().strip()
            result.append({'node':'/dev/'+node.name,'physical':physical,'generation':str(parent),'name':name,'release':release,'descriptor_sha256':hashlib.sha256(descriptor).hexdigest()})
        except (OSError,StopIteration):continue
    return result

def selector(item):return identity(item['physical']+'|'+item['generation'])


def hardware(action,target,field=None,value=None,transport=None):
    import time
    from ace68_protocol import Transport,state,KEY_FIELDS,validate_key_value,changed_key,RATES,MODES
    from execution import Fault,FaultCode
    from drafts import atomic_json
    item=next((c for c in candidates() if selector(c)==target),None)
    if not item:raise Fault(FaultCode.DISCONNECTED,'mchose-ace68','Exact Ace68-II configuration interface is absent')
    with (transport or Transport)(item['node']) as wire:
        current=state(wire)
        if action=='read':return current
        if isinstance(field,str) and field.startswith('profile/'):
            parts=field.split('/')
            if len(parts)!=3 or parts[1]!=str(current['profiles']):raise Fault(FaultCode.CONFIG,'mchose-ace68','Profile changed since the command was prepared')
            field=parts[2]
        if action!='set' or current['firmware_version']!='121':raise Fault(FaultCode.BACKEND_UNSUPPORTED,'mchose-ace68','Writes are validated only for Ace68-II firmware 121')
        commands=[];profile=current['profiles']
        if field in KEY_FIELDS:
            if not isinstance(value,dict) or not value or len(value)>68:raise ValueError('Expected selected-key distances/modes')
            for key,desired in value.items():
                ticks=validate_key_value(current,field,key,desired);offset=int(key)*8
                payload=changed_key(current['raw_keys'][offset:offset+8],field,ticks)
                commands.append((161,profile*1024+offset,payload))
        elif field=='profiles':
            if type(value) is not int or value not in current['profile_choices']:raise ValueError('Profile is not enabled')
            commands=[(14,0,bytes([current['raw_base'][2:6].index(value)]))]
        elif field=='polling_rate':
            if type(value) is not int or value not in RATES.values():raise ValueError('Unsupported polling rate')
            code=next(k for k,v in RATES.items() if v==value);commands=[(6,profile*64+4,bytes([(current['raw_config'][4]&240)|code]))]
        elif field in ['brightness','lighting_speed']:
            maximum=100 if field=='brightness' else 4
            if type(value) is not int or not 0<=value<=maximum:raise ValueError('Lighting value outside verified range')
            commands=[(6,profile*64+(9 if field=='brightness' else 10),bytes([value if field=='brightness' else 4-value]))]
        elif field=='lighting_mode':
            if value not in MODES.values():raise ValueError('Unsupported light mode')
            commands=[(6,profile*64+8,bytes([next(k for k,v in MODES.items() if v==value)]))]
        elif field=='lighting_palette':
            if value not in ['Single color','Random colors']:raise ValueError('Unsupported palette')
            commands=[(6,profile*64+12,bytes([['Single color','Random colors'].index(value)]))]
        elif field=='lighting':
            if not isinstance(value,list) or len(value)!=3 or any(type(v) is not int or not 0<=v<=255 for v in value):raise ValueError('Expected RGB channels')
            # A color edit never silently changes random-color mode.
            commands=[(6,profile*64+14,bytes(value))]
        else:raise Fault(FaultCode.BACKEND_UNSUPPORTED,'mchose-ace68','No safe implementation for this feature')
        root=Path.home()/'.local/state/logi-center/backups'/('ace68-'+identity(item['physical']))
        atomic_json(root/(str(time.time_ns())+'.json'),{'format':'ace68-ii-observed-config','version':1,'source':'device','vid':VID,'pid':PID,'settings':current})
        for command,offset,payload in commands:
            wire.request(command,offset,len(payload),list(payload))
        actual=state(wire)
        if field!='profiles':
            expected={k:list(current[k]) for k in ['raw_base','raw_config','raw_keys']}
            for command,offset,payload in commands:
                name,local=('raw_keys',offset-profile*1024) if command==161 else ('raw_config',offset-profile*64)
                expected[name][local:local+len(payload)]=list(payload)
            if any(actual[k]!=v for k,v in expected.items()):raise Fault(FaultCode.CONNECTION,'mchose-ace68','Partial apply: unrelated configuration changed; private pre-write snapshot retained')
        if field!='profiles' and actual['profiles']!=profile:raise Fault(FaultCode.CONNECTION,'mchose-ace68','Profile changed during apply; private snapshot retained')
        return actual


def setting_plan(target,field,value,profile=None):
    import json
    from operations import Plan,Observation
    def read(runner):
        state=json.loads(runner(['logi-sdk','mchose-ace68','read',target]))
        if profile is not None and field!='profiles' and state['profiles']!=profile:raise ValueError('Profile changed during readback')
        observed=state[field]
        if isinstance(value,dict):observed={key:observed[key] for key in value}
        return Observation(observed,'device')
    return Plan(['logi-sdk','mchose-ace68','set',target,('profile/'+str(profile)+'/'+field) if profile is not None else field,json.dumps(value)],value,read,target=target)


class Ace68Adapter:
    name='mchose-ace68'
    def __init__(self,root='/sys/class/hidraw',runner=None):
        from backend import run
        self.root=root;self.run=runner or run
    def associate(self,records):
        # This exact wired revision has three interfaces of one keyboard, not a
        # multi-unit wireless receiver. Collapse only these known kernel siblings.
        for device in [d for d in records if d.backend==self.name]:
            for peer in records:
                if peer.backend=='linux-input' and peer.kind=='mouse' and peer.vid==VID and peer.pid==PID and peer.physical.split('|',1)[0]==device.physical:peer.kind='interface'
                if peer.backend=='linux-input' and peer.kind=='keyboard' and peer.vid==VID and peer.pid==PID and peer.physical.split('|',1)[0]==device.physical:
                    peer.physical=device.physical;peer.id=device.id
    def discover(self):
        import json
        from diagnostics import fault_for
        from ace68_protocol import KEY_FIELDS,RATES,MODES
        records=[]
        for item in candidates(self.root):
            target=selector(item);faults=[]
            caps=[Capability('usb_release',self.name,True,True,False,False,item['release'],'kernel',limitation='USB bcdDevice only; PCB/switch revision is not established.'),Capability('keyboard_layout',self.name,True,True,False,False,'Ace68-II ANSI 68','model_definition')]
            try:
                observed=json.loads(self.run(['logi-sdk',self.name,'read',target]))
                for field in ['firmware_version','profiles','polling_rate','brightness','lighting_mode','lighting_speed','lighting_palette','lighting',*KEY_FIELDS,'key_details']:
                    writable=field not in ['firmware_version','key_details'] and observed['firmware_version']=='121'
                    choices=observed['profile_choices'] if field=='profiles' else list(RATES.values()) if field=='polling_rate' else list(MODES.values()) if field=='lighting_mode' else ['Single color','Random colors'] if field=='lighting_palette' else []
                    low,high=(0,100) if field=='brightness' else (0,4) if field=='lighting_speed' else (None,None)
                    cap=Capability(field,self.name,True,True,writable,writable,observed[field],'device',choices=choices,minimum=low,maximum=high,limitation='Ace68-II firmware 121. Hardware profile readback; not optical RGB verification. Stored RGB is used in Single color palette; random colors stay independent.')
                    if writable:cap.plan=lambda value,t=target,f=field,p=observed['profiles']:setting_plan(t,f,value,p)
                    caps.append(cap)
            except Exception as error:faults.append(fault_for(error,self.name))
            for field in ['socd','dks','mod_tap','toggle_key','key_remap','macros','layers']:
                caps.append(Capability(field,self.name,None,False,False,False,None,'unavailable',limitation='Stored advanced-key formats are not yet validated for editing; no software emulation is installed.',evidence=['software_detected']))
            records.append(Device('ace68:'+identity(item['physical']),item['name'],'keyboard',self.name,target,item['physical'],VID,PID,'usb',True,caps,faults=faults))
        return records
