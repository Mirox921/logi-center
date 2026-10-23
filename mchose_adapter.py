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
    return {'firmware_version':ident.get('firmware_code'),'dpi':stages[stage],'dpi_stages':stages,'stage':stage,'polling_rate':RATES[rate],'debounce':body[18],'sleep':body[19],'motion_sync':bool(body[17]&16),'ripple':bool(body[17]&4),'angle_snap':bool(body[17]&8),'profiles':body[0],'charging':ident.get('charging',False),'battery_status':ident['battery'],'raw':list(body),'identity':ident}

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
    def read(self):
        for attempt in range(4):
            data=self.exchange(0x11,0x06)
            if len(data)>=11 and any(data[:4]):break
            time.sleep(.12)
        else:raise Fault(FaultCode.CONNECTION,'mchose','Empty identity reply; profile recovery is never automatic')
        if len(data)<11:raise ValueError('Short identity reply')
        vid,pid=struct.unpack_from('<HH',data)
        if vid not in [0x3837,0x5253] or data[8]&7 not in [0,1,2]:raise ValueError('Protocol identity mismatch')
        if not data[8]&8:raise Fault(FaultCode.DISCONNECTED,'mchose','Receiver has no connected mouse')
        ident={'vid':vid,'pid':pid,'firmware_code':hex(int.from_bytes(data[4:8],'little')),'mode':data[8]&7,'battery':data[9] if data[9]<=100 else None,'charging':bool(data[10])}
        return decode(self.exchange(0x12,0x67),ident)

def hardware(action,node,field=None,value=None,transport=Transport):
    candidate=next((item for item in candidates() if selector(item)==node or action=='read' and item['node']==node),None)
    if not candidate:raise Fault(FaultCode.DISCONNECTED,'mchose','Validated configuration interface is absent')
    with transport(candidate['node']) as device:
        current=device.read()
        ident=current.get('identity',{})
        expected=(int(candidate['vid'],16),int(candidate['pid'],16))
        actual_identity=(ident.get('vid'),ident.get('pid'))
        allowed={expected,(0x3837,0x4150)} if expected==(0x3837,0x1001) else {expected}
        if ident and actual_identity not in allowed:raise ValueError('USB and protocol identity disagree')
        if action=='read':return current
        if action!='set':raise ValueError('Unsupported operation')
        body=bytearray(current['raw'])
        # Validate everything before any setting report. Keep an independent private
        # snapshot of the observed block, never overwrite a user's previous backup.
        if field=='dpi':
            maximum=42000 if current['identity'].get('pid')==0x4150 else 26000
            if type(value) is not int or not 50<=value<=maximum or value%50:raise ValueError(f'DPI must be 50..{maximum} in steps of 50')
            stage=current['stage'];body[4+stage*2:6+stage*2]=value.to_bytes(2,'little');body[51+stage*2:53+stage*2]=value.to_bytes(2,'little')
        elif field in ['stage','profiles','debounce','sleep']:
            maximum={'stage':len(current['dpi_stages'])-1,'profiles':2,'debounce':255,'sleep':255}[field]
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
        else:device.exchange(0x12,0x57,bytes(body),reply=False)
        time.sleep(.08)
        actual=device.read()
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
            caps=[];faults=[];connected=None
            try:
                state=json.loads(self.run(['logi-sdk','mchose','read',item['node']]))
                connected=True
                for field in ['firmware_version','dpi','stage','polling_rate','debounce','sleep','profiles','battery_status','charging','motion_sync','ripple','angle_snap']:
                    value=state.get(field)
                    if value is None:continue
                    writable=field in ['dpi','stage','polling_rate','debounce','sleep','profiles']
                    choices=RATES if field=='polling_rate' else list(range(state['raw'][16])) if field=='stage' else [0,1,2] if field=='profiles' else []
                    low,high=(50,42000 if state.get('identity',{}).get('pid')==0x4150 else 26000) if field=='dpi' else (0,255) if field in ['debounce','sleep'] else (None,None)
                    cap=Capability(field,self.name,True,True,writable,writable,value,'device',choices=choices,minimum=low,maximum=high,limitation='Documented L7-family layout; K7 DPI change/readback/restore physically checked; other writes require model-specific testing. LOD and combined performance-flag writes are unavailable.',evidence=['software_detected','read_observed'])
                    if field=='dpi':cap.step=50
                    if writable:cap.plan=lambda value,f=field,n=selector(item):setting_plan(n,f,value)
                    caps.append(cap)
                caps.append(Capability('dpi_stages',self.name,True,True,False,False,state['dpi_stages'],'device',limitation='Stage values are read; edit DPI after selecting an enabled stage.'))
            except Exception as error:
                from diagnostics import fault_for
                fault=fault_for(error,self.name);faults.append(fault);connected=False if fault.code==FaultCode.DISCONNECTED else None
            records.append(Device('mchose:'+identity(item['physical']),item['name'],'mouse',self.name,selector(item),item['physical'],item['vid'],item['pid'],'usb',connected,caps,faults=faults))
        return records

def setting_plan(node,field,value):
    command=['logi-sdk','mchose','set',node,field,json.dumps(value)]
    def read(runner):return Observation(json.loads(runner(['logi-sdk','mchose','read',node]))[field],'device')
    return Plan(command,value,read,target=node)
