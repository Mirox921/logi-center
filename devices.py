"""Adapter registry, conservative physical identity and capability/evidence inventory.

No raw HID writes. Adapters own discovery/read; operation routing uses existing
parameter-specific plans and never broadcasts or blindly retries a write.
"""
from dataclasses import dataclass,field
from datetime import datetime,timezone
from pathlib import Path
from typing import Protocol
import hashlib,json,re,struct
from execution import Fault,FaultCode

def matches_name(name,query):
    """Case-insensitive substring search; normalize incidental whitespace."""
    normalize=lambda value:' '.join(value.casefold().split())
    return normalize(query) in normalize(name)

def now():return datetime.now(timezone.utc).isoformat()

@dataclass
class Capability:
    name:str
    backend:str
    supported:bool|None=None
    readable:bool=False
    writable:bool=False
    verifiable:bool=False
    value:object=None
    source:str='unavailable'
    observed_at:str=field(default_factory=now)
    choices:list=field(default_factory=list)
    minimum:float|None=None
    maximum:float|None=None
    limitation:str=''
    evidence:list=field(default_factory=lambda:['backend_supported'])
    last_operation:dict=field(default_factory=dict)
    plan:object=None
    label:str=""
    step:float=1

@dataclass
class Device:
    id:str
    name:str
    kind:str
    backend:str
    target:str=''
    physical:str='' # Internal bus path; never exported in public reports.
    vid:str=''
    pid:str=''
    connection:str='unknown'
    connected:bool|None=True
    capabilities:list=field(default_factory=list)
    simulated:bool=False
    faults:list=field(default_factory=list)
    backends:list=field(default_factory=list)
    targets:dict=field(default_factory=dict)
    def __post_init__(self):
        if not self.backends:self.backends=[self.backend]
        if not self.targets:self.targets={self.backend:[self.target]}

class Adapter(Protocol):
    name:str
    def discover(self)->list[Device]:...

class DeviceManager:
    def __init__(self,adapters=()):self.adapters=list(adapters);self.devices=[];self.faults=[]
    def discover(self):
        records=[];self.faults=[]
        for adapter in self.adapters:
            try:records.extend(adapter.discover())
            except Exception as error:
                from diagnostics import fault_for
                self.faults.append(fault_for(error,adapter.name))
        self.link_physical(records)
        self.devices=self.merge(records);return self.devices
    @staticmethod
    def link_physical(records):
        # Join incomplete CLI records only when both backend selectors and the
        # resolved kernel identity are unique. Two identical units remain separate.
        for item in records:
            if item.backend=='linux-input' or not item.physical or '|' in item.physical:continue
            # Same exact USB parent + a single input function of this kind. Keep
            # receiver slots separate when two input identities share that parent.
            inputs={p.physical for p in records if p.backend=='linux-input' and p.kind==item.kind and p.physical.split('|',1)[0]==item.physical}
            if len(inputs)==1:item.physical=next(iter(inputs))
        for item in records:
            if item.physical or not item.vid or not item.pid or item.simulated:continue
            peers=[p for p in records if not p.simulated and p.vid==item.vid and p.pid==item.pid and p.kind==item.kind]
            candidates={p.physical for p in peers if p.physical}
            same_backend=[p for p in peers if p.backend==item.backend]
            if len(candidates)==1 and len(same_backend)==1:item.physical=next(iter(candidates))
    @staticmethod
    def merge(records):
        merged={}
        for item in records:
            # Exact physical path only. VID/PID or model alone never merge units.
            key=('sim' if item.simulated else 'real',item.physical or item.id)
            if key not in merged:merged[key]=item;continue
            current=merged[key]
            if current.kind=='input':current.kind=item.kind
            if current.backend=='linux-input' and item.backend!='linux-input':
                current.name=item.name;current.kind=item.kind;current.backend=item.backend;current.target=item.target
            current.backends=list(dict.fromkeys([*current.backends,*item.backends]))
            for backend,targets in item.targets.items():current.targets[backend]=list(dict.fromkeys([*current.targets.get(backend,[]),*targets]))
            known={(c.name,c.backend) for c in current.capabilities}
            current.capabilities.extend(c for c in item.capabilities if (c.name,c.backend) not in known)
            current.faults.extend(item.faults)
        for device in merged.values():
            rgb=[c for c in device.capabilities if c.backend=='openrgb' and c.name in ['lighting','lighting_mode','brightness'] and c.writable]
            if rgb:
                for cap in device.capabilities:
                    if cap.backend!='openrgb' and cap.name in ['lighting','lighting_mode','brightness'] and cap.writable:
                        cap.writable=False;cap.limitation+=' RGB owner: OpenRGB; competing editor disabled.'
        return list(merged.values())
    def record_operation(self,args,result):
        backend=args[0]
        if backend=='logi-sdk' and len(args)>=5:
            backend,target,setting=args[1],args[3],args[4]
        else:
            target=args[1] if backend=='ratbagctl' and len(args)>1 else args[2] if backend in ['pactl','solaar'] and len(args)>2 else args[args.index('-d')+1] if backend=='headsetcontrol' and '-d' in args else None
        if target is None:return
        if args[0]!='logi-sdk':setting='dpi' if 'dpi' in args else 'polling_rate' if 'rate' in args else 'lighting' if 'led' in args else 'buttons' if 'button' in args else 'profiles' if 'profile' in args else 'sidetone' if backend=='headsetcontrol' else args[3] if backend=='solaar' else args[1].rsplit('-',1)[-1]
        for device in self.devices:
            if target not in device.targets.get(backend,[]):continue
            if result.state.value=='disconnected':device.connected=False
            for cap in device.capabilities:
                if cap.backend!=backend or cap.name.rsplit(':',1)[-1]!=setting:continue
                cap.last_operation={'state':result.state.value,'source':result.source,'at':now()}
                if result.actual is not None:cap.value=result.actual;cap.source=result.source;cap.observed_at=now()
                if result.state.value=='confirmed':
                    evidence='command_confirmed' if result.source=='device' else 'audio_server_command_confirmed'
                    if evidence not in cap.evidence:cap.evidence.append(evidence)
    def guard_command(self,args):
        """Apply the same ownership policy to editors and legacy backup writes."""
        if not args:return
        if args[0]=='logi-sdk' and len(args)>=5 and args[2]=='set':
            backend,target,setting=args[1],args[3],args[4]
            matches=[d for d in self.devices if target in d.targets.get(backend,[])]
            if len(matches)!=1:raise Fault(FaultCode.DISCONNECTED,'device-manager','Write target is absent or ambiguous')
            self.route(matches[0].id,setting,backend)
        if args[0]=='ratbagctl' and len(args)>2 and 'led' in args and 'set' in args:
            for device in self.devices:
                if args[1] in device.targets.get('ratbagctl',[]) and any(c.backend=='openrgb' and c.writable and c.name in ['lighting','lighting_mode'] for c in device.capabilities):
                    raise Fault(FaultCode.CONFIG,'device-manager','OpenRGB owns lighting for this device; competing writes are disabled')
    def route(self,device_id,setting,backend=None):
        device=next((d for d in self.devices if d.id==device_id),None)
        if device is None or device.connected is False:raise Fault(FaultCode.DISCONNECTED,'device-manager','Device is disconnected')
        matches=[c for c in device.capabilities if c.name==setting and c.writable and (backend is None or c.backend==backend)]
        if not matches:raise Fault(FaultCode.BACKEND_UNSUPPORTED,'device-manager','No writable capability reported')
        if len({c.backend for c in matches})>1:raise Fault(FaultCode.CONFIG,'device-manager','Multiple backends expose this setting; choose one explicitly')
        return matches[0]

def identity(path):return hashlib.sha256(str(path).encode()).hexdigest()[:24]

def usb_identity(path):
    """Return exact USB interface parent, shared by input/HID/ALSA siblings."""
    path=Path(path).resolve()
    for parent in [path,*path.parents]:
        try:
            vid=(parent/'idVendor').read_text().strip();pid=(parent/'idProduct').read_text().strip()
            return str(parent),vid,pid
        except OSError:pass
    return '', '', ''

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
            keyboard=all(bits&(1<<key) for key in [14,30,57]);mouse=bool(bits&(1<<272))
            if not keyboard and not mouse:continue
            physical,vid,pid=usb_identity(node)
            # Receiver slots/interface paths stay intact; stripping /inputN:slot
            # would incorrectly merge two devices behind one receiver.
            try:input_phys=(node/'phys').read_text().strip()
            except OSError:input_phys=''
            if physical and input_phys:physical+='|'+input_phys
            ident=physical or str(node.resolve())
            cap=Capability('standard_input',self.name,True,True,False,False,'keyboard' if keyboard else 'mouse','kernel',limitation='Kernel input detection does not imply RGB or remapping support.',evidence=['software_detected','read_observed'])
            records.append(Device(self.name+':'+identity(ident),name,'keyboard' if keyboard else 'mouse',self.name,physical=physical,vid=vid,pid=pid,connection='usb' if vid else 'unknown',capabilities=[cap]))
        return DeviceManager.merge(records)

class RatbagAdapter:
    name='ratbagctl'
    def __init__(self,runner=None,detailed=False):
        from backend import run
        self.run=runner or run;self.detailed=detailed
    def discover(self):
        from backend import mouse_list,read_mouse
        records=[]
        inventory=mouse_list(self.run(['ratbagctl','list']))
        for index,(target,name) in enumerate(inventory):
            if sum(item[0]==target for item in inventory)>1:
                records.append(Device('ratbag:ambiguous:'+target+':'+str(index),name,'mouse',self.name,target,connected=None,faults=[Fault(FaultCode.CONFIG,self.name,'Backend selector collision; writes disabled')]))
                continue
            if not self.detailed:
                records.append(Device('ratbag:'+target,name,'mouse',self.name,target));continue
            try:
                data=read_mouse(target,runner=self.run);caps=mouse_capabilities(data,target)
                model=re.search(r'Model:\s*(\S+)',data['text']);parts=model[1].split(':') if model else []
                vid,pid=(parts[1:3] if len(parts)>=3 else ('',''))
                records.append(Device('ratbag:'+target,name,'mouse',self.name,target,vid=vid,pid=pid,capabilities=caps))
            except Exception as error:
                from diagnostics import fault_for
                records.append(Device('ratbag:'+target,name,'mouse',self.name,target,connected=None,faults=[fault_for(error,self.name)]))
        return records

def mouse_capabilities(data,target=""):
    active=next((p for p in data.get('profiles',[]) if p['index']==data.get('active')),None)
    if active is None:return []
    result=[]
    def add(name,value,writable,choices=(),limitation=''):
        result.append(Capability(name,'ratbagctl',True,True,writable,False,value,'backend_cache',choices=list(choices),limitation=limitation or 'ratbagd properties may be cached; physical writes are unverified.',evidence=['software_detected','read_observed']))
    if data.get('dpis') and active.get('resolutions'):add('dpi',[r['dpi'] for r in active['resolutions']],True,data['dpis'])
    if data.get('rates'):add('polling_rate',active.get('rate'),True,data['rates'])
    if len(data.get('profiles',[]))>1:add('profiles',data.get('active'),True,[p['index'] for p in data['profiles']])
    if active.get('buttons'):
        types=data.get('button_types',{});add('buttons',len(active['buttons']),bool(types))
        add('macros',None,any(4 in t for t in types.values()),limitation='Editing requires ActionTypes=macro on each selected button; unknown is read-only.')
    if active.get('leds'):add('lighting',len(active['leds']),any(data.get('led_modes',{}).values()))
    if target:
        from operations import plan_for
        base=['ratbagctl',target,'profile',str(active['index'])]
        resolution=next((r for r in active.get('resolutions',[]) if r['active']),None)
        for cap in result:
            if cap.name=='dpi' and resolution:
                cap.value=resolution['dpi'];cap.plan=lambda value,b=base,r=resolution:plan_for([*b,'resolution',str(r['index']),'dpi','set',str(value)])
            elif cap.name=='polling_rate':cap.plan=lambda value,b=base:plan_for([*b,'rate','set',str(value)])
            elif cap.name=='profiles':cap.plan=lambda value,t=target:plan_for(['ratbagctl',t,'profile','active','set',str(value)])
    return result

class PulseAdapter:
    name='pactl'
    def __init__(self,runner=None):
        from backend import run
        self.run=runner or run
    def discover(self):
        records=[]
        for collection,kind in [('sinks','output'),('sources','microphone')]:
            for node in json.loads(self.run(['pactl','-f','json','list',collection])):
                name=node['name']
                if name.endswith('.monitor') or name.startswith('easyeffects_'):continue
                props=node.get('properties',{});card=str(props.get('alsa.card',''))
                physical,vid,pid=usb_identity('/sys/class/sound/card'+card+'/device') if card.isdigit() else ('','','')
                # Same sound card can expose several legitimate audio endpoints.
                physical=physical or ('alsa-card:'+card if card.isdigit() else '')
                prefix=kind+':'+name
                caps=[]
                volumes=node.get('volume',{})
                if isinstance(volumes,dict) and volumes and all(isinstance(v,dict) and re.fullmatch(r'\d+%',str(v.get('value_percent',''))) for v in volumes.values()):
                    level=int(next(iter(volumes.values()))['value_percent'].rstrip('%'))
                    caps.append(Capability(prefix+':volume',self.name,True,True,True,True,level,'audio_server',minimum=0,maximum=100,evidence=['software_detected','read_observed'],limitation='Setting volume changes all channels.'))
                if type(node.get('mute')) is bool:caps.append(Capability(prefix+':mute',self.name,True,True,True,True,node['mute'],'audio_server',choices=[False,True],evidence=['software_detected','read_observed']))
                from operations import plan_for
                for cap in caps:
                    setting=cap.name.rsplit(':',1)[-1]
                    cap.label=node.get('description','Audio endpoint')
                    cap.plan=lambda value,k=kind,n=name,f=setting:plan_for(['pactl','set-'+('sink' if k=='output' else 'source')+'-'+f,n,str(int(value))+'%' if f=='volume' else '1' if value else '0'])
                records.append(Device('pulse:'+prefix,node.get('description',name),'audio',self.name,name,physical,vid,pid,'usb' if vid else 'audio',capabilities=caps))
        return records

def usb_id(value):
    if type(value) is int:return f'{value:04x}' if 0<=value<=65535 else ''
    value=str(value or '').lower().removeprefix('0x')
    return value.zfill(4) if re.fullmatch('[0-9a-f]{1,4}',value) else ''

class HeadsetAdapter:
    name='headsetcontrol'
    def __init__(self,runner=None):
        from backend import run
        self.run=runner or run
    def discover(self):
        doc=json.loads(self.run(['headsetcontrol','-o','json']));result=[]
        for index,item in enumerate(doc.get('devices',[])):
            vid=usb_id(item.get('id_vendor'));pid=usb_id(item.get('id_product'))
            target=vid+':'+pid;capabilities=[]
            for cap in item.get('capabilities',[]):
                if not isinstance(cap,str):continue
                name=cap.removeprefix('CAP_').lower()
                battery=item.get('battery',{}) if name=='battery_status' else {}
                level=battery.get('level');readable=type(level) is int and 0<=level<=100 and battery.get('status') in ['BATTERY_AVAILABLE','BATTERY_CHARGING']
                source='device' if readable else 'unavailable'
                capabilities.append(Capability(name,self.name,True,readable,name=='sidetone' and bool(vid and pid),False,level if readable else None,source,minimum=0 if name=='sidetone' else None,maximum=128 if name=='sidetone' else None,limitation='Other reported features are diagnostic-only until a parameter-specific adapter is implemented.',evidence=['software_detected']))
            result.append(Device('headset:'+target+':'+str(index),item.get('device','USB headset'),'audio',self.name,target,vid=vid,pid=pid,connection='usb',connected=True if item.get('status','success')=='success' else None,capabilities=capabilities))
        from operations import plan_for
        for device in result:
            for cap in device.capabilities:
                if cap.name=='sidetone' and cap.writable:cap.plan=lambda value,t=device.target:plan_for(['headsetcontrol','-d',t,'-s',str(value)])
        # The CLI selects by VID/PID: ambiguous identical units must not be written.
        for d in result:
            if sum(other.target==d.target for other in result)>1:
                for cap in d.capabilities:cap.writable=False;cap.limitation='Multiple identical units; backend selector is ambiguous.'
        return result

class SavedSolaarAdapter:
    name='solaar-local'
    def __init__(self,path=None):self.path=path
    def discover(self):
        from backend import saved_solaar_devices
        result=[]
        for index,item in enumerate(saved_solaar_devices(self.path)):
            name=item.get('_NAME','Logitech device')
            caps=[Capability(key,self.name,None,True,False,False,value,'local_saved_settings',limitation='Saved configuration only; live feature support has not been probed.',evidence=['backend_supported']) for key,value in item.items() if not key.startswith('_')]
            result.append(Device('solaar-saved:'+identity(str(item.get('_serial') or item.get('_unitId') or str(item.get('_modelId',''))+':record:'+str(index))+name),name,'keyboard' if 'keyboard' in name.lower() or 'G515' in name else 'input',self.name,connected=None,capabilities=caps))
        return result


def serial_usb_identity(serial,root='/sys/bus/usb/devices'):
    """Private exact serial + unique physical USB parent, never public report data."""
    if not serial or len(serial)<4 or len(set(serial))==1:return '', '', ''
    matches=[]
    for node in Path(root).glob('*'):
        try:
            if (node/'serial').read_text().strip()==serial:
                item=usb_identity(node)
                if item[0] and item not in matches:matches.append(item)
        except OSError:continue
    return matches[0] if len(matches)==1 else ('','','')
