"""Scoped G515 settings reads. No full Solaar enumeration or write recovery."""
import json,re
from copy import deepcopy
from logi_center.core.services.execution import Fault,FaultCode,CURRENT_CANCEL

READ_KEYS=('rgb_control','brightness_control','rgb_zone_1','per-key-lighting',
           'rgb_idle_timeout','rgb_sleep_timeout')
LIVE_KEYS={'rgb_control','brightness_control'}


def battery_from_text(text):
    match=re.search(r'^#   logi-center-battery: (\{[^\n]+\})$',text,re.M)
    if not match:return None
    state=json.loads(match[1])
    if not isinstance(state,dict) or type(state.get('charging')) not in (bool,type(None)):
        raise ValueError('Invalid G515 charging state')
    level=state.get('battery_status')
    if level is not None and (type(level) is not int or not 0<=level<=100):raise ValueError('Invalid G515 battery level')
    return {'battery_status':level,'charging':state.get('charging')}


def read_battery(target,runner):
    state=battery_from_text(runner(['solaar','config',target,'brightness_control'],timeout=5))
    if state is None:raise Fault(FaultCode.UNSUPPORTED,'solaar-battery','Battery getter did not report state')
    return state


def rgb_capabilities(text):
    match=re.search(r'^#   logi-center-rgb: (\{[^\n]+\})$',text,re.M)
    if not match:return None
    info=json.loads(match[1])
    if not isinstance(info,dict) or type(info.get('readable')) is not bool or not isinstance(info.get('effects'),list):
        raise ValueError('Invalid RGB capabilities')
    if len(info['effects'])>16:raise ValueError('Too many RGB effects')
    seen=set()
    for effect in info['effects']:
        if not isinstance(effect,dict) or type(effect.get('id')) is not int or effect['id'] not in (0,1,3,4,10,11,21,22,23):
            raise ValueError('Invalid RGB effect')
        if effect['id'] in seen:raise ValueError('Duplicate RGB effect')
        seen.add(effect['id'])
        params=effect.get('parameters')
        if not isinstance(params,dict) or set(params)-{'color','period','intensity','saturation','direction','speed'}:
            raise ValueError('Invalid RGB parameters')
        for spec in params.values():
            if not isinstance(spec,dict) or set(spec)-{'minimum','maximum','default','choices'}:
                raise ValueError('Invalid RGB limits')
            for key,value in spec.items():
                values=value if key=='choices' and isinstance(value,list) else [value]
                if not values or len(values)>16 or any(type(v) is not int or not 0<=v<=16777215 for v in values):
                    raise ValueError('Invalid RGB parameter value')
            if spec.get('minimum',0)>spec.get('maximum',16777215):raise ValueError('Invalid RGB parameter range')
    return info


def parse_value(key,text):
    from logi_center.adapters.external.backend import solaar_settings
    import yaml
    setting=next((s for s in solaar_settings(text) if s['key']==key),None)
    info=rgb_capabilities(text) if key=='rgb_zone_1' else None
    if setting is None or setting['value'].startswith('?') and not (info and not info['readable']):
        raise Fault(FaultCode.CONNECTION,'solaar','Requested setting is absent or unreadable: '+key)
    raw=setting['value'].strip()
    if key=='rgb_control':
        if raw.lower() not in ('true','false','on','off','0','1','3'):raise ValueError('Invalid RGB control value')
        value=raw.lower() in ('true','on','1','3')
    elif key in ('rgb_zone_1','per-key-lighting'):
        # Solaar's map validator prints {1:0xffffff}, which needs YAML spacing.
        if key=='per-key-lighting':raw=re.sub(r'([,{]\s*\d+):(?=\S)',r'\1: ',raw)
        if len(raw)>2*1024*1024:raise ValueError('Setting exceeds size limit')
        try:value=yaml.load(raw,Loader=yaml.BaseLoader)  # tags never construct Python objects
        except yaml.YAMLError as error:raise ValueError('Invalid Solaar YAML') from error
        if info and not info['readable'] and (not isinstance(value,dict) or setting['value'].startswith('?')):value={}
        if not isinstance(value,dict):raise ValueError('Expected a setting map')
        if info:setting['native_rgb']=info
    elif key=='brightness_control':
        value=int(raw)
        if not 0<=value<=100:raise ValueError('Invalid brightness')
        metadata=re.search(r'^#   logi-center-brightness: (\{[^\n]+\})$',text,re.M)
        if metadata:
            info=json.loads(metadata[1])
            if not isinstance(info,dict) or set(info)-{'minimum','maximum','levels'}:
                raise ValueError('Invalid brightness metadata')
            minimum=info.get('minimum');maximum=info.get('maximum')
            if type(minimum) is not int or type(maximum) is not int or not 0<=minimum<=value<=maximum<=100:
                raise ValueError('Invalid brightness range')
            levels=info.get('levels')
            if levels is not None and (not isinstance(levels,list) or not 1<=len(levels)<=128
                    or any(type(v) is not int or not minimum<=v<=maximum for v in levels)
                    or levels!=sorted(set(levels))):
                raise ValueError('Invalid brightness levels')
            setting['native_brightness']=info
    else:value=raw
    return value,setting


def read_snapshot(target='G515 LS TKL',runner=None,cache=None):
    """Prefer real getters; write-only colors and host timers stay cache-sourced.

    A successful scoped CLI read verifies reachability even when RGB control is
    False. A failed/empty parse is never treated as an empty successful snapshot.
    """
    from logi_center.adapters.external.backend import run,saved_keyboard,keyboard_saved_settings
    runner=runner or run
    saved=deepcopy(saved_keyboard() if cache is None else cache)
    settings={s['key']:s for s in keyboard_saved_settings(saved) if s['key'] in READ_KEYS}
    sources={key:'local_saved_settings' for key in saved}
    errors=[];reachable=False;rgb_info=None
    for key in READ_KEYS:
        token=CURRENT_CANCEL.get()
        if token is not None and token.is_set():raise Fault(FaultCode.CANCELLED,'solaar','Operation cancelled')
        try:
            text=runner(['solaar','config',target,key],timeout=5)
            value,setting=parse_value(key,text)
            reachable=True
            if key=='rgb_zone_1' and setting.get('native_rgb'):
                rgb_info=setting['native_rgb'];settings[key]=setting
                if rgb_info['readable']:
                    saved[key]=value;sources[key]='device'
                elif key not in saved:
                    saved[key]=value;sources[key]='backend_cache' if value else 'unavailable'
                continue
            if key in LIVE_KEYS:
                saved[key]=value;sources[key]='device'
                if key=='rgb_control':setting['value']=str(value).lower();setting['choices']=['true','false']
                else:setting['value']=str(value)
                settings[key]=setting
            elif key not in saved:
                saved[key]=value
                sources[key]='unavailable' if key in ('rgb_idle_timeout','rgb_sleep_timeout') else 'backend_cache'
                if key in ('rgb_idle_timeout','rgb_sleep_timeout'):settings[key]=setting
            # No getter exists for per-key/zone colors or host-side timers.
            # CLI defaults must not replace previously saved user settings.
        except Fault as error:
            if error.code==FaultCode.CANCELLED:raise
            errors.append(error)
            if error.code in (FaultCode.DISCONNECTED,FaultCode.MISSING,FaultCode.PERMISSION):break
        except (ValueError,TypeError) as error:
            errors.append(Fault(FaultCode.CONFIG,'solaar','Could not parse setting '+key+': '+str(error)))
    if not settings and not isinstance(saved.get('rgb_zone_1'),dict):
        raise errors[0] if errors else Fault(FaultCode.CONNECTION,'solaar','No G515 settings returned')
    return dict(settings=list(settings.values()),saved=saved,sources=sources,target=target,
                reachable=reachable,errors=errors,rgb_capabilities=rgb_info)


def observed_capabilities(snapshot):
    """Publish scoped reads to inventory without inventing RGB effect readback."""
    from logi_center.core.capabilities import Capability
    from logi_center.core.services.operations import plan_for
    caps=[]
    for key in READ_KEYS:
        if key not in snapshot['saved']:continue
        source=snapshot['sources'].get(key,'unavailable')
        writable=key in LIVE_KEYS and source=='device' and snapshot['reachable']
        cap=Capability(key,'solaar',True,source!='unavailable',writable,writable,
                       snapshot['saved'][key],source)
        if writable:
            if key=='rgb_control':cap.choices=[False,True]
            else:
                info=next((s.get('native_brightness',{}) for s in snapshot['settings'] if s['key']==key),{})
                cap.choices=info.get('levels',[]);cap.minimum=info.get('minimum',0);cap.maximum=info.get('maximum',100)
            def plan(value,c=cap):
                if not c.writable:raise ValueError('Setting is not writable')
                if c.name=='rgb_control':
                    if type(value) is not bool:raise ValueError('Expected boolean LED control')
                elif type(value) is not int or not c.minimum<=value<=c.maximum or c.choices and value not in c.choices:
                    raise ValueError('Brightness is outside native limits')
                return plan_for(['solaar','config',snapshot['target'],c.name,str(value).lower()])
            cap.plan=plan
        elif key=='rgb_zone_1':cap.limitation='Effect writes use the dedicated lighting editor; cached state is not hardware confirmation.'
        caps.append(cap)
    return caps
