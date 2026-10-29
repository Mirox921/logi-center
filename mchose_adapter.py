"""Bounded MCHOSE L7-family protocol adapter, derived from upstream PROTOCOL.md.

Unlike upstream Config::read, reading never reselects a profile. No firmware,
raw-command console or arbitrary report IDs are exposed. Run hardware I/O in
sdk_worker.py so a stalled ioctl cannot block GTK or outlive its deadline.
"""
from pathlib import Path
import json,re,os,time,fcntl,struct,select
from devices import Device,Capability,identity,usb_identity
from execution import Fault,FaultCode
from operations import Plan,Observation
from drafts import atomic_json

RATES=[125,500,1000,2000,4000,8000]

# K7 Ultra's own M HUB lightSetting panel (3837:1001), not MagDock 3837:1012.
DOCK_EFFECTS={'battery':1,'breathing':2,'flash':3,'cycle':4,'stars':5,'static':6,'wave':7}

def dock_values(record):
    if len(record)!=15 or record[0] not in (0,1):raise ValueError('Invalid K7 dock RGB record')
    mode=next((name for name,index in DOCK_EFFECTS.items() if index==record[1]),'unknown')
    return {'enabled':bool(record[0]),'mode':mode,'color':list(record[8:11]),
            'brightness':record[3] if record[3]<=100 else None,
            'duration':record[6] if record[6]<=2 else None,
            'direction':record[14] if record[14]<=1 else None}

def prepare_dock_record(original,changes):
    dock_values(original)
    if not isinstance(changes,dict) or not changes or set(changes)-{'enabled','mode','color','brightness','duration','direction'}:
        raise ValueError('Invalid K7 dock setting fields')
    result=bytearray(original)
    for name,value in changes.items():
        if name=='enabled':
            if type(value) is not bool:raise ValueError('Expected a dock lighting switch')
            result[0]=int(value)
        elif name=='mode':
            if value=='off':result[0]=0
            elif isinstance(value,str) and value in DOCK_EFFECTS:
                result[0]=1;result[1]=DOCK_EFFECTS[value]
                result[2]=result[4]=result[7]=0  # native mode, per M HUB
            else:raise ValueError('Unsupported K7 native dock effect')
        elif name=='color':
            if not isinstance(value,list) or len(value)!=3 or any(type(v) is not int or not 0<=v<=255 for v in value):
                raise ValueError('Expected three RGB channels')
            result[8:11]=bytes(value);result[11:14]=bytes(value)  # both M HUB color triplets
        else:
            maximum={'brightness':100,'duration':2,'direction':1}[name]
            if type(value) is not int or not 0<=value<=maximum:raise ValueError('K7 dock value outside M HUB range')
            result[{'brightness':3,'duration':6,'direction':14}[name]]=value
            if name=='brightness':result[0]=1 if value else 0
    if changes.get('mode')=='off':result[0]=0
    if 'enabled' in changes:result[0]=int(changes['enabled'])
    return bytes(result)

def _dock_record(device):
    record=device.exchange(0x11,0x1b)
    if len(record)<15:raise ValueError('Short K7 dock RGB record')
    record=bytes(record[:15]);dock_values(record)
    return record

def _is_k7_dock(candidate,ident):
    return ((candidate['vid'],candidate['pid'])==('3837','1001') and
            (ident.get('vid'),ident.get('pid'))==(0x3837,0x4150))

def candidates(root='/sys/class/hidraw'):
    result=[]
    for node in sorted(Path(root).glob('hidraw*')):
        try:
            text=(node/'device/uevent').read_text();descriptor=(node/'device/report_descriptor').read_bytes()
        except OSError:continue
        match=re.search(r'HID_ID=[0-9A-Fa-f]+:([0-9A-Fa-f]+):([0-9A-Fa-f]+)',text)
        if not match or int(match[1],16) not in [0x3837,0x5253]:continue
        name=re.search(r'HID_NAME=(.*)',text);name=name[1] if name else 'MCHOSE'
        if 'G3' in name.upper() or int(match[2],16)==0x4245:continue
        if not all(token in descriptor for token in [b'\x06\x01\xff',b'\x85\x11',b'\x85\x12']):continue
        physical,vid,pid=usb_identity(node/'device')
        result.append({'node':'/dev/'+node.name,'name':name,'vid':f'{int(match[1],16):04x}','pid':f'{int(match[2],16):04x}','generation':str((node/'device').resolve()),'physical':physical or str((node/'device').resolve())})
    return result

def selector(item):return identity(item['physical']+'|'+item['generation']) if item.get('generation') else identity(item['physical'])

def decode(body,ident):
    if len(body)!=63 or not any(body):raise ValueError('Empty/short config; no profile recovery is attempted')
    stages=[int.from_bytes(body[4+i*2:6+i*2],'little') for i in range(6)]
    if not 1<=body[16]<=6 or any(not 50<=v<=65535 for v in stages) or body[0]>2:raise ValueError('Config does not match the supported family')
    pair=body[1] if ident['mode']==0 else body[2];stage=pair&15;rate=pair>>4
    if stage>=body[16] or rate>=len(RATES):raise ValueError('Invalid active stage/rate')
    state={'firmware_version':ident.get('firmware_code'),'dpi':stages[stage],'dpi_stages':stages,'stage':stage,'polling_rate':RATES[rate],'debounce':body[18],'sleep':body[19],'motion_sync':bool(body[17]&16),'ripple':bool(body[17]&4),'angle_snap':bool(body[17]&8),'profiles':body[0],'charging':ident.get('charging',False),'battery_status':ident['battery'],'raw':list(body),'identity':ident}
    if (ident.get('vid'),ident.get('pid'))==(0x3837,0x4150):
        from k7_settings import values
        state.update(values(body,ident['mode']))
    return state

class Transport:
    def __init__(self,node):self.node=node;self.fd=None;self.last=0
    def __enter__(self):
        try:self.fd=os.open(self.node,os.O_RDWR|os.O_CLOEXEC)
        except FileNotFoundError:raise Fault(FaultCode.DISCONNECTED,'mchose','HID node disappeared or is unavailable in this environment') from None
        try:fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BaseException:os.close(self.fd);raise
        return self
    def __exit__(self,*unused):os.close(self.fd)
    def _drain(self):
        for unused in range(32):
            if not select.select([self.fd],[],[],0)[0]:break
            os.read(self.fd,128)
    def _wait_ready(self,command):
        deadline=time.monotonic()+.5
        while time.monotonic()<deadline:
            if not select.select([self.fd],[],[],max(0,deadline-time.monotonic()))[0]:return
            raw=os.read(self.fd,128)
            if len(raw)>=3 and raw[0] in [0x13,0x14] and raw[1]^255==0xE5 and raw[2]^255==command:return
    def exchange(self,report,command,args=b'',reply=True):
        if report not in [0x11,0x12]:raise ValueError('Unsupported report')
        size=21 if report==0x11 else 65
        if len(args)>size-2:raise ValueError('Oversized report')
        for attempt in range(3 if command in [0x06,0x67] else 1):
            if reply:self._drain()
            time.sleep(max(0,.025-(time.monotonic()-self.last)))
            frame=bytearray([report]+[255]*(size-1));payload=bytes([command])+args
            frame[1:len(payload)+1]=bytes(v^255 for v in payload)
            fcntl.ioctl(self.fd,(3<<30)|(size<<16)|(ord('H')<<8)|6,frame,True);self.last=time.monotonic()
            if not reply:return None
            self._wait_ready(command)
            time.sleep(.025);response=bytearray(size);response[0]=report
            length=fcntl.ioctl(self.fd,(3<<30)|(size<<16)|(ord('H')<<8)|7,response,True);self.last=time.monotonic()
            if 2<=length<=size and response[0]==report and response[1]^255==command:return bytes(v^255 for v in response[2:length])
        raise Fault(FaultCode.CONNECTION,'mchose','No matching protocol response')
    def read_identity(self):
        for attempt in range(4):
            data=self.exchange(0x11,0x06)
            if len(data)>=11 and any(data[:4]):break
            time.sleep(.12)
        else:raise Fault(FaultCode.CONNECTION,'mchose','Empty identity reply; profile recovery is never automatic')
        if len(data)<11:raise ValueError('Short identity reply')
        vid,pid=struct.unpack_from('<HH',data)
        if vid not in [0x3837,0x5253] or data[8]&7 not in [0,1,2]:raise ValueError('Protocol identity mismatch')
        if not data[8]&8:raise Fault(FaultCode.DISCONNECTED,'mchose','Receiver has no connected mouse')
        return {'vid':vid,'pid':pid,'firmware_code':hex(int.from_bytes(data[4:8],'little')),'mode':data[8]&7,'battery':data[9] if data[9]<=100 else None,'charging':bool(data[10])}

    def read(self):
        ident=self.read_identity()
        return decode(self.exchange(0x12,0x67),ident)

def hardware(action,node,field=None,value=None,transport=Transport):
    candidate=next((item for item in candidates() if selector(item)==node or action=='read' and item['node']==node),None)
    if not candidate:raise Fault(FaultCode.DISCONNECTED,'mchose','Validated configuration interface is absent')
    with transport(candidate['node']) as device:
        if action=='dock' or action=='set' and field=='dock_lighting':
            if action=='dock':
                if (candidate['vid'],candidate['pid'])!=('3837','1001') or 'K7 Ultra' not in candidate.get('name',''):
                    raise Fault(FaultCode.BACKEND_UNSUPPORTED,'mchose','K7 Ultra receiver identity is not confirmed')
                original=_dock_record(device)
                return {'dock_lighting':dock_values(original),'dock_rgb_record':list(original)}
            ident=device.read_identity()
            if not _is_k7_dock(candidate,ident):raise Fault(FaultCode.BACKEND_UNSUPPORTED,'mchose','K7 Ultra dock identity is not confirmed')
            original=_dock_record(device)
            if (not isinstance(value,dict) or set(value)!={'changes','expected_record'} or
                    not isinstance(value['expected_record'],list) or len(value['expected_record'])!=15 or
                    any(type(v) is not int or not 0<=v<=255 for v in value['expected_record'])):
                raise ValueError('Invalid K7 dock write context')
            if list(original)!=value['expected_record']:
                raise Fault(FaultCode.CONFIG,'mchose','Dock lighting changed since the command was prepared')
            proposed=prepare_dock_record(original,value['changes'])
            from datetime import datetime,timezone
            root=Path.home()/'.local/state/logi-center/backups'/('mchose-'+identity(candidate['physical']))
            atomic_json(root/(str(time.time_ns())+'-dock.json'),{'format':'k7-ultra-observed-rgb','version':1,
                'source':'device','created_at':datetime.now(timezone.utc).isoformat(),'rgb_record':list(original)})
            device.exchange(0x11,0x2b,proposed,reply=False)
            time.sleep(.08)
            actual=_dock_record(device)
            allowed={i for i,(before,after) in enumerate(zip(original,proposed)) if before!=after}
            if any(actual[i]!=original[i] for i in range(15) if i not in allowed):
                raise Fault(FaultCode.CONNECTION,'mchose','Unrelated dock RGB fields changed; private pre-write snapshot retained')
            return {'dock_lighting':dock_values(actual),'dock_rgb_record':list(actual)}
        if action=='battery':
            # The identity report already carries battery, charging and mode.
            # Do not fetch the configuration block for telemetry updates.
            ident=device.read_identity()
            expected=(int(candidate['vid'],16),int(candidate['pid'],16))
            allowed={expected,(0x3837,0x4150)} if expected==(0x3837,0x1001) else {expected}
            if (ident.get('vid'),ident.get('pid')) not in allowed:raise ValueError('USB and protocol identity disagree')
            return {'battery_status':ident['battery'],'charging':ident['charging'],'identity':ident}
        current=device.read()
        ident=current.get('identity',{})
        expected=(int(candidate['vid'],16),int(candidate['pid'],16))
        actual_identity=(ident.get('vid'),ident.get('pid'))
        allowed={expected,(0x3837,0x4150)} if expected==(0x3837,0x1001) else {expected}
        if ident and actual_identity not in allowed:raise ValueError('USB and protocol identity disagree')
        if action=='read':
            if _is_k7_dock(candidate,ident):
                try:
                    record=_dock_record(device)
                    current.update(dock_lighting=dock_values(record),dock_rgb_record=list(record))
                except Exception:current['dock_read_unavailable']=True
            return current
        if action!='set':raise ValueError('Unsupported operation')
        from k7_settings import FIELDS,prepare,unchanged
        if field in FIELDS:
            if (ident.get('vid'),ident.get('pid'))!=(0x3837,0x4150):
                raise Fault(FaultCode.BACKEND_UNSUPPORTED,'mchose','Native K7 settings require exact model identity')
            if (not isinstance(value,dict) or set(value)!={'changes','expected_raw','expected_mode'} or
                    type(value['expected_mode']) is not int or value['expected_mode'] not in (0,1,2) or
                    not isinstance(value['expected_raw'],list) or len(value['expected_raw'])!=63 or
                    any(type(v) is not int or not 0<=v<=255 for v in value['expected_raw'])):
                raise ValueError('Invalid K7 setting context')
            if value['expected_mode']!=ident.get('mode') or not unchanged(value['expected_raw'],current['raw'],{3:255}):
                raise Fault(FaultCode.CONFIG,'mchose','K7 configuration changed since the command was prepared')
            frames,allowed_changes=prepare(current['raw'],field,value['changes'],ident['mode'])
            from datetime import datetime,timezone
            root=Path.home()/'.local/state/logi-center/backups'/('mchose-'+identity(candidate['physical']))
            atomic_json(root/(str(time.time_ns())+'-k7.json'),{'format':'mchose-observed-config','version':1,
                'source':'device','created_at':datetime.now(timezone.utc).isoformat(),'settings':current})
            for report,command,args in frames:
                device.exchange(report,command,args,reply=False)
                time.sleep(.08)
                actual=device.read()
                if (actual.get('identity',{}).get('vid'),actual.get('identity',{}).get('pid'))!=(0x3837,0x4150):
                    raise Fault(FaultCode.DISCONNECTED,'mchose','K7 identity changed during apply')
                if not unchanged(current['raw'],actual['raw'],allowed_changes):
                    raise Fault(FaultCode.CONNECTION,'mchose','Unrelated K7 settings changed; private pre-write snapshot retained')
                if field=='button_bindings':
                    from k7_settings import values
                    index=str(args[0]);desired=value['changes'][index]
                    if values(actual['raw'])[field][index]!=desired:return actual  # stop at first mismatch, no retries
            return actual
        expected_profile=expected_stage=None
        if isinstance(value,dict):
            if set(value) not in ({'value','expected_profile'},{'value','expected_profile','expected_stage'}):
                raise ValueError('Invalid MCHOSE setting context')
            expected_profile=value['expected_profile'];expected_stage=value.get('expected_stage')
            if type(expected_profile) is not int or not 0<=expected_profile<=2:
                raise ValueError('Invalid expected MCHOSE profile')
            if 'expected_stage' in value and (field!='dpi' or type(expected_stage) is not int or not 0<=expected_stage<6):
                raise ValueError('Invalid expected MCHOSE DPI stage')
            value=value['value']
            if current['profiles']!=expected_profile or expected_stage is not None and current['stage']!=expected_stage:
                raise Fault(FaultCode.CONFIG,'mchose','Profile or DPI stage changed since the command was prepared')
        body=bytearray(current['raw'])
        # Validate everything before any setting report. Keep an independent private
        # snapshot of the observed block, never overwrite a user's previous backup.
        if field=='dpi':
            maximum=42000 if current['identity'].get('pid')==0x4150 else 26000
            if type(value) is not int or not 50<=value<=maximum or value%50:raise ValueError(f'DPI must be 50..{maximum} in steps of 50')
            stage=current['stage'];body[4+stage*2:6+stage*2]=value.to_bytes(2,'little');body[51+stage*2:53+stage*2]=value.to_bytes(2,'little')
        elif field in ['stage','profiles','debounce','sleep']:
            maximum={'stage':len(current['dpi_stages'])-1,'profiles':2,
                     'debounce':20 if actual_identity==(0x3837,0x4150) else 255,'sleep':255}[field]
            if type(value) is not int or not 0<=value<=maximum:raise ValueError('Value outside protocol range')
            if field=='stage':
                if value>=body[16]:raise ValueError('DPI stage is disabled')
                body[1]=(body[1]&240)|value;body[2]=(body[2]&240)|value
            elif field=='debounce':body[18]=value
            elif field=='sleep':body[19]=value
        elif field=='polling_rate':
            if value not in RATES:raise ValueError('Unsupported rate')
        else:raise Fault(FaultCode.BACKEND_UNSUPPORTED,'mchose','No safe write policy for this setting')
        from datetime import datetime,timezone
        root=Path.home()/'.local/state/logi-center/backups'/('mchose-'+identity(candidate['physical']))
        atomic_json(root/(str(time.time_ns())+'.json'),{'format':'mchose-observed-config','version':1,'source':'device','vid':candidate['vid'],'pid':candidate['pid'],'created_at':datetime.now(timezone.utc).isoformat(),'settings':current})
        if field=='profiles':device.exchange(0x11,0x58,bytes([value]),reply=False)
        elif field=='polling_rate':
            index=RATES.index(value);device.exchange(0x11,0x41,bytes([index,index]),reply=False)
        elif actual_identity==(0x3837,0x4150) and field=='sleep':
            device.exchange(0x11,0x0a,bytes([int(bool(value)),value]),reply=False)
        elif actual_identity==(0x3837,0x4150) and field=='debounce':
            device.exchange(0x11,0x43,bytes([value]),reply=False)
        else:device.exchange(0x12,0x57,bytes(body),reply=False)
        time.sleep(.08)
        actual=device.read()
        if (expected_profile is not None and field!='profiles' and actual['profiles']!=expected_profile or
                expected_stage is not None and actual['stage']!=expected_stage):
            raise Fault(FaultCode.CONNECTION,'mchose','Profile or DPI stage changed during apply; private snapshot retained')
        if field!='profiles':
            allowed={3,17}
            if field=='dpi':allowed.update([4+stage*2,5+stage*2,51+stage*2,52+stage*2])
            elif field in ['stage','polling_rate']:allowed.update([1,2])
            elif field=='debounce':allowed.add(18)
            elif field=='sleep':allowed.add(19)
            changed=[i for i,(a,b) in enumerate(zip(current['raw'],actual['raw'])) if a!=b and i not in allowed]
            if changed or (current['raw'][17]^actual['raw'][17])&254:raise Fault(FaultCode.CONNECTION,'mchose','Partial apply: unrelated configuration changed. Private pre-write snapshot retained; inspect device before continuing.')
        return actual

class MchoseAdapter:
    name='mchose'
    def __init__(self,runner=None,root='/sys/class/hidraw'):
        from backend import run
        self.run=runner or run;self.root=root
    def associate(self,records):
        # The exact K7 receiver exports a keyboard interface for mouse bindings.
        # It is not a second physical keyboard; do not infer this for other models.
        for mouse in [d for d in records if d.backend==self.name and d.vid=='3837' and d.pid=='1001']:
            for peer in records:
                if peer.backend=='linux-input' and peer.kind=='keyboard' and peer.vid==mouse.vid and peer.pid==mouse.pid and peer.physical.split('|',1)[0]==mouse.physical:
                    peer.kind='interface'
    def discover(self):
        records=[]
        for item in candidates(self.root):
            caps=[];faults=[];connected=None;connection='unknown'
            try:
                state=json.loads(self.run(['logi-sdk','mchose','read',item['node']]))
                connected=True
                mode=state.get('identity',{}).get('mode')
                connection='usb' if mode==0 else 'wireless' if mode in (1,2) else 'unknown'
                for field in ['firmware_version','dpi','stage','polling_rate','debounce','sleep','profiles','battery_status','charging','motion_sync','ripple','angle_snap']:
                    value=state.get(field)
                    # Keep an unreadable battery field as an explicit unknown
                    # capability so the UI can say that charge was not reported.
                    if value is None and field!='battery_status':continue
                    writable=field in ['dpi','stage','polling_rate','debounce','sleep','profiles']
                    choices=RATES if field=='polling_rate' else list(range(state['raw'][16])) if field=='stage' else [0,1,2] if field=='profiles' else []
                    low,high=(50,42000 if state.get('identity',{}).get('pid')==0x4150 else 26000) if field=='dpi' else (0,255) if field in ['debounce','sleep'] else (None,None)
                    if field=='debounce' and (state.get('identity',{}).get('vid'),state.get('identity',{}).get('pid'))==(0x3837,0x4150):high=20
                    cap=Capability(field,self.name,True,True,writable,writable,value,'device',choices=choices,minimum=low,maximum=high,limitation='Documented L7-family layout; K7 DPI change/readback/restore physically checked; other writes require model-specific testing. LOD and combined performance-flag writes are unavailable.',evidence=['software_detected','read_observed'])
                    if field=='dpi':cap.step=50
                    if writable:cap.plan=lambda value,f=field,n=selector(item),p=state['profiles'],s=state['stage']:setting_plan(n,f,value,p,s if f=='dpi' else None)
                    caps.append(cap)
                caps.append(Capability('dpi_stages',self.name,True,True,False,False,state['dpi_stages'],'device',limitation='Stage values are read; edit DPI after selecting an enabled stage.'))
                if 'dock_lighting' in state and 'dock_rgb_record' in state:
                    caps.append(dock_capability(selector(item),state))
                caps.extend(k7_capabilities(selector(item),state))
            except Exception as error:
                from diagnostics import fault_for
                fault=fault_for(error,self.name);faults.append(fault);connected=False if fault.code==FaultCode.DISCONNECTED else None
                # The matched protocol family has a battery field, but a failed
                # read does not reveal whether the device has one or its charge.
                caps.append(Capability('battery_status',self.name,None,False,False,False,None,'unavailable',limitation='Charge could not be read; battery support and current state are unknown.',evidence=['backend_supported']))
            records.append(Device('mchose:'+identity(item['physical']),item['name'],'mouse',self.name,selector(item),item['physical'],item['vid'],item['pid'],connection,connected,caps,faults=faults))
        return records

def setting_plan(node,field,value,profile=None,stage=None):
    payload=value if profile is None else {'value':value,'expected_profile':profile}
    if stage is not None:
        if profile is None or field!='dpi':raise ValueError('A DPI-stage guard requires a profile and a DPI setting')
        payload['expected_stage']=stage
    command=['logi-sdk','mchose','set',node,field,json.dumps(payload)]
    def read(runner):
        observed=json.loads(runner(['logi-sdk','mchose','read',node]))
        if (profile is not None and field!='profiles' and observed['profiles']!=profile or
                stage is not None and observed['stage']!=stage):
            raise Fault(FaultCode.CONNECTION,'mchose','Profile or DPI stage changed during readback')
        return Observation(observed[field],'device')
    return Plan(command,value,read,target=node)

def dock_setting_plan(node,changes,record):
    changes=dict(changes)
    if changes.get('mode')=='off':changes.pop('mode');changes['enabled']=False
    prepare_dock_record(record,changes)  # validate before creating an executable plan
    command=['logi-sdk','mchose','set',node,'dock_lighting',json.dumps({'changes':changes,'expected_record':list(record)})]
    def read(runner):
        state=json.loads(runner(['logi-sdk','mchose','dock',node]))['dock_lighting']
        return Observation({name:state[name] for name in changes},'device')
    return Plan(command,changes,read,target=node)

def dock_capability(target,state):
    record=bytes(state['dock_rgb_record']);dock_values(record)
    cap=Capability('dock_lighting','mchose',True,True,True,True,state['dock_lighting'],'device',
                   limitation='Native K7 Ultra dock effects; record readback does not verify visible animation.')
    cap.plan=lambda changes:dock_setting_plan(target,changes,record)
    return cap


def k7_setting_plan(target,field,changes,raw,mode):
    from k7_settings import prepare
    changes=dict(changes);prepare(raw,field,changes,mode)
    command=['logi-sdk','mchose','set',target,field,json.dumps({'changes':changes,'expected_raw':list(raw),'expected_mode':mode})]
    def read(runner):
        state=json.loads(runner(['logi-sdk','mchose','read',target]))
        ident=state.get('identity',{})
        if state['profiles']!=raw[0] or ident.get('mode')!=mode or (ident.get('vid'),ident.get('pid'))!=(0x3837,0x4150):
            raise Fault(FaultCode.CONFIG,'mchose','K7 context changed during readback')
        return Observation({key:state[field][key] for key in changes},'device')
    return Plan(command,changes,read,target=target)


def k7_capabilities(target,state):
    from k7_settings import FIELDS
    ident=state.get('identity',{})
    if (ident.get('vid'),ident.get('pid'))!=(0x3837,0x4150):return []
    result=[]
    for field in FIELDS:
        if field not in state:continue
        cap=Capability(field,'mchose',True,True,True,True,state[field],'device',
            limitation='Native K7 M HUB command; new setting combinations require physical verification.')
        if field=='sensor_config' and state[field].get('lod') not in (0,1,2):cap.writable=False
        if field=='dpi_config' and any(type(v) is not int or not 50<=v<=42000 or v%50 for k,v in state[field].items() if k[0] in ('x','y')):
            cap.writable=False
        cap.plan=lambda changes,f=field,r=tuple(state['raw']),m=ident['mode']:k7_setting_plan(target,f,changes,r,m)
        result.append(cap)
    return result


def update_observed(device,state):
    """Refresh existing capabilities and their exact write context after a read."""
    from copy import deepcopy
    from devices import now
    targets=device.targets.get('mchose',[])
    profile=state.get('profiles');stage=state.get('stage')
    changed=False
    if 'dock_lighting' in state and 'dock_rgb_record' in state and len(targets)==1:
        fresh=dock_capability(targets[0],state)
        existing=next((c for c in device.capabilities if c.backend=='mchose' and c.name=='dock_lighting'),None)
        if existing is None:device.capabilities.append(fresh);changed=True
        else:
            changed|=existing.value!=fresh.value
            existing.value=fresh.value;existing.plan=fresh.plan;existing.source='device';existing.observed_at=fresh.observed_at
    if len(targets)==1:
        for fresh in k7_capabilities(targets[0],state):
            existing=next((c for c in device.capabilities if c.backend=='mchose' and c.name==fresh.name),None)
            if existing is None:device.capabilities.append(fresh);changed=True
            else:
                changed|=existing.value!=fresh.value
                existing.value=fresh.value;existing.plan=fresh.plan;existing.source='device';existing.observed_at=fresh.observed_at
    for cap in device.capabilities:
        if cap.backend!='mchose' or cap.name not in state or cap.name in ('dock_lighting','dpi_config','button_bindings','sensor_config'):continue
        changed|=cap.value!=state[cap.name] or cap.source!='device'
        cap.value=deepcopy(state[cap.name]);cap.source='device';cap.observed_at=now()
        if (cap.writable and len(targets)==1 and type(profile) is int and 0<=profile<=2
                and (cap.name!='dpi' or type(stage) is int and 0<=stage<6)):
            cap.plan=lambda value,f=cap.name,n=targets[0],p=profile,s=stage:setting_plan(n,f,value,p,s if f=='dpi' else None)
    return changed
