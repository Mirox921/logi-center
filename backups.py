"""Checksummed, provenance-aware snapshots and allowlisted restore plans."""
from dataclasses import dataclass,field
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,re,uuid,os
from execution import Fault,FaultCode
from operations import plan_for,perform,State,Result,read_action

FORMAT='logi-center-device-backup';VERSION=1

def digest(document):
    payload={k:v for k,v in document.items() if k!='sha256'}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def seal(kind,model,settings,source):
    doc={'format':FORMAT,'version':VERSION,'created_at':datetime.now(timezone.utc).isoformat(),
         'device':{'kind':kind,'model':model},'source':source,'settings':settings,
         'coverage':'Supported fields reported by the selected backend only; not a firmware image.'}
    doc['sha256']=digest(doc);return doc

def snapshot(kind,target,runner=None):
    from backend import run,read_mouse,saved_keyboard
    runner=runner or run
    if kind=='mouse':
        data=read_mouse(target,runner=runner)
        match=re.search(r'Model:\s*(\S+)',data['text'])
        if not match:raise Fault(FaultCode.CONFIG,'backup','Mouse model not reported')
        profiles=[]
        for p in data['profiles']:
            item={k:v for k,v in p.items() if k!='buttons'}
            item['buttons']=[{'index':b['index'],'action':read_action('macro '+b['action'] if b['macro'] else b['action'])} for b in p['buttons']]
            profiles.append(item)
        return seal(kind,match[1],{'profiles':profiles},'backend_cache')
    if kind=='keyboard':
        data=saved_keyboard()
        if not data:raise Fault(FaultCode.DISCONNECTED,'solaar','No saved G515 settings are available')
        allowed=['rgb_control','brightness_control','rgb_idle_timeout','rgb_sleep_timeout','rgb_zone_1']
        return seal(kind,'G515:'+data.get('_modelId','unknown'),{k:data[k] for k in allowed if k in data},'local_saved_settings')
    if kind=='audio':
        settings={}
        for category in ['sinks','sources']:
            devices=json.loads(runner(['pactl','-f','json','list',category]))
            settings[category]=[{'name':d['name'],'volume':[int(v['value_percent'].rstrip('%')) for v in d['volume'].values()],'mute':d['mute']} for d in devices if not d['name'].endswith('.monitor') and not d['name'].startswith('easyeffects_')]
        return seal(kind,'local-audio-devices',settings,'audio_server')
    raise ValueError('Unknown backup kind')

def write_backup(document,path):
    validate(document)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with os.fdopen(os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w',encoding='utf-8') as out:json.dump(document,out,ensure_ascii=False,indent=2)
        temp.chmod(0o600);temp.replace(path)
    finally:temp.unlink(missing_ok=True)

def read_backup(path):
    path=Path(path)
    if path.stat().st_size>2*1024*1024:raise ValueError('Backup exceeds 2 MB')
    doc=json.loads(path.read_text());validate(doc);return doc

def integer(value,low,high):
    if type(value) is not int or not low<=value<=high:raise ValueError('Invalid numeric backup value')

def action(action):
    if not isinstance(action,list) or not action or len(action)>513 or not all(isinstance(token,str) for token in action):raise ValueError('Invalid button action')
    if action[0]=='disabled' and len(action)==1:return
    if action[0]=='button' and len(action)==2 and str(action[1]).isdigit():integer(int(action[1]),1,32);return
    if action[0]=='special' and len(action)==2 and action[1] in ['resolution-cycle-up','resolution-cycle-down','resolution-up','resolution-down','resolution-alternate','profile-cycle-up','profile-cycle-down','wheel-left','wheel-right','second-mode']:return
    if action[0]=='key' and len(action)==2 and re.fullmatch(r'KEY_[A-Z0-9_]+',action[1]):return
    if action[0]=='macro' and len(action)>1:
        down=set()
        for token in action[1:]:
            if not isinstance(token,str) or not re.fullmatch(r'[+-]?KEY_[A-Z0-9_]+|t\d{1,5}',token):raise ValueError('Invalid macro token')
            if token.startswith('+'):
                if token[1:] in down:raise ValueError('Key pressed twice without release')
                down.add(token[1:])
            elif token.startswith('-'):
                if token[1:] not in down:raise ValueError('Key released without press')
                down.remove(token[1:])
        if down:raise ValueError('Macro leaves a key held down')
        return
    raise ValueError('Unsupported button action')

def validate(doc):
    try:
        if not isinstance(doc,dict) or doc['format']!=FORMAT or (type(doc['version']) is not int or doc['version']!=VERSION):raise ValueError('Unsupported backup format/version')
        if doc.get('sha256')!=digest(doc):raise ValueError('Backup integrity check failed')
        kind=doc['device']['kind'];settings=doc['settings']
        if kind not in ['mouse','keyboard','audio'] or not isinstance(settings,dict):raise ValueError('Invalid device backup')
        if not isinstance(doc['device']['model'],str) or len(doc['device']['model'])>200:raise ValueError('Invalid device model')
        if kind=='mouse':
            profiles=settings['profiles']
            if not isinstance(profiles,list) or not 1<=len(profiles)<=16:raise ValueError('Invalid profiles')
            ids=set()
            for p in profiles:
                integer(p['index'],0,15)
                if p['index'] in ids:raise ValueError('Duplicate profile')
                ids.add(p['index']);integer(p['rate'],1,8000)
                if type(p['active']) is not bool:raise ValueError('Invalid active flag')
                for collection in ['buttons','resolutions','leds']:
                    if not isinstance(p[collection],list) or len(p[collection])>64:raise ValueError('Too many settings')
                    values=[v['index'] for v in p[collection]]
                    if len(values)!=len(set(values)):raise ValueError('Duplicate setting index')
                    for v in values:integer(v,0,63)
                for b in p['buttons']:action(b['action'])
                for r in p['resolutions']:
                    integer(r['dpi'],50,100000)
                    for flag in ['active','default','disabled']:
                        if type(r[flag]) is not bool:raise ValueError('Invalid resolution flag')
                for led in p['leds']:
                    if led['mode'] not in ['off','on','cycle','breathing']:raise ValueError('Unsupported LED mode')
                    if led.get('color') is not None and not re.fullmatch('[0-9a-fA-F]{6}',led['color']):raise ValueError('Invalid LED color')
                    for key,maximum in [('duration',10000),('brightness',255)]:
                        if led.get(key) is not None:integer(led[key],0,maximum)
        elif kind=='keyboard':
            if not set(settings)<={'rgb_control','brightness_control','rgb_idle_timeout','rgb_sleep_timeout','rgb_zone_1'}:raise ValueError('Unsupported keyboard property')
            for key,value in settings.items():
                if key=='rgb_control':
                    if value not in ['true','false']:raise ValueError('Invalid lighting control')
                elif key=='rgb_zone_1':
                    if not isinstance(value,dict) or not set(value)<={'ID','color','intensity','period','ramp','form','saturation','direction'}:raise ValueError('Invalid lighting effect')
                    for field,number in value.items():integer(int(str(number),0),0,0xffffff if field=='color' else 65535)
                else:integer(int(value),0,1800 if 'timeout' in key else 100)
        else:
            for key in ['sources','sinks']:
                if not isinstance(settings[key],list) or len(settings[key])>128:raise ValueError('Invalid audio devices')
                for d in settings[key]:
                    if not isinstance(d['name'],str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,250}',d['name']):raise ValueError('Invalid audio device name')
                    if type(d['mute']) is not bool or not 1<=len(d['volume'])<=32:raise ValueError('Invalid audio state')
                    for v in d['volume']:integer(v,0,100)
    except (KeyError,TypeError,AttributeError) as error:raise ValueError('Malformed backup structure') from error

@dataclass
class Change:
    category:str
    label:str
    args:list
    current:object=None
    desired:object=None
    id:str=""

@dataclass
class Preview:
    backup:dict
    current:dict
    changes:list=field(default_factory=list)
    skipped:list=field(default_factory=list)


def change_values(args,current,backup):
    def value(document):
        settings=document['settings']
        if args[0]=='ratbagctl':
            if args[2:4]==['profile','active']:return next((p['index']+1 for p in settings['profiles'] if p['active']),None)
            profile=next(p for p in settings['profiles'] if p['index']==int(args[3]))
            if args[4]=='rate':return profile['rate']
            if args[4]=='button':return next(b['action'] for b in profile['buttons'] if b['index']==int(args[5]))
            if args[4]=='led':return next(v.get(args[7]) for v in profile['leds'] if v['index']==int(args[5]))
            if args[4]=='resolution':
                if args[5] in ['active','default']:return next((r['index']+1 for r in profile['resolutions'] if r[args[5]]),None)
                resolution=next(r for r in profile['resolutions'] if r['index']==int(args[5]))
                return not resolution['disabled'] if args[6] in ['enabled','disabled'] else resolution['dpi']
        if args[0]=='solaar':return settings.get(args[3])
        if args[0]=='pactl':
            _,kind,field=args[1].split('-');node=next(d for d in settings[kind+'s'] if d['name']==args[2]);return node[field]
        return None
    return value(current),value(backup)

def preview(backup,current,target):
    validate(backup);validate(current)
    if backup['device']!=current['device']:raise ValueError('Backup model does not match this device')
    result=Preview(backup,current);kind=backup['device']['kind']
    def add(category,label,args):
        old,new=change_values(args,current,backup)
        key=hashlib.sha256(json.dumps(args,ensure_ascii=False).encode()).hexdigest()[:20]
        result.changes.append(Change(category,label,args,old,new,key))
    if kind=='mouse':
        old={p['index']:p for p in current['settings']['profiles']}
        for p in backup['settings']['profiles']:
            if p['index'] not in old:result.skipped.append('Profile '+str(p['index']+1)+' is unavailable');continue
            before=old[p['index']];base=['ratbagctl',target,'profile',str(p['index'])];name='Profile '+str(p['index']+1)
            if p['rate']!=before['rate']:add('dpi',name+' · polling rate → '+str(p['rate']),[*base,'rate','set',str(p['rate'])])
            for r in p['resolutions']:
                previous=next((v for v in before['resolutions'] if v['index']==r['index']),None)
                if previous is None:result.skipped.append(name+' · DPI stage unavailable');continue
                prefix=[*base,'resolution',str(r['index'])]
                if r['dpi']!=previous['dpi']:add('dpi',name+' · DPI → '+str(r['dpi']),[*prefix,'dpi','set',str(r['dpi'])])
                if r['disabled']!=previous['disabled']:add('dpi',name+' · DPI enabled state',[*prefix,'disabled' if r['disabled'] else 'enabled','set'])
                for flag in ['default','active']:
                    if r[flag] and not previous[flag]:add('dpi',name+' · '+flag+' DPI stage',[*base,'resolution',flag,'set',str(r['index'])])
            for b in p['buttons']:
                previous=next((v for v in before['buttons'] if v['index']==b['index']),None)
                if previous is None:result.skipped.append(name+' · button unavailable');continue
                if b['action']!=previous['action']:add('buttons',name+' · button '+str(b['index']+1)+' → '+' '.join(b['action']),[*base,'button',str(b['index']),'action','set',*b['action']])
            for led in p['leds']:
                previous=next((v for v in before['leds'] if v['index']==led['index']),None)
                if previous is None:result.skipped.append(name+' · lighting zone unavailable');continue
                for field in ['color','duration','brightness','mode']:
                    if led.get(field) is not None and led[field]!=previous.get(field):add('lighting',name+' · lighting '+str(led['index']+1)+' · '+field+' → '+str(led[field]),[*base,'led',str(led['index']),'set',field,str(led[field])])
        # Change active profile last; never activate profiles just to edit them.
        active=next((p for p in backup['settings']['profiles'] if p['active']),None)
        if active and active['index'] in old and not old[active['index']]['active']:add('profile','Active profile → '+str(active['index']+1),['ratbagctl',target,'profile','active','set',str(active['index'])])
    elif kind=='keyboard':
        for key,value in backup['settings'].items():
            if key not in current['settings']:result.skipped.append(key+' is unavailable');continue
            if value==current['settings'][key]:continue
            if key=='rgb_zone_1':value='!LEDEffectSetting '+json.dumps({k:int(str(v),0) for k,v in value.items()})
            add('lighting','G515 · '+key+' → '+str(value),['solaar','config','G515',key,str(value)])
    else:
        for collection,kind_name in [('sinks','sink'),('sources','source')]:
            old={d['name']:d for d in current['settings'][collection]}
            for d in backup['settings'][collection]:
                if d['name'] not in old:result.skipped.append('Audio device is unavailable');continue
                before=old[d['name']]
                if d['volume']!=before['volume']:
                    if len(set(d['volume']))!=1:result.skipped.append('Independent channel volume restore is not supported')
                    else:add('audio',kind_name+' · volume → '+str(d['volume'][0])+'%',['pactl','set-'+kind_name+'-volume',d['name'],str(d['volume'][0])+'%'])
                if d['mute']!=before['mute']:add('audio',kind_name+' · mute → '+str(d['mute']),['pactl','set-'+kind_name+'-mute',d['name'],'1' if d['mute'] else '0'])
    return result

@dataclass
class RestoreReport:
    results:list
    safety_copy:str
    skipped:list
    stopped:bool


def restore(preview,selected,target,runner=None,cancel=None,safety_root=None,on_result=None):
    from backend import run
    runner=runner or run;kind=preview.backup['device']['kind']
    # Re-read immediately before mutation; derive plans again, never execute file-provided commands.
    current=snapshot(kind,target,runner)
    if current['settings']!=preview.current['settings']:raise ValueError('Device settings changed since preview; review again')
    fresh=globals()['preview'](preview.backup,current,target)
    safety_root=Path(safety_root) if safety_root else Path.home()/'.local/state/logi-center/backups'
    path=safety_root/('before-restore-'+uuid.uuid4().hex+'.json');write_backup(current,path)
    results=[];stopped=False
    for change in fresh.changes:
        if change.category not in selected and change.id not in selected:continue
        result=perform(plan_for(change.args),runner,cancel=cancel);results.append((change.label,result))
        if on_result:on_result(result)
        if not result.accepted:stopped=True;break
    return RestoreReport(results,str(path),fresh.skipped,stopped)
