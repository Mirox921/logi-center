"""Scoped G515 settings reads. No full Solaar enumeration or write recovery."""
import json,re
from copy import deepcopy
from logi_center.core.services.execution import Fault,FaultCode,CURRENT_CANCEL

READ_KEYS=('rgb_control','brightness_control','rgb_zone_1','per-key-lighting',
           'rgb_idle_timeout','rgb_sleep_timeout')
LIVE_KEYS={'rgb_control','brightness_control'}


def parse_value(key,text):
    from logi_center.adapters.external.backend import solaar_settings
    import yaml
    setting=next((s for s in solaar_settings(text) if s['key']==key),None)
    if setting is None or setting['value'].startswith('?'):
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
        if not isinstance(value,dict):raise ValueError('Expected a setting map')
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
    errors=[];reachable=False
    for key in READ_KEYS:
        token=CURRENT_CANCEL.get()
        if token is not None and token.is_set():raise Fault(FaultCode.CANCELLED,'solaar','Operation cancelled')
        try:
            text=runner(['solaar','config',target,key],timeout=5)
            value,setting=parse_value(key,text)
            reachable=True
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
                reachable=reachable,errors=errors)
