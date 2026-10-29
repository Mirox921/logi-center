"""Backend-independent capability observations and supported operation metadata."""
from dataclasses import dataclass, field
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


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
