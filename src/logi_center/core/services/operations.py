"""Parameter-specific write/readback policies. Never upgrade cache data to device truth."""
from dataclasses import dataclass,field
from enum import Enum
import json,re,time
from logi_center.core.services.execution import Fault,FaultCode

class State(str,Enum):
    LOCAL='local_saved_only';UNSUPPORTED='unsupported';PERMISSION='permission_denied';CONFIRMED='confirmed';SENT='sent_unverified';MISMATCH='mismatch';ERROR='error';DISCONNECTED='disconnected';CANCELLED='cancelled'

@dataclass
class Observation:
    value:object
    source:str  # device, audio_server, backend_cache, local

@dataclass
class Result:
    state:State
    component:str
    requested:object=None
    actual:object=None
    source:str='unavailable'
    fault:Fault|None=None
    @property
    def accepted(self):return self.state in [State.CONFIRMED,State.SENT]

@dataclass
class Plan:
    command:list
    expected:object=None
    reader:object=None
    tolerance:float=0
    target:str=''


def numbers(text):return [int(x) for x in re.findall(r'\d+',text)]
def first_number(text):
    values=numbers(text)
    if not values:raise ValueError('No numeric readback')
    return values[0]

def macro_tokens(text):
    # Convert libratbag's display notation to the CLI token form.
    result=[]
    for arrow,key,delay in re.findall(r'([↓↑↕]?)(KEY_[A-Z0-9_]+)|(?:t|wait\s*)(\d+)',text):
        if delay:result.append('t'+delay)
        else:result.append({'↓':'+','↑':'-','↕':'','':''}[arrow]+key)
    return result

def action_value(parts):
    if parts[0]=='macro':return ['macro',*parts[1:]]
    return parts

def read_action(text):
    if 'macro' in text.lower() or any(x in text for x in ['↓','↑','↕']):return ['macro',*macro_tokens(text)]
    text=text.strip()
    match=re.search(r"mapped to (?:key )?'(.*)'",text)
    if match:text=match[1]
    else:text=text.strip("'")
    if text.startswith('button '):return ['button',str(first_number(text))]
    if text.endswith('mapped to none'):return ['disabled']
    if text.startswith('KEY_'):return ['key',text]
    if text.lower() in ['none','disabled']:return ['disabled']
    return ['special',text]

def plan_for(args):
    args=list(args);component=args[0]
    plan=Plan(args,target=args[1] if len(args)>1 else '')
    if component=='ratbagctl' and 'set' in args:
        pos=args.index('set');before=args[:pos];after=args[pos+1:]
        if not after:
            if before[-1] in ['enabled','disabled']:
                plan.expected=True;plan.reader=lambda runner:Observation(runner([*before,'get']).strip().lower()=='true','backend_cache')
            return plan
        if before[-2:]==['profile','active'] or before[-2:]==['resolution','active'] or before[-1] in ['rate','dpi','brightness','duration']:
            plan.expected=first_number(after[0])
            plan.reader=lambda runner:Observation(first_number(runner([*before,'get'])),'backend_cache')
        elif 'button' in before and before[-1]=='action':
            plan.expected=action_value(after)
            plan.reader=lambda runner:Observation(read_action(runner([*before,'get'])),'backend_cache')
        elif 'led' in before:
            field=after[0];raw=after[1] if len(after)>1 else None
            plan.expected=int(raw) if field in ('duration','brightness') else raw.lower() if isinstance(raw,str) and field in ('color','mode') else raw
            base=before+['get']
            def led_read(runner):
                text=runner(base)
                match=re.search(r'\b'+re.escape(field)+r':\s*([^,\s]+)',text)
                if not match:raise ValueError('LED property is not reported by this backend')
                value=int(match[1]) if field in ('duration','brightness') else match[1].lower()
                return Observation(value,'backend_cache')
            plan.reader=led_read
        return plan
    if component=='pactl' and len(args)>=3:
        operation=args[1]
        if operation.startswith('set-default-'):
            kind=operation.removeprefix('set-default-');plan.expected=args[2]
            plan.reader=lambda runner:Observation(runner(['pactl','get-default-'+kind]),'audio_server')
        elif re.fullmatch(r'set-(sink|source)-(volume|mute)',operation):
            kind,field=operation.split('-')[1:];name=args[2];raw=args[3]
            plan.expected=int(raw.rstrip('%')) if field=='volume' else raw in ['1','true']
            plan.tolerance=1 if field=='volume' else 0
            def audio_read(runner):
                devices=json.loads(runner(['pactl','-f','json','list',kind+'s']))
                device=next((d for d in devices if d['name']==name or str(d['index'])==name),None)
                if device is None:raise Fault(FaultCode.DISCONNECTED,'pactl','Audio device is disconnected')
                value=[int(v['value_percent'].rstrip('%')) for v in device['volume'].values()] if field=='volume' else device['mute']
                return Observation(value,'audio_server')
            plan.reader=audio_read
    elif component=='easyeffects' and '-b' in args:
        plan.expected=args[-1]=='1'
        def bypass_read(runner):
            value=runner(['easyeffects','-b','3']).strip().lower()
            if value not in ['true','false','1','2','enabled','disabled']:raise ValueError('Unrecognized bypass readback')
            return Observation(value in ['true','1','enabled'],'backend_cache')
        plan.reader=bypass_read
    elif component=='solaar' and len(args)>=5:
        plan.expected=args[-1]
        # Explicitly supported live read only; RGB effects and timers are not readable.
        if args[3]=='brightness_control':
            plan.expected=int(args[-1])
            def brightness(runner):
                text=runner(args[:4]);match=re.search(r'^brightness_control\s*=\s*(\d+)',text,re.M)
                if not match:raise ValueError('Brightness readback unavailable')
                return Observation(int(match[1]),'device')
            plan.reader=brightness
    elif component=='headsetcontrol':plan.expected=args[-1]  # no sidetone getter in this backend
    return plan

def same(expected,actual,tolerance=0):
    if isinstance(actual,list) and isinstance(expected,(int,float)):
        return bool(actual) and all(abs(float(v)-expected)<=tolerance for v in actual)
    if isinstance(expected,(int,float)) and not isinstance(expected,bool) and isinstance(actual,(int,float)):
        return abs(expected-actual)<=tolerance
    if isinstance(expected,list) and isinstance(actual,list) and expected[:1]==actual[:1]==['macro']:
        def expanded(value):
            result=[]
            for token in value[1:]:result.extend(['+'+token,'-'+token] if token.startswith('KEY_') else [token])
            return result
        return expanded(expected)==expanded(actual)
    return expected==actual

def fault_state(fault,readback=False):
    if fault.code==FaultCode.DISCONNECTED:return State.DISCONNECTED
    if fault.code==FaultCode.CANCELLED:return State.CANCELLED
    if not readback and fault.code in [FaultCode.UNSUPPORTED,FaultCode.DEVICE_UNSUPPORTED,FaultCode.BACKEND_UNSUPPORTED]:return State.UNSUPPORTED
    if not readback and fault.code==FaultCode.PERMISSION:return State.PERMISSION
    return State.SENT if readback else State.ERROR

def perform(plan,runner=None,cancel=None):
    if runner is None:
        from logi_center.adapters.external.backend import run
        runner=run
    def call(args):
        if cancel is not None and cancel.is_set():raise Fault(FaultCode.CANCELLED,plan.command[0],'Operation cancelled')
        return runner(args,cancel=cancel) if cancel is not None else runner(args)
    component=plan.command[1] if plan.command[0]=='logi-sdk' and len(plan.command)>1 else plan.command[0]
    try:call(plan.command)
    except Fault as fault:
        state=fault_state(fault)
        return Result(state,component,plan.expected,fault=fault)
    except Exception as error:return Result(State.ERROR,component,plan.expected,fault=Fault(FaultCode.INTERNAL,component,type(error).__name__))
    if plan.reader is None:return Result(State.SENT,component,plan.expected)
    try:observation=plan.reader(call)
    except Fault as fault:
        state=fault_state(fault,readback=True)
        return Result(state,component,plan.expected,fault=fault)
    except Exception as error:return Result(State.SENT,component,plan.expected,fault=Fault(FaultCode.INTERNAL,component,'Readback unavailable: '+type(error).__name__))
    if not same(plan.expected,observation.value,plan.tolerance):state=State.MISMATCH
    else:state=State.CONFIRMED if observation.source in ['device','audio_server'] else State.LOCAL if observation.source in ['local','local_saved_settings'] else State.SENT
    return Result(state,component,plan.expected,observation.value,observation.source)
