"""Ace68-II identification, isolated from the MCHOSE mouse protocol.

Only exact 41e4:2116 interface 01 and its 64-byte unnumbered I/O descriptor
are accepted. sysfs bcdDevice is a USB release identifier, not firmware proof.
"""
from pathlib import Path
import re,hashlib
from devices import Device,Capability,usb_identity,identity

VID='41e4';PID='2116'
LAYOUT=[['Esc',*list('1234567890'),'-','=','Backspace','Insert'],['Tab',*list('QWERTYUIOP'),'[',']','\\','Del'],['Caps',*list('ASDFGHJKL'),';',"'",'Enter','PgUp'],['LShift',*list('ZXCVBNM'),',','.','/','RShift','↑','PgDn'],['LCtrl','Super','LAlt','Space','RAlt','Fn','RCtrl','←','↓','→']]
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
        colors=action=='colors' or bool(field and field.rsplit('/',1)[-1]=='key_lighting')
        if colors:
            from ace68_bindings import read_colors
            current.update(read_colors(wire,current['profiles']))
            if list(wire.read(4,0,56))!=current['raw_base']:raise Fault(FaultCode.CONFIG,'mchose-ace68','Profile changed during color read')
        advanced=action=='advanced' or bool(field and field.rsplit('/',1)[-1]=='advanced_keys')
        if action=='bindings' or advanced or field and field.rsplit('/',1)[-1]=='key_remap':
            from ace68_bindings import read as read_bindings
            current.update(read_bindings(wire,current['profiles']))
            if advanced:
                from ace68_advanced import read as read_advanced
                current.update(read_advanced(wire,current['profiles'],current))
            after=wire.read(4,0,56)
            if list(after)!=current['raw_base']:raise Fault(FaultCode.CONFIG,'mchose-ace68','Profile changed during layer read')
        if action in ('bindings','advanced','colors'):return current
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
        elif field=='key_remap':
            from ace68_bindings import prepare
            if not isinstance(value,dict) or set(value)!={'changes','expected_bindings'}:raise ValueError('Invalid Ace68 binding context')
            if value['expected_bindings']!=current['raw_bindings']:
                raise Fault(FaultCode.CONFIG,'mchose-ace68','Bindings changed since the command was prepared')
            commands=prepare(profile,current,value['changes'])
        elif field=='key_lighting':
            from ace68_bindings import prepare_colors
            if not isinstance(value,dict) or set(value)!={'changes','expected_colors'}:raise ValueError('Invalid color context')
            if value['expected_colors']!=current['raw_colors']:raise Fault(FaultCode.CONFIG,'mchose-ace68','Key colors changed since preparation')
            if current['lighting_mode']!='Custom':raise ValueError('Select and apply native Custom mode first')
            commands=prepare_colors(profile,current,value['changes'])
        elif field=='advanced_keys':
            from ace68_advanced import prepare
            if not isinstance(value,dict) or set(value)!={'changes','expected_context'}:raise ValueError('Invalid advanced context')
            context={key:current[key] for key in ('raw_config','raw_keys','raw_bindings','raw_advanced')}
            if value['expected_context']!=context:raise Fault(FaultCode.CONFIG,'mchose-ace68','Advanced configuration changed since preparation')
            commands,expected=prepare(current,value['changes'])
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
        elif field=='lighting_direction':
            if type(value) is not int or value not in (0,1):raise ValueError('Invalid native lighting direction')
            commands=[(6,profile*64+11,bytes([value]))]
        elif field in ('win_lock','stability_mode','key_debounce','adaptive_calibration'):
            if type(value) is not bool:raise ValueError('Expected a keyboard switch')
            offset,mask=(6,1) if field=='win_lock' else (7,2) if field=='stability_mode' else (7,4) if field=='adaptive_calibration' else (7,224)
            if field=='key_debounce' and current['raw_config'][7]>>5 not in (0,7):
                raise ValueError('Unknown debounce level; refusing to replace it')
            if field=='win_lock' and current['keyboard_mode']=='Mac':raise ValueError('Win Lock is unavailable in Mac mode')
            setting=(current['raw_config'][offset]&~mask)|(mask if value else 0)
            commands=[(6,profile*64+offset,bytes([setting]))]
        elif field=='keyboard_mode':
            if value not in ('Windows','Mac'):raise ValueError('Unknown keyboard mode')
            mode=profile*4+(2 if value=='Mac' else 0)
            commands=[(6,profile*64+1,bytes([(current['raw_config'][1]&240)|mode]))]
            if value=='Mac' and current['win_lock']:commands.append((6,profile*64+6,bytes([current['raw_config'][6]&254])))
        elif field=='lighting':
            if not isinstance(value,list) or len(value)!=3 or any(type(v) is not int or not 0<=v<=255 for v in value):raise ValueError('Expected RGB channels')
            # A color edit never silently changes random-color mode.
            commands=[(6,profile*64+14,bytes(value))]
        else:raise Fault(FaultCode.BACKEND_UNSUPPORTED,'mchose-ace68','No safe implementation for this feature')
        root=Path.home()/'.local/state/logi-center/backups'/('ace68-'+identity(item['physical']))
        atomic_json(root/(str(time.time_ns())+'.json'),{'format':'ace68-ii-observed-config','version':1,'source':'device','vid':VID,'pid':PID,'settings':current})
        for index,(command,offset,payload) in enumerate(commands):
            if index:
                base=wire.read(4,0,56)
                if len(base)!=56 or not 1<=base[1]<=4 or not 0<=base[0]<base[1] or base[2+base[0]]!=profile:
                    raise Fault(FaultCode.CONFIG,'mchose-ace68','Profile changed during selected-key apply; private snapshot retained')
            wire.request(command,offset,len(payload),list(payload))
        actual=state(wire)
        if colors:actual.update(read_colors(wire,profile))
        if field in ('key_remap','advanced_keys'):actual.update(read_bindings(wire,profile))
        if field=='advanced_keys':actual.update(read_advanced(wire,profile,actual))
        if field!='profiles':
            expected={k:list(current[k]) for k in ['raw_base','raw_config','raw_keys']}
            if colors:expected['raw_colors']=current['raw_colors'][:]
            if field in ('key_remap','advanced_keys'):expected['raw_bindings']=[bank[:] for bank in current['raw_bindings']]
            if field=='advanced_keys':expected['raw_advanced']={name:bank[:] for name,bank in current['raw_advanced'].items()}
            for command,offset,payload in commands:
                if command==11:
                    local=offset-profile*512;expected['raw_colors'][local:local+len(payload)]=list(payload)
                    continue
                if command==9:
                    layer=(offset//512)%4;local=offset%512
                    expected['raw_bindings'][layer][local:local+len(payload)]=list(payload)
                    continue
                if command in (163,165,167):
                    from ace68_advanced import BANKS
                    name=next(name for name,spec in BANKS.items() if spec[1]==command)
                    local=offset-profile*BANKS[name][2]
                    expected['raw_advanced'][name][local:local+len(payload)]=list(payload)
                    continue
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


def binding_capability(target,observed):
    import json
    from operations import Plan,Observation
    from copy import deepcopy
    profile=observed['profiles'];raw=deepcopy(observed['raw_bindings'])
    cap=Capability('key_remap','mchose-ace68',True,True,observed['firmware_version']=='121',True,
                   deepcopy(observed['key_remap']),'device')
    def plan(changes):
        from ace68_bindings import prepare
        prepare(profile,observed,changes)
        def read(runner):
            current=json.loads(runner(['logi-sdk','mchose-ace68','bindings',target]))
            if current['profiles']!=profile:raise ValueError('Profile changed during binding readback')
            return Observation({key:current['key_remap'][key] for key in changes},'device')
        payload={'changes':changes,'expected_bindings':raw}
        return Plan(['logi-sdk','mchose-ace68','set',target,'profile/'+str(profile)+'/key_remap',json.dumps(payload)],changes,read,target=target)
    if cap.writable:cap.plan=plan
    return cap


def color_capability(target,observed):
    import json
    from copy import deepcopy
    from operations import Plan,Observation
    profile=observed['profiles'];raw=observed['raw_colors'][:]
    cap=Capability('key_lighting','mchose-ace68',True,True,observed['firmware_version']=='121',True,
                   deepcopy(observed['key_lighting']),'device')
    def plan(changes):
        from ace68_bindings import prepare_colors
        prepare_colors(profile,observed,changes)
        def read(runner):
            current=json.loads(runner(['logi-sdk','mchose-ace68','colors',target]))
            if current['profiles']!=profile:raise ValueError('Profile changed during color readback')
            return Observation({key:current['key_lighting'][key] for key in changes},'device')
        return Plan(['logi-sdk','mchose-ace68','set',target,'profile/'+str(profile)+'/key_lighting',
                     json.dumps({'changes':changes,'expected_colors':raw})],changes,read,target=target)
    if cap.writable:cap.plan=plan
    return cap


def advanced_capability(target,observed):
    import json
    from copy import deepcopy
    from operations import Plan,Observation
    profile=observed['profiles']
    context={key:deepcopy(observed[key]) for key in ('raw_config','raw_keys','raw_bindings','raw_advanced')}
    cap=Capability('advanced_keys','mchose-ace68',True,True,observed['firmware_version']=='121',True,
                   deepcopy(observed['advanced_keys']),'device',limitation='Native DKS/MT/TGL/RS/SOCD; one binding per Apply. Physical writes not yet validated.')
    def plan(changes):
        from ace68_advanced import prepare
        unused,expected=prepare(observed,changes)
        def read(runner):
            current=json.loads(runner(['logi-sdk','mchose-ace68','advanced',target]))
            if current['profiles']!=profile:raise ValueError('Profile changed during advanced readback')
            return Observation({key:current['advanced_keys'].get(key) for key in changes},'device')
        payload={'changes':changes,'expected_context':context}
        return Plan(['logi-sdk','mchose-ace68','set',target,'profile/'+str(profile)+'/advanced_keys',json.dumps(payload)],expected,read,target=target)
    if cap.writable:cap.plan=plan
    return cap


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
                for field in ['firmware_version','profiles','polling_rate','brightness','lighting_mode','lighting_speed','lighting_palette','lighting_direction','lighting','win_lock','stability_mode','key_debounce','adaptive_calibration','keyboard_mode',*KEY_FIELDS,'key_details']:
                    if field not in observed:continue
                    writable=field not in ['firmware_version','key_details'] and observed['firmware_version']=='121'
                    if field=='key_debounce' and type(observed[field]) is not bool:writable=False
                    if field=='win_lock' and observed.get('keyboard_mode')=='Mac':writable=False
                    choices=observed['profile_choices'] if field=='profiles' else list(RATES.values()) if field=='polling_rate' else list(MODES.values()) if field=='lighting_mode' else ['Single color','Random colors'] if field=='lighting_palette' else [0,1] if field=='lighting_direction' else ['Windows','Mac'] if field=='keyboard_mode' else []
                    low,high=(0,100) if field=='brightness' else (0,4) if field=='lighting_speed' else (None,None)
                    cap=Capability(field,self.name,True,True,writable,writable,observed[field],'device',choices=choices,minimum=low,maximum=high,limitation='Ace68-II firmware 121. Hardware profile readback; not optical RGB verification. Stored RGB is used in Single color palette; random colors stay independent.')
                    if writable:cap.plan=lambda value,t=target,f=field,p=observed['profiles']:setting_plan(t,f,value,p)
                    caps.append(cap)
            except Exception as error:faults.append(fault_for(error,self.name))
            for field in ['socd','dks','mod_tap','toggle_key','key_remap','macros','layers']:
                native=field!='macros' and any(c.name=='firmware_version' and c.value=='121' for c in caps)
                note='Native bank is read on demand in the QML editor; new writes are source-validated, not physically tested.' if native else 'Macro bank capacity/format and safe allocation are not validated; existing records are preserved.' if field=='macros' else 'This firmware revision is not validated for advanced editing.'
                caps.append(Capability(field,self.name,True if native else None,False,False,False,None,'model_definition' if native else 'unavailable',limitation=note,evidence=['backend_supported'] if native else ['software_detected']))
            records.append(Device('ace68:'+identity(item['physical']),item['name'],'keyboard',self.name,target,item['physical'],VID,PID,'usb',True,caps,faults=faults))
        return records
