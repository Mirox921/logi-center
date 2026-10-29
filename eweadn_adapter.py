"""EWEADN S9 adapter over verified ByteTech feature pages.

All ioctls run in sdk_worker; discovery/status never send configuration setters.
No arbitrary reports, firmware, pairing or macro-flash API is exported.
"""
from pathlib import Path
import os,re,time,fcntl,json,hashlib
from devices import Device,Capability,identity,usb_identity,now
from execution import Fault,FaultCode
from operations import Plan,Observation
from eweadn_protocol import REPORT_ID,PACKET_SIZE,FIELDS,RATES,decode,basics,packet,response,prepare

# Official Hub lists both shared receivers and model-specific wired products.
SUPPORTED_IDS={('372e',p) for p in ('1026','1027','103d','105e','1029','108d')}
WIRELESS={'1026','103d'}


def candidates(root='/sys/class/hidraw'):
    result=[]
    for node in sorted(Path(root).glob('hidraw*')):
        try:
            text=(node/'device/uevent').read_text();desc=(node/'device/report_descriptor').read_bytes()
        except OSError:continue
        match=re.search(r'HID_ID=[0-9A-Fa-f]+:([0-9A-Fa-f]+):([0-9A-Fa-f]+)',text)
        if not match:continue
        vid,pid=(f'{int(match[i],16):04x}' for i in (1,2))
        if (vid,pid) not in SUPPORTED_IDS:continue
        if not all(token in desc for token in (b'\x06\x00\xff',b'\x85\x03',b'\xb1\x02')):continue
        physical,_,_=usb_identity(node/'device');generation=str((node/'device').resolve())
        result.append(dict(node='/dev/'+node.name,vid=vid,pid=pid,physical=physical or generation,
                           generation=generation,descriptor=hashlib.sha256(desc).hexdigest()))
    return result


def selector(item):return identity(item['physical']+'|'+item['generation']+'|'+item['descriptor'])


class Transport:
    def __init__(self,node):self.node=node
    def __enter__(self):
        self.fd=os.open(self.node,os.O_RDWR|os.O_NONBLOCK)
        try:fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            os.close(self.fd);raise Fault(FaultCode.CONNECTION,'eweadn','Configuration interface is busy; close the vendor browser tab')
        return self
    def __exit__(self,*args):os.close(self.fd)
    def send(self,main,sub,data=b'',encap=0):
        buf=packet(main,sub,data,encap);request=(3<<30)|(len(buf)<<16)|(ord('H')<<8)|6
        fcntl.ioctl(self.fd,request,buf)
    def get(self):
        buf=bytearray(64);buf[0]=REPORT_ID
        fcntl.ioctl(self.fd,(3<<30)|(64<<16)|(ord('H')<<8)|7,buf,True)
        return bytes(buf)
    def read_page(self,page):
        # No background reader threads, lost replies, unbounded wake loops or
        # configuration retries. A stalled ioctl dies with the SDK deadline.
        needed={0:20,64:10,65:57,128:8,129:7}.get(page)
        if needed is None:raise ValueError('Page is not allowlisted')
        data=b''
        for index in range((needed+9)//10):
            chunk=None
            for attempt in range(3):
                self.send(79,page+index,encap=index)
                until=time.monotonic()+.85
                while time.monotonic()<until:
                    time.sleep(.08)
                    try:chunk=response(self.get(),page+index,index);break
                    except ValueError:continue
                if chunk is not None:break
            if chunk is None:
                if page==0 and len(data)>=12:return data  # base S9 exposes three slots
                if page==65 and len(data)>=41:return data  # independent Y may be absent
                raise Fault(FaultCode.TIMEOUT,'eweadn','No matching page response; move the mouse to wake it and retry')
            data+=chunk
            if len(data)>=needed:return data[:needed]
        return data


def read_state(device,connection):
    model=device.read_page(128)
    pages={128:model}
    for page in (129,64,65,0):pages[page]=device.read_page(page)
    return decode(pages,connection)


def fingerprint(state):
    return identity(json.dumps([state['model_id'],state['firmware_version'],state['connection'],state['pages']],sort_keys=True,separators=(',',':')))


def hardware(action,target,field=None,value=None,transport=Transport):
    matches=[item for item in candidates() if selector(item)==target]
    if len(matches)!=1:raise Fault(FaultCode.DISCONNECTED,'eweadn','Exact validated HID interface is absent or ambiguous')
    item=matches[0];connection='wireless' if item['pid'] in WIRELESS else 'usb'
    with transport(item['node']) as device:
        if action=='status':
            from eweadn_protocol import MODELS
            model=device.read_page(128)
            if len(model)<8 or int.from_bytes(model[2:8],'big') not in MODELS:
                raise Fault(FaultCode.DEVICE_UNSUPPORTED,'eweadn','Receiver is no longer paired with a verified S9 model')
            return basics(device.read_page(129))
        state=read_state(device,connection)
        if item['pid'] in ('103d','1029'):state['max_report']=0  # 1 kHz receiver / wired S9 Pro
        if action=='read':return state
        if action!='set' or field not in (*FIELDS,'factory_reset'):raise Fault(FaultCode.BACKEND_UNSUPPORTED,'eweadn','Unknown or unsafe operation')
        if not isinstance(value,dict) or set(value)!={'changes','profile','fingerprint'}:raise ValueError('Invalid guarded write request')
        if state['profiles']!=value['profile'] or fingerprint(state)!=value['fingerprint']:
            raise Fault(FaultCode.CONFIG,'eweadn','Configuration changed; read again before applying the saved draft')
        if field=='factory_reset':
            if value['changes']!={'confirm':True}:raise ValueError('Explicit reset confirmation required')
            commands=[(6,255,b'')];expected=None  # exact official reset-all command
        else:commands,expected=prepare(state,field,value['changes'])
        from drafts import atomic_json
        root=Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'logi-center/eweadn'
        atomic_json(root/(f'pre-write-{time.time_ns()}-'+target+'.json'),{'version':1,'state':state})
        key_progress=bytearray(state['pages']['0'])
        for main,sub,data in commands:
            sensor=device.read_page(64)
            if len(sensor)<10 or sensor[9]!=state['profiles']:
                raise Fault(FaultCode.CONNECTION,'eweadn','Profile changed during operation; partial changes may remain')
            device.send(main,sub,data)  # setters are never retried automatically
            time.sleep(.12)
            if main==48:
                key_progress[sub:sub+4]=data
                actual_keys=device.read_page(0)
                if bytes(actual_keys[:len(key_progress)])!=bytes(key_progress):
                    raise Fault(FaultCode.CONNECTION,'eweadn','Button write was not confirmed; remaining button writes stopped')
        if field=='factory_reset':return {'sent':True}  # no invented default/readback guarantee
        actual=read_state(device,connection)
        if actual['model_id']!=state['model_id'] or actual['profiles']!=state['profiles'] or actual['pages']!=expected:
            raise Fault(FaultCode.CONNECTION,'eweadn','Readback differs or unrelated fields changed; private snapshot retained')
        return actual


def setting_plan(target,field,changes,state):
    prepare(state,field,changes)
    request={'changes':changes,'profile':state['profiles'],'fingerprint':fingerprint(state)}
    expected={key:changes[key] for key in changes}
    def reader(run):
        # hardware(set) already compares the complete observed pages, not ACKs.
        # Read again through the same SDK boundary and check the profile.
        actual=json.loads(run(['logi-sdk','eweadn','read',target]))
        if actual['profiles']!=state['profiles']:raise Fault(FaultCode.CONNECTION,'eweadn','Profile changed during readback')
        return Observation({k:actual[field][k] for k in expected},'device')
    return Plan(['logi-sdk','eweadn','set',target,field,json.dumps(request)],expected,reader,target=target)


def reset_plan(target,state,confirmed):
    if confirmed is not True:raise ValueError('Explicit reset confirmation required')
    request={'changes':{'confirm':True},'profile':state['profiles'],'fingerprint':fingerprint(state)}
    return Plan(['logi-sdk','eweadn','set',target,'factory_reset',json.dumps(request)],True,target=target)


def capabilities(target,state):
    caps=[]
    for name in ('model_id','firmware_version','battery_status','charging','profiles','max_dpi','max_report','writable_buttons'):
        caps.append(Capability(name,'eweadn',True,True,False,False,state.get(name),'device'))
    for field in FIELDS:
        cap=Capability(field,'eweadn',True,True,True,True,state[field],'device')
        cap.plan=lambda changes,f=field:setting_plan(target,f,changes,state)
        caps.append(cap)
    cap=Capability('factory_reset','eweadn',True,False,True,False,None,'unavailable')
    cap.plan=lambda confirmed:reset_plan(target,state,confirmed);caps.append(cap)
    caps.extend([Capability('macros','eweadn',True,False,False,False,None,'unavailable',
        limitation='Official macro upload formats the device macro bank through an OTA path; existing bank read/rollback is unavailable. Local recording is supported.'),
        Capability('onboard_configuration','eweadn',True,True,False,False,None,'device')])
    return caps


class EweadnAdapter:
    name='eweadn'
    def __init__(self,root='/sys/bus/usb/devices',runner=None,hidroot='/sys/class/hidraw'):
        from backend import run
        self.root=Path(root);self.run=runner or run;self.hidroot=hidroot
    def associate(self,records):
        for mouse in records:
            if mouse.backend!=self.name or not any(c.name=='model_id' and c.source=='device' for c in mouse.capabilities):continue
            for peer in records:
                if peer.backend=='linux-input' and peer.kind=='keyboard' and peer.vid==mouse.vid and peer.pid==mouse.pid and peer.physical.split('|',1)[0]==mouse.physical:
                    peer.kind='interface'
    def discover(self):
        interfaces=candidates(self.hidroot);records=[]
        for path in sorted(self.root.glob('*')):
            try:vid=(path/'idVendor').read_text().strip().lower();pid=(path/'idProduct').read_text().strip().lower()
            except OSError:continue
            if (vid,pid) not in SUPPORTED_IDS:continue
            physical=str(path.resolve())
            try:name=(path/'product').read_text().strip()
            except OSError:name=''
            name=name or 'EWEADN receiver'
            matches=[i for i in interfaces if i['physical']==physical]
            target=selector(matches[0]) if len(matches)==1 else physical
            caps=[];faults=[]
            if len(matches)==1:
                try:
                    state=json.loads(self.run(['logi-sdk','eweadn','read',target]));name=state['name'];caps=capabilities(target,state)
                except Exception as error:
                    from diagnostics import fault_for
                    faults.append(fault_for(error,self.name))
            if not caps:caps=[Capability('onboard_configuration',self.name,None,False,False,False,None,'unavailable',
                limitation='S9 model identity and vendor interface could not be read; configuration writes are disabled.')]
            records.append(Device('eweadn:'+identity(physical),name,'mouse',self.name,target,physical,vid,pid,
                'wireless' if pid in WIRELESS else 'usb',True,caps,faults))
        return records
