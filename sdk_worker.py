"""Short-lived optional backend API boundary. No automatic server/service start."""
import json,sys,os
from execution import Fault,FaultCode

def dispatch(backend,action,target=None,field=None,value=None):
    if action=='status':
        from importlib.metadata import version,PackageNotFoundError
        package={'openrgb':'openrgb-python','openrazer':'openrazer','rivalcfg':'rivalcfg'}.get(backend)
        if package is None:raise Fault(FaultCode.BACKEND_UNSUPPORTED,backend,'No component status probe')
        records=dispatch(backend,'discover')
        try:release=version(package)
        except PackageNotFoundError:release='version metadata unavailable'
        return {'version':release,'devices':len(records)}
    if backend=='mchose-ace68':
        from ace68_adapter import hardware
        return hardware(action,target,field,value)
    if backend=='mchose':
        from mchose_adapter import hardware
        return hardware(action,target,field,value)
    if backend=='rivalcfg':
        from rivalcfg_adapter import hardware
        return hardware(action,target,field,value)
    if backend=='openrazer':
        from openrazer_adapter import hardware
        return hardware(action,target,field,value)
    if backend=='openrgb':
        from openrgb_adapter import hardware
        return hardware(action,target,field,value)
    raise Fault(FaultCode.BACKEND_UNSUPPORTED,backend,'Unknown adapter')

if __name__=='__main__':
    os.umask(0o077)
    try:
        args=sys.argv[1:];args=args+[None]*(5-len(args))
        if args[4] is not None:args[4]=json.loads(args[4])
        print(json.dumps({'ok':True,'value':dispatch(*args)}))
    except Exception as error:
        from diagnostics import fault_for
        fault=fault_for(error,sys.argv[1] if len(sys.argv)>1 else 'sdk')
        print(json.dumps({'ok':False,'code':fault.code.value,'component':fault.component,'message':fault.message}))
