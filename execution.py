"""Bounded, cancellable process execution and a shared fault vocabulary."""
from dataclasses import dataclass
from enum import Enum
import os,re,signal,subprocess,time
from contextvars import ContextVar
CURRENT_CANCEL=ContextVar("logi_operation_cancel",default=None)

class FaultCode(str,Enum):
    MISSING='missing_component';UNAVAILABLE='component_unavailable';PERMISSION='permission_denied'
    UNSUPPORTED='unsupported';DEVICE_UNSUPPORTED='device_unsupported';BACKEND_UNSUPPORTED='backend_unsupported';DISCONNECTED='disconnected';TIMEOUT='timeout';CANCELLED='cancelled'
    CONNECTION='connection_error';CONFIG='invalid_configuration';INTERNAL='internal_error'

@dataclass
class Fault(Exception):
    code:FaultCode
    component:str
    message:str
    def __str__(self):return f'{self.component}: {self.message}'

def redact(text):
    text=re.sub(r'/home/[^/\s]+', '~',str(text))
    text=re.sub(r'(?i)((?:serial|token|password|secret)[\w ]*\s*[:=]\s*)[^\s,]+',r'\1[redacted]',text)
    text=re.sub(r'alsa_(?:input|output)\.[A-Za-z0-9_.:-]+','[audio-device]',text)
    text=re.sub(r'\b(?:gh[pousr]_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]+)\b','[redacted]',text)
    return text[-1600:]

def classify(component,text):
    value=text.lower()
    if any(x in value for x in ['permission denied','operation not permitted','access denied']):code=FaultCode.PERMISSION
    elif any(x in value for x in ['no online device','no such device','device disconnected','device not found','invalid device','device is offline']):code=FaultCode.DISCONNECTED
    elif any(x in value for x in ['not implemented','unrecognized arguments','unknown command']):code=FaultCode.BACKEND_UNSUPPORTED
    elif any(x in value for x in ['feature not supported','capability','out of available range']):code=FaultCode.DEVICE_UNSUPPORTED
    elif any(x in value for x in ['not supported','unsupported']):code=FaultCode.UNSUPPORTED
    elif any(x in value for x in ['connection refused','failed to connect','dbus','connection failure']):code=FaultCode.CONNECTION
    elif any(x in value for x in ['invalid','configuration','parse error']):code=FaultCode.CONFIG
    else:code=FaultCode.UNAVAILABLE
    return Fault(code,component,redact(text) or 'Command failed')

def _stop(process):
    if process.poll() is not None:return
    try:os.killpg(process.pid,signal.SIGTERM)
    except ProcessLookupError:return
    try:process.communicate(timeout=.5)
    except subprocess.TimeoutExpired:
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        process.communicate()

def command(args,timeout=20,cancel=None):
    if cancel is None:cancel=CURRENT_CANCEL.get()
    component=os.path.basename(args[0]);env=dict(os.environ,LC_ALL='C.UTF-8')
    if cancel is not None and cancel.is_set():raise Fault(FaultCode.CANCELLED,component,'Operation cancelled')
    try:process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env,start_new_session=True)
    except FileNotFoundError:raise Fault(FaultCode.MISSING,component,'Required component is not installed') from None
    except PermissionError:raise Fault(FaultCode.PERMISSION,component,'Cannot execute component') from None
    deadline=time.monotonic()+timeout
    try:
        while True:
            if cancel is not None and cancel.is_set():raise Fault(FaultCode.CANCELLED,component,'Operation cancelled')
            remaining=deadline-time.monotonic()
            if remaining<=0:raise Fault(FaultCode.TIMEOUT,component,'Operation timed out')
            try:out,err=process.communicate(timeout=min(.2,remaining));break
            except subprocess.TimeoutExpired:continue
    except BaseException:
        _stop(process);raise
    if process.returncode:raise classify(component,err or out)
    return out.strip()
