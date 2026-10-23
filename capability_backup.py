"""Versioned scalar provider backups; commands always come from live capabilities."""
from pathlib import Path
from datetime import datetime,timezone
import json,uuid
from backups import digest,Preview,Change,RestoreReport
from drafts import atomic_json
from operations import perform

FORMAT='logi-center-capability-backup'
PROVIDERS={'mchose','openrgb','openrazer'}

def capture(device,runner=None):
    from backend import run
    runner=runner or run
    if device.connected is False:raise ValueError('Device disconnected')
    settings={}
    for backend,targets in device.targets.items():
        if backend not in PROVIDERS:continue
        if len(targets)!=1:raise ValueError('Ambiguous backend target')
        state=json.loads(runner(['logi-sdk',backend,'read',targets[0]]))
        for cap in device.capabilities:
            if cap.backend!=backend or not cap.readable:continue
            if backend=='openrazer':
                if cap.name not in state['settings']:continue
                value=state['settings'][cap.name]['value']
            else:
                if cap.name not in state:continue
                value=state[cap.name]
            if cap.name in ['raw','identity'] or value is None:continue
            settings[backend+':'+cap.name]={'value':value,'source':'device' if backend=='mchose' else 'backend_cache'}
    if not settings:raise ValueError('No readable provider settings')
    doc={'format':FORMAT,'version':1,'created_at':datetime.now(timezone.utc).isoformat(),'device':{'kind':device.kind,'model':device.name,'vid':device.vid,'pid':device.pid},'source':'per-setting provenance','settings':settings,'coverage':'Readable capability subset only. No firmware, full onboard memory or unknown macros.'}
    doc['sha256']=digest(doc);return doc


def validate(doc):
    if not isinstance(doc,dict) or doc.get('format')!=FORMAT or type(doc.get('version')) is not int or doc['version']!=1 or doc.get('sha256')!=digest(doc):raise ValueError('Invalid capability backup format/version/checksum')
    if not isinstance(doc.get('device'),dict) or any(not isinstance(doc['device'].get(k),str) or len(doc['device'][k])>256 for k in ['kind','model','vid','pid']):raise ValueError('Invalid device descriptor')
    if not isinstance(doc.get('settings'),dict) or len(doc['settings'])>256:raise ValueError('Invalid capability settings')
    for key,item in doc['settings'].items():
        if not isinstance(key,str) or len(key)>100 or key.split(':')[0] not in PROVIDERS or not isinstance(item,dict) or set(item)!={'value','source'} or item['source'] not in ['device','backend_cache']:raise ValueError('Invalid setting/provenance')
    if len(json.dumps(doc))>2*1024*1024:raise ValueError('Backup exceeds size limit')


def read(path):
    if Path(path).stat().st_size>2*1024*1024:raise ValueError('Backup exceeds size limit')
    doc=json.loads(Path(path).read_text());validate(doc);return doc


def write(doc,path):validate(doc);atomic_json(Path(path),doc)


def preview(doc,current,device):
    validate(doc);validate(current)
    if doc['device']!=current['device']:raise ValueError('Backup device/model identifiers differ')
    result=Preview(doc,current)
    caps={c.backend+':'+c.name:c for c in device.capabilities}
    for key,item in doc['settings'].items():
        cap=caps.get(key);observed=current['settings'].get(key)
        if cap is None or not cap.writable or cap.plan is None or observed is None:
            result.skipped.append(key+' · unsupported/read-only/not currently readable');continue
        desired=item['value']
        if cap.choices and desired not in cap.choices:raise ValueError(key+' is outside live choices')
        if cap.minimum is not None and (type(desired) not in [int,float] or not cap.minimum<=desired<=cap.maximum or (desired-cap.minimum)%cap.step):raise ValueError(key+' is outside live range')
        if desired==observed['value']:continue
        result.changes.append(Change('provider',key,[],observed['value'],desired,key))
    # Profile/stage selection precedes fields belonging to that profile/stage.
    result.changes.sort(key=lambda c:0 if c.id.endswith(':profiles') else 1 if c.id.endswith(':stage') else 2)
    return result


def restore(preview,selected,device,runner=None,safety_root=None,on_result=None):
    from backend import run
    runner=runner or run
    current=capture(device,runner)
    if current['settings']!=preview.current['settings']:raise ValueError('Device changed since preview; review again')
    fresh=globals()['preview'](preview.backup,current,device)
    root=Path(safety_root) if safety_root else Path.home()/'.local/state/logi-center/backups'
    path=root/('before-provider-restore-'+uuid.uuid4().hex+'.json');write(current,path)
    caps={c.backend+':'+c.name:c for c in device.capabilities};results=[];stopped=False
    for change in fresh.changes:
        if change.id not in selected:continue
        cap=caps[change.id]
        result=perform(cap.plan(change.desired),runner);results.append((change.label,result))
        if on_result:on_result(result)
        if not result.accepted:stopped=True;break
    return RestoreReport(results,str(path),fresh.skipped,stopped)
