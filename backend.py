"""Adapters use argument vectors, bounded execution and explicit user writes."""
import json, os, re, subprocess, sys

def run(args, timeout=20, cancel=None):
    from execution import command,Fault,FaultCode
    if len(args)>2 and args[:3]==['solaar','config','G515']:
        if keyboard_online() is not True:raise Fault(FaultCode.DISCONNECTED,'solaar','Keyboard is not responding')
        from pathlib import Path
        args=[sys.executable,str(Path(__file__).with_name('solaar_write.py')),*args[1:]]
    return command(args,timeout=timeout,cancel=cancel)

def mouse_list(text):
    return [(m[1],m[2].strip()) for m in re.finditer(r'^([^\s:]+):\s+(.+)$',text,re.M)]

def solaar_settings(text):
    result=[]; label=''; choices=None
    for line in text.splitlines():
        if line.startswith('#   possible values: one of ['):
            match=re.search(r'\[\s*(.*?)\s*\]',line)
            if match:choices=[x.strip() for x in match[1].split(',')]
        elif line.startswith('#   possible values: on/'):
            choices=['true','false']
        elif line.startswith('# ') and not line.startswith('#   '):
            if not label: label=line[2:]
        else:
            m=re.match(r'^([a-z][a-z0-9_-]*)\s*=\s*(.+)$',line)
            if m:
                result.append(dict(key=m[1],value=m[2],label=label or m[1],choices=choices))
                label='';choices=None
    return result

def audio_devices(kind):
    return [d for d in json.loads(run(['pactl','-f','json','list',kind])) if not d['name'].endswith('.monitor') and not d['name'].startswith('easyeffects_')]

def volume(d):
    vs=[x['value_percent'] for x in d.get('volume',{}).values()]
    return int(vs[0].rstrip('%')) if vs else 0

def wireless_batteries(root='/sys/class/power_supply'):
    """Read kernel battery data; coarse levels must not become invented percentages."""
    from pathlib import Path
    result=[]
    for directory in sorted(Path(root).glob('*')):
        try:
            fields={}
            for line in (directory/'uevent').read_text().splitlines():
                if '=' in line:
                    k,v=line.split('=',1);fields[k.removeprefix('POWER_SUPPLY_')]=v
            model=fields.get('MODEL_NAME','')
            if fields.get('SCOPE')!='Device' or 'logitech' not in fields.get('MANUFACTURER','').lower():continue
            capacity=fields.get('CAPACITY','')
            percent=int(capacity) if capacity.isdigit() and 0<=int(capacity)<=100 else None
            result.append({'model':model,'percent':percent,'level':fields.get('CAPACITY_LEVEL','Unknown'),
                           'online':fields.get('ONLINE','1')=='1','status':fields.get('STATUS','Unknown')})
        except OSError:continue
    return result

def battery_label(battery):
    if not battery:return 'Заряд недоступен','battery-missing-symbolic'
    if not battery['online']:return 'Не подключено или спит','battery-missing-symbolic'
    percent=battery['percent'];level=battery['level']
    if percent is not None:
        label=f'{percent}%'
        icon='battery-empty-symbolic' if percent<=10 else ('battery-low-symbolic' if percent<=30 else ('battery-good-symbolic' if percent<=70 else 'battery-full-symbolic'))
    else:
        label={'Full':'Высокий заряд','High':'Высокий заряд','Normal':'Средний заряд','Low':'Низкий заряд','Critical':'Пора заменить батарейку'}.get(level,'Заряд неизвестен')
        icon='battery-low-symbolic' if level in ['Low','Critical'] else 'battery-full-symbolic' if level in ['Full','High'] else 'battery-good-symbolic'
    if battery['status']=='Charging':label+=' · заряжается';icon='battery-good-charging-symbolic'
    elif battery['status']=='Full':label+=' · заряжено'
    return label,icon

def load_preferences(path=None):
    from pathlib import Path
    path=Path(path) if path else Path.home()/'.config/logi-center/preferences.json'
    try:
        value=json.loads(path.read_text())
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError):return {}

def save_preferences(value,path=None):
    from pathlib import Path
    path=Path(path) if path else Path.home()/'.config/logi-center/preferences.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2))
    temporary.replace(path)

def saved_keyboard(path=None):
    from pathlib import Path
    import yaml
    path=Path(path) if path else Path.home()/'.config/solaar/config.yaml'
    try:
        # BaseLoader reads plain strings/maps, without constructing tagged objects.
        devices=yaml.load(path.read_text(),Loader=yaml.BaseLoader)
        return next((d for d in devices if isinstance(d,dict) and 'G515' in d.get('_NAME','')), {})
    except (OSError,ValueError,yaml.YAMLError,TypeError):return {}

def import_preset(source,root=None):
    """Install a local EasyEffects JSON preset, without overwriting existing presets."""
    from pathlib import Path
    source=Path(source)
    if source.stat().st_size>2*1024*1024:raise ValueError('Файл слишком большой для пресета (больше 2 МБ).')
    data=json.loads(source.read_text(encoding='utf-8-sig'))
    if not isinstance(data,dict):raise ValueError('Нужен пресет EasyEffects в формате JSON.')
    kinds=[kind for kind in ['input','output'] if isinstance(data.get(kind),dict)]
    if not kinds:raise ValueError('Это не пресет EasyEffects: настройки микрофона или наушников не найдены.')
    root=Path(root) if root else Path.home()/'.config/easyeffects'
    name=source.stem.strip() or 'Импортированный эффект'
    # Pick a single unused name across both directions.
    original=name;number=2
    while any((root/kind/(name+'.json')).exists() for kind in kinds):
        name=f'{original} ({number})';number+=1
    for kind in kinds:
        folder=root/kind;folder.mkdir(parents=True,exist_ok=True)
        target=folder/(name+'.json')
        with target.open('x',encoding='utf-8') as stream:
            json.dump({kind:data[kind]},stream,ensure_ascii=False,indent=2)
    return name,kinds

def keyboard_online(root='/sys/class/hidraw', transport=None):
    """HID++ root ping only; never create a Device, enumerate settings or run RGB cleanup."""
    from pathlib import Path
    candidates=[]
    for node in Path(root).glob('*'):
        try:text=(node/'device/uevent').read_text()
        except OSError:continue
        if re.search(r'^HID_NAME=.*G515',text,re.M):candidates.append((node,text))
    if not candidates:return False
    if transport is None:
        from logitech_receiver import base
        transport=base
    unknown=False
    for node,text in candidates:
        handle=None
        try:
            handle=transport.open_path('/dev/'+node.name)
            physical=re.search(r'^HID_PHYS=(.*)$',text,re.M)
            slot=re.search(r':(\d+)$',physical[1]) if physical else None
            number=int(slot[1]) if slot else 0xff
            if transport.ping(handle,number,long_message=True):return True
        except Exception:unknown=True
        finally:
            if handle is not None:transport.close(handle)
    return None if unknown else False

def keyboard_saved_settings():
    """Build the supported UI from saved data, without opening the HID device."""
    saved=saved_keyboard()
    choices={'rgb_control':['true','false'],
             'rgb_idle_timeout':['Disabled','15 Seconds','30 Seconds','1 Minute','2 Minutes','5 Minutes'],
             'rgb_sleep_timeout':['Disabled','2 Minutes','5 Minutes','10 Minutes','15 Minutes','30 Minutes']}
    result=[]
    for key in ['rgb_control','brightness_control','rgb_idle_timeout','rgb_sleep_timeout','rgb_zone_1']:
        if key not in saved:continue
        value=saved[key]
        if key=='rgb_idle_timeout':value={'0':'Disabled','15':'15 Seconds','30':'30 Seconds','60':'1 Minute','120':'2 Minutes','300':'5 Minutes'}.get(value,value)
        if key=='rgb_sleep_timeout':value={'0':'Disabled','120':'2 Minutes','300':'5 Minutes','600':'10 Minutes','900':'15 Minutes','1800':'30 Minutes'}.get(value,value)
        result.append(dict(key=key,value=str(value),label=key,choices=choices.get(key)))
    return result

def parse_mouse_info(text):
    """Separate profiles so inactive DPI/buttons never leak into the active profile."""
    profiles=[]
    sections=list(re.finditer(r'^Profile (\d+):([^\n]*)\n',text,re.M))
    for index,match in enumerate(sections):
        body=text[match.end():sections[index+1].start() if index+1<len(sections) else len(text)]
        rate=re.search(r'Report Rate: (\d+)Hz',body)
        resolutions=[{'index':int(m[1]),'dpi':int(m[2]),'active':'(active)' in m[3],'disabled':'(disabled)' in m[3],'default':'(default)' in m[3]} for m in re.finditer(r'^\s+(\d+): (\d+)dpi([^\n]*)',body,re.M)]
        buttons=[]
        for m in re.finditer(r"Button: (\d+) is mapped to (?:(macro|key) )?(?:'([^']+)'|(none))",body):
            buttons.append({'index':int(m[1]),'action':m[3] or 'disabled','macro':m[2]=='macro','type':m[2] or ('disabled' if m[4] else 'mapping')})
        leds=[]
        for m in re.finditer(r'LED: (\d+), depth: (\w+), mode: (\w+)([^\n]*)',body):
            color=re.search(r'color: ([0-9a-fA-F]{6})',m[4]);duration=re.search(r'duration: (\d+)',m[4]);brightness=re.search(r'brightness: (\d+)',m[4])
            leds.append({'index':int(m[1]),'mode':m[3],'color':color[1] if color else None,'duration':int(duration[1]) if duration else None,'brightness':int(brightness[1]) if brightness else None})
        profiles.append({'index':int(match[1]),'active':'(active)' in match[2],'rate':int(rate[1]) if rate else None,'resolutions':resolutions,'buttons':buttons,'leds':leds})
    return {'profiles':profiles,'active':next((p['index'] for p in profiles if p['active']),None)}

def read_mouse(device,runner=None):
    runner=runner or run
    text=runner(['ratbagctl',device,'info'])
    data=parse_mouse_info(text);data['text']=text
    for key,command in [('dpis',['dpi','get-all']),('rates',['rate','get-all'])]:
        try:data[key]=[int(x) for x in runner(['ratbagctl',device,*command]).split() if x.isdigit()]
        except Exception:data[key]=[]
    active=next((p for p in data['profiles'] if p['index']==data['active']),None)
    data['button_types']={}
    if active and runner is run:
        try:
            from ratbag_dbus import button_types
            match=re.search(r'Model:\s*(\S+)',text)
            if match:data['button_types']=button_types(match[1],active['index'])
        except Exception:pass  # Unknown capability must not be presented as supported.
    data['led_modes']={}
    if active:
        for led in active['leds']:
            try:
                values=runner(['ratbagctl',device,'profile',str(active['index']),'led',str(led['index']),'capabilities'])
                data['led_modes'][led['index']]=[x for x in re.findall(r'\b(?:off|on|cycle|breathing)\b',values)]
            except Exception:data['led_modes'][led['index']]=[]
    return data
