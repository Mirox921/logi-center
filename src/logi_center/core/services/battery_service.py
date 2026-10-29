"""Shared read-only battery polling extracted from GTK, independent of widgets."""
import json
from logi_center.adapters.external.linux_input import KernelBatteryAdapter
from logi_center.adapters.external.headset_adapter import HeadsetAdapter
from logi_center.core.devices.devices import now
from logi_center.core.services.diagnostics import fault_for


def collect(devices,runner=None,kernel_factory=KernelBatteryAdapter,headset_factory=HeadsetAdapter):
    from logi_center.adapters.external.backend import run
    runner=runner or run
    results=[];headset_result=None;headset_error=None
    for device in devices:
        if device.kind not in ('mouse','keyboard') or device.connected is False:continue
        if not any(c.name=='battery_status' and c.backend in ('mchose','openrazer','eweadn') for c in device.capabilities):continue
        for backend in ('mchose','openrazer','eweadn'):
            targets=device.targets.get(backend,[])
            if len(targets)!=1:continue
            try:
                action='battery' if backend=='mchose' else 'status' if backend=='eweadn' else 'read'
                state=json.loads(runner(['logi-sdk',backend,action,targets[0]]))
                if not isinstance(state,dict) or backend=='openrazer' and not isinstance(state.get('settings',{}),dict):
                    raise ValueError('Invalid battery response')
                results.append((device.id,backend,targets[0],state,None))
            except Exception as error:results.append((device.id,backend,targets[0],None,error))
    kernel=kernel_factory().discover();kernel_factory().associate([*devices,*kernel])
    if any(d.kind=='audio' and d.connected is not False and any(c.name=='battery_status' and c.backend=='headsetcontrol' for c in d.capabilities) for d in devices):
        try:headset_result=headset_factory(runner=runner).discover()
        except Exception as error:headset_error=error
    return results,kernel,headset_result,headset_error


def apply(devices,outcome):
    """Apply on the GUI thread, matching live IDs/selectors, never model/VID/PID."""
    results,kernel,headsets,headset_error=outcome
    failed=False;changed=False
    for ident,backend,target,state,error in results:
        current=next((d for d in devices if d.id==ident and d.connected is not False and target in d.targets.get(backend,[])),None)
        if current is None:continue
        current.faults=[f for f in current.faults if f.component!=backend]
        if error:
            failed=True;current.faults.append(fault_for(error,backend));continue
        if backend=='mchose':
            mode=state.get('identity',{}).get('mode') if isinstance(state.get('identity'),dict) else None
            observed_connection='usb' if mode==0 else 'wireless' if mode in (1,2) else None
            if observed_connection and current.connection!=observed_connection:
                current.connection=observed_connection;changed=True
        for cap in current.capabilities:
            if cap.backend!=backend or cap.name not in ('battery_status','charging'):continue
            entry=state.get('settings',{}).get(cap.name,{}) if backend=='openrazer' else {}
            value=entry.get('value') if backend=='openrazer' and isinstance(entry,dict) else state.get(cap.name) if backend in ('mchose','eweadn') else None
            changed|=cap.value!=value;cap.value=value
            # OpenRazer D-Bus values remain cache-sourced, as in its adapter.
            cap.source=('device' if backend in ('mchose','eweadn') else 'backend_cache') if value is not None else 'unavailable'
            cap.observed_at=now()
    for observed in kernel:
        matches=[d for d in devices if d.physical==observed.physical and d.kind==observed.kind and d.connected is not False]
        if len(matches)!=1:continue
        changed|=_apply_caps(matches[0],observed.capabilities)
    if headset_error:
        failed=True
        for d in devices:
            if 'headsetcontrol' in d.targets:d.faults=[f for f in d.faults if f.component!='headsetcontrol']+[fault_for(headset_error,'headsetcontrol')]
    elif headsets is not None:
        for observed in headsets:
            target=observed.target
            if sum(d.target==target for d in headsets)!=1:continue
            matches=[d for d in devices if d.connected is not False and (d.id==observed.id or target in d.targets.get('headsetcontrol',[]))]
            if len(matches)!=1:continue
            current=matches[0];current.faults=[f for f in current.faults if f.component!='headsetcontrol']
            changed|=_apply_caps(current,observed.capabilities)
    return failed,changed


def _apply_caps(current,observations):
    changed=False
    for observed in observations:
        if observed.name not in ('battery_status','charging'):continue
        cap=next((c for c in current.capabilities if c.name==observed.name and c.backend==observed.backend),None)
        if cap is None:current.capabilities.append(observed);changed=True
        else:
            changed|=cap.value!=observed.value;cap.value=observed.value;cap.source=observed.source;cap.observed_at=observed.observed_at
    return changed
