"""Adapter registry, conservative physical identity and capability/evidence inventory.

No raw HID writes. Adapters own discovery/read; operation routing uses existing
parameter-specific plans and never broadcasts or blindly retries a write.
"""
from dataclasses import dataclass,field
from logi_center.core.capabilities.model import Capability
from datetime import datetime,timezone
from pathlib import Path
from typing import Protocol
from logi_center.core.services.execution import Fault,FaultCode

def matches_name(name,query):
    """Case-insensitive substring search; normalize incidental whitespace."""
    normalize=lambda value:' '.join(value.casefold().split())
    return normalize(query) in normalize(name)

def now():return datetime.now(timezone.utc).isoformat()

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
    private_identity:dict=field(default_factory=dict,repr=False)
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
                from logi_center.core.services.diagnostics import fault_for
                self.faults.append(fault_for(error,adapter.name))
        for adapter in sorted(self.adapters,key=lambda a:getattr(a,'association_priority',0)):
            associate=getattr(adapter,'associate',None)
            if associate:associate(records)
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
        # Some gaming mice expose a keyboard-like HID collection for vendor
        # buttons. Suppress only a sibling input node with the same USB parent,
        # VID/PID and exact model name after the conventional " Keyboard" suffix.
        # A shared product name or VID/PID without a shared physical parent is
        # never enough to hide a real keyboard.
        mice=[d for d in records if d.backend=='linux-input' and d.kind=='mouse' and d.physical and d.vid and d.pid]
        for candidate in records:
            if candidate.backend!='linux-input' or candidate.kind!='keyboard' or not candidate.physical or not candidate.vid or not candidate.pid:
                continue
            normalized=' '.join(candidate.name.casefold().split())
            suffix=' keyboard'
            if not normalized.endswith(suffix):continue
            model=normalized[:-len(suffix)]
            peers=[d for d in mice if d.vid==candidate.vid and d.pid==candidate.pid and d.physical.split('|',1)[0]==candidate.physical.split('|',1)[0] and ' '.join(d.name.casefold().split())==model]
            if len(peers)==1:candidate.kind='interface'
        merged={}
        for item in records:
            # Exact physical path only. VID/PID or model alone never merge units.
            key=('sim' if item.simulated else 'real',item.physical or item.id,item.kind)
            if key not in merged:merged[key]=item;continue
            current=merged[key]
            if current.kind=='input':current.kind=item.kind
            if current.backend=='linux-input' and item.backend not in ('linux-input','solaar-local','kernel-battery'):
                current.name=item.name;current.kind=item.kind;current.backend=item.backend;current.target=item.target
                if item.connection!='unknown' or item.backend=='mchose':
                    # The input bus identifies a USB receiver, not necessarily
                    # the link between receiver and mouse.
                    current.connection=item.connection
            if item.backend!='linux-input' and item.connected is False:current.connected=False
            elif current.connected is None and item.connected is True:current.connected=True
            current.backends=list(dict.fromkeys([*current.backends,*item.backends]))
            for backend,targets in item.targets.items():current.targets[backend]=list(dict.fromkeys([*current.targets.get(backend,[]),*targets]))
            known={(c.name,c.backend) for c in current.capabilities}
            current.capabilities.extend(c for c in item.capabilities if (c.name,c.backend) not in known)
            current.faults.extend(item.faults)
            for name,value in item.private_identity.items():
                if name not in current.private_identity:current.private_identity[name]=value
        for device in merged.values():
            rgb=[c for c in device.capabilities if c.backend=='openrgb' and c.name in ['lighting','lighting_mode','brightness','lighting_speed','lighting_palette'] and c.writable]
            if rgb:
                for cap in device.capabilities:
                    if cap.backend!='openrgb' and cap.name in ['lighting','lighting_mode','brightness','lighting_speed','lighting_palette'] and cap.writable:
                        cap.writable=False;cap.limitation+=' RGB owner: OpenRGB; competing editor disabled.'
        return list(merged.values())
    def active(self,kind,simulation=False):
        """Current discovery only; remembered pairings never enter control pages."""
        return [d for d in self.devices if d.kind==kind and d.simulated==simulation and d.backend!='solaar-local' and d.connected is not False and (d.connected is True or any(c.source=='kernel' for c in d.capabilities) or d.physical and Path(d.physical.split('|',1)[0]).exists())]
    def record_operation(self,args,result):
        backend=args[0]
        if backend=='logi-sdk' and len(args)>=5:
            backend,target,setting=args[1],args[3],args[4]
        else:
            target=args[1] if backend=='ratbagctl' and len(args)>1 else args[2] if backend in ['pactl','solaar'] and len(args)>2 else args[args.index('-d')+1] if backend=='headsetcontrol' and '-d' in args else None
        if target is None:return
        if args[0]=='logi-sdk' and backend=='mchose-ace68' and setting.startswith('profile/'):setting=setting.split('/')[-1]
        if args[0]!='logi-sdk':setting='dpi' if 'dpi' in args else 'polling_rate' if 'rate' in args else 'lighting' if 'led' in args else 'buttons' if 'button' in args else 'profiles' if 'profile' in args else 'sidetone' if backend=='headsetcontrol' else args[3] if backend=='solaar' else args[1].rsplit('-',1)[-1]
        for device in self.devices:
            if target not in device.targets.get(backend,[]):continue
            if result.state.value=='disconnected':device.connected=False
            for cap in device.capabilities:
                if cap.backend!=backend or cap.name.rsplit(':',1)[-1]!=setting:continue
                cap.last_operation={'state':result.state.value,'source':result.source,'at':now()}
                if result.actual is not None:
                    cap.value={**cap.value,**result.actual} if isinstance(cap.value,dict) and isinstance(result.actual,dict) else result.actual
                    cap.source=result.source;cap.observed_at=now()
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
            if backend=='mchose-ace68' and setting.startswith('profile/'):
                parts=setting.split('/')
                actual=next((c.value for c in matches[0].capabilities if c.name=='profiles' and c.backend==backend),None)
                if len(parts)!=3 or parts[1]!=str(actual):raise Fault(FaultCode.CONFIG,'device-manager','Profile changed; review the pending operation')
                setting=parts[2]
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
