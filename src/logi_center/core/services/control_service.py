"""Toolkit-free editor descriptors over existing capability plans and services."""
from dataclasses import dataclass, field
from copy import deepcopy
import math, re
from logi_center.core.services.operations import plan_for, same
from logi_center.core.services.execution import Fault, FaultCode
from logi_center.i18n import tr as _, canonical_text

NAMES={'dpi_x':'DPI по горизонтали','dpi_y':'DPI по вертикали','backend_features':'Возможности, сообщённые backend','dpi':'Чувствительность DPI','polling_rate':'Частота опроса, Гц','profiles':'Встроенный профиль','buttons':'Кнопки','macros':'Макросы','lighting':'Подсветка','standard_input':'Стандартный ввод','sidetone':'Слышимость своего голоса','battery_status':'Заряд аккумулятора','volume':'Громкость','mute':'Без звука','lighting_mode':'Эффект подсветки','brightness':'Яркость','zones':'Зоны подсветки','stage':'Ступень DPI','dpi_stages':'Ступени DPI','debounce':'Задержка устранения дребезга, мс','sleep':'Таймер сна (единицы протокола)','motion_sync':'Синхронизация сенсора','ripple':'Подавление дрожания','angle_snap':'Выпрямление линий'}

NAMES.update({'firmware_version':'Версия прошивки','usb_release':'Версия USB-устройства','keyboard_layout':'Раскладка клавиатуры','actuation':'Точка срабатывания','rapid_trigger':'Rapid Trigger','rt_press':'RT при нажатии','rt_release':'RT при отпускании','press_dead_zone':'Верхняя мёртвая зона','release_dead_zone':'Нижняя мёртвая зона','key_details':'Параметры магнитных переключателей','lighting_palette':'Палитра подсветки','lighting_speed':'Скорость эффекта','socd':'SOCD / Snap Tap','dks':'Динамическое нажатие (DKS)','mod_tap':'Mod Tap','toggle_key':'Toggle Key','key_remap':'Переназначение клавиш','layers':'Слои клавиатуры'})
NAMES.update({'lighting_direction':'Направление эффекта','win_lock':'Блокировка Win','stability_mode':'Защита от случайных нажатий',
              'key_debounce':'Оптимизация дребезга','adaptive_calibration':'Адаптивная калибровка (бета)','keyboard_mode':'Режим клавиатуры'})

GROUPS={'pointer':'Чувствительность и скорость','buttons':'Кнопки и макросы','keys':'Клавиши',
        'lighting':'Подсветка','profiles':'Профили','advanced':'Дополнительно',
        'indicators':'Индикаторы мыши','dock':'Док-станция'}
KEY_LABELS={'actuation':'Точка срабатывания, мм','rapid_trigger':'Режим Rapid Trigger','rt_press':'RT при нажатии, мм','rt_release':'RT при отпускании, мм','press_dead_zone':'Верхняя мёртвая зона, мм','release_dead_zone':'Нижняя мёртвая зона, мм'}


def binding(device):
    """Private identity, excluding telemetry that can change during editing."""
    return (device.id,device.physical,device.vid,device.pid,
            tuple(sorted((k,tuple(v)) for k,v in device.targets.items())))


def group_for(name):
    if name in ('dpi','dpi_x','dpi_y','stage','polling_rate','dpi_stages'):return 'pointer'
    if name=='profiles':return 'profiles'
    if name.startswith('lighting') or name in ('brightness','rgb_control','brightness_control','rgb_zone_1','rgb_idle_timeout','rgb_sleep_timeout'):return 'lighting'
    return 'advanced'


def is_k7_ultra(device):
    """Identify known K7 receiver/wired identities without guessing from names."""
    return (device.kind=='mouse' and device.vid=='3837' and device.pid in ('1001','4150')
            and 'mchose' in device.backends and 'K7 Ultra' in device.name)


# Nominal DPI-indicator colors from the K7 Ultra manual. These are UI swatches,
# not an optical LED readback or a configurable device color.
K7_DPI_INDICATORS=(('Красный','#d85b55'),('Синий','#548bd6'),
                   ('Зелёный','#59ad78'),('Жёлтый','#d8b547'),
                   ('Бирюзовый','#50b8c4'),('Фиолетовый','#a77ad1'))


def k7_dpi_indicator(stage):
    """Return the manual's color name and a legible swatch for a zero-based stage."""
    return K7_DPI_INDICATORS[stage] if type(stage) is int and 0<=stage<len(K7_DPI_INDICATORS) else None


def display(value):
    if value is None:return _('Нет данных')
    if type(value) is bool:return _('Включено') if value else _('Выключено')
    if isinstance(value,list):return ', '.join(str(v) for v in value)
    return str(value)


def choice_caption(value):
    return _({'on':'Статичный цвет','off':'Выключено','breathing':'Дыхание','cycle':'Цикл цветов',
              'Static':'Статичный цвет','Breathing':'Дыхание','Wave':'Волна','Off':'Выключено',
              'Single color':'Один цвет','Random colors':'Случайные цвета','Custom':'Поклавишные цвета',
              'Vertical wave':'Вертикальная волна','Center spread':'Из центра','Star twinkle':'Мерцание звёзд',
              'Color cycle':'Цикл цветов','Disco':'Диско','Linear gradient':'Линейный градиент',
              'Bottom up':'Снизу вверх','Reciprocal rebound':'Взаимный отскок','Center spin':'Вращение из центра',
              'Diagonal flow':'Диагональный поток','Laser rain':'Лазерный дождь','Dot twinkle':'Мерцание точек',
              'Fireworks':'Фейерверк','Triangle bounce':'Треугольный отскок','Solid ripple':'Постоянная рябь',
              'Key ripple':'Рябь от клавиши','Key trail':'След клавиши','Key firework':'Фейерверк клавиши','Key beam':'Луч клавиши',
              'true':'Включено','false':'Выключено'}.get(value,value)) if isinstance(value,str) else display(value)


@dataclass
class Control:
    id:str
    label:str
    group:str
    observed:object
    draft_key:str
    backend:str
    kind:str='readonly'
    choices:list=field(default_factory=list)
    choice_labels:list=field(default_factory=list)
    minimum:float=0
    maximum:float=100
    step:float=1
    source:str='unavailable'
    writable:bool=False
    factory:object=None
    capability:str=''
    encode:object=lambda v:v
    decode:object=lambda v:v
    note:str=''
    profile:object=None
    key_index:str=''
    batch_factory:object=None

    def validate(self,value):
        if not self.writable or self.factory is None:raise ValueError('Setting is not writable')
        if self.kind=='choice':
            if value not in self.choices or type(value) is bool and not any(type(c) is bool for c in self.choices):raise ValueError('Value is outside capability choices')
            value=deepcopy(next(c for c in self.choices if c==value))
        if self.kind=='number':
            if type(value) not in (int,float) or not math.isfinite(value) or not self.minimum<=value<=self.maximum:raise ValueError('Value is outside capability range')
            ticks=(value-self.minimum)/self.step
            if abs(ticks-round(ticks))>1e-5:raise ValueError('Value is outside capability step')
            if self.step>=1 and float(self.step).is_integer() and float(value).is_integer():value=int(value)
        if self.kind=='color' and (not isinstance(value,list) or len(value)!=3 or any(type(v) is not int or not 0<=v<=255 for v in value)):raise ValueError('Expected RGB channels')
        if self.kind=='bool' and type(value) is not bool:raise ValueError('Expected a boolean')
        if self.kind=='binding':
            from logi_center.adapters.mchose.k7_settings import validate_action
            validate_action(value)
        if self.kind=='acebinding':
            from logi_center.adapters.mchose.ace68_bindings import validate_action
            validate_action(value)
        if self.kind=='ewebinding':
            from logi_center.protocols.eweadn_protocol import validate_action
            validate_action(value)
        return value

    def plans(self,value):
        result=self.factory(self.validate(value))
        return result if isinstance(result,list) else [result]


def capability_controls(device):
    result=[]
    profile=next((c.value for c in device.capabilities if c.backend=='mchose' and c.name=='profiles' and c.readable),None)
    stage=next((c.value for c in device.capabilities if c.backend=='mchose' and c.name=='stage' and c.readable),None)
    hidden={'standard_input','battery_present','battery_status','charging','identity','raw','key_details','firmware_version','usb_release','keyboard_layout','zones','backend_features','buttons','macros'}
    for cap in device.capabilities:
        if cap.backend=='eweadn':
            if cap.name in ('dpi_config','sensor_config','button_bindings'):
                result+=eweadn_controls(device,cap)
            continue
        if cap.backend=='mchose-ace68' and cap.name in ('key_remap','advanced_keys','key_lighting') and isinstance(cap.value,dict):continue
        if is_k7_ultra(device) and cap.backend=='mchose':
            native={c.name for c in device.capabilities if c.backend=='mchose' and isinstance(c.value,dict)}
            if cap.name in ('dpi_config','sensor_config','button_bindings'):
                result+=k7_controls(device,cap,profile);continue
            if ('dpi_config' in native and cap.name in ('dpi','stage','dpi_stages') or
                    'sensor_config' in native and cap.name in ('motion_sync','ripple','angle_snap')):continue
        if cap.backend=='mchose' and cap.name=='dock_lighting' and isinstance(cap.value,dict):
            result+=dock_controls(device,cap);continue
        if device.kind=='audio' and cap.backend=='pactl':continue  # AudioEndpoint owns logical server routes.
        if cap.backend=='ratbagctl' or cap.name in hidden or isinstance(cap.value,dict):continue
        if not cap.readable and not cap.writable:continue
        kind='choice' if cap.choices else 'color' if cap.name=='lighting' or cap.name.startswith('lighting_zone_') else 'bool' if type(cap.value) is bool else 'number' if cap.minimum is not None and cap.maximum is not None else 'readonly'
        # Explicit simulation metadata is defined by the fixture, never a real model guess.
        if device.simulated and cap.writable and kind=='readonly':
            kind='number' if type(cap.value) in (int,float) else 'color' if cap.name=='lighting' else 'readonly'
        value=cap.value
        if kind=='color' and isinstance(value,str) and re.fullmatch('[0-9a-fA-F]{6}',value):value=[int(value[i:i+2],16) for i in (0,2,4)]
        field=Control(cap.backend+':'+cap.name,NAMES.get(cap.name,cap.name.replace('_',' ')),group_for(cap.name),value,
            'device:'+device.id+':'+cap.name+('@'+cap.backend if len({c.backend for c in device.capabilities if c.name==cap.name and c.writable})>1 else ''),cap.backend,kind,deepcopy(cap.choices),source=cap.source,
            minimum=cap.minimum if cap.minimum is not None else 0,maximum=cap.maximum if cap.maximum is not None else 50000,
            step=cap.step,writable=cap.writable and (cap.plan is not None or device.simulated) and kind!='readonly',
            factory=cap.plan,capability=cap.name,note=cap.limitation)
        if cap.backend=='mchose' and cap.name!='profiles' and type(profile) is int:
            field.draft_key+=':profile:'+str(profile)
            if cap.name=='dpi' and type(stage) is int:field.draft_key+=':stage:'+str(stage)
        if is_k7_ultra(device) and cap.backend=='mchose' and cap.name in ('motion_sync','ripple','angle_snap'):
            field.note='Запись флагов сенсора для K7 Ultra не проверена; настройка доступна только для чтения.'
        if is_k7_ultra(device) and cap.backend=='mchose' and cap.name=='sleep':field.label='Таймер сна, мин (0 — никогда)'
        if is_k7_ultra(device) and cap.backend=='mchose' and cap.name=='debounce':field.maximum=20
        if is_k7_ultra(device) and cap.backend=='mchose' and cap.writable:field.note=''
        if cap.backend=='mchose-ace68':
            ace_profile=next((c.value for c in device.capabilities if c.backend==cap.backend and c.name=='profiles'),None)
            field.profile=ace_profile
            if cap.name!='profiles' and type(ace_profile) is int:field.draft_key+=':profile:'+str(ace_profile)
            if cap.name in ('polling_rate','win_lock','stability_mode','key_debounce','adaptive_calibration','keyboard_mode'):field.group='performance'
            if cap.writable:field.note=''
            if cap.name=='adaptive_calibration':field.note='Флаг включает автоматическую калибровку в прошивке. Снимок настроек не сохраняет измеренную калибровку сенсоров.'
            if cap.name=='keyboard_mode':field.note='Режим Mac отключает блокировку Win; остальные настройки сохраняются.'
            if cap.name=='lighting_direction':field.choice_labels=['Прямое','Обратное']
        if device.simulated and field.writable:field.factory=lambda value:None
        result.append(field)
    return result


def k7_controls(device,cap,profile):
    from logi_center.adapters.mchose.k7_settings import BUTTONS,validate_action
    specs=[]
    if cap.name=='dpi_config':
        specs=[('count','Количество ступеней','choice',1,6,list(range(1,7)),[]),
               ('active','Активная ступень DPI','choice',0,5,list(range(6)),[])]
        specs += [(axis+str(i),'DPI '+axis.upper(),'number',200,42000,[],[]) for i in range(6) for axis in ('x','y')]
        group='pointer'
    elif cap.name=='button_bindings':
        specs=[(str(i),label,'binding',0,0,[],[]) for i,label,x,y in BUTTONS]
        group='buttons'
    else:
        specs=[('performance_mode','Режим сенсора','choice',0,2,[0,1,2],['Производительный','Игровой','Экстремальный']),
               ('lod','Высота отрыва, мм','choice',0,2,[0,1,2],['0.7','1','2']),
               ('rotation','Угол сенсора, °','number',-30,30,[],[]),
               ('ripple','Подавление дрожания','bool',0,1,[],[]),
               ('angle_snap','Выпрямление линий','bool',0,1,[],[]),
               ('motion_sync','Синхронизация сенсора','bool',0,1,[],[])]
        group='advanced'
    result=[]
    for key,label,kind,low,high,choices,labels in specs:
        value=cap.value.get(key)
        writable=cap.writable and cap.plan is not None and value is not None and (not choices or value in choices)
        if kind=='number':writable=writable and type(value) in (int,float) and low<=value<=high
        if kind=='binding':
            try:validate_action(value)
            except ValueError:writable=False
        result.append(Control('mchose:'+cap.name+':'+key,label,group,deepcopy(value),
            'device:'+device.id+':'+cap.name+':profile:'+str(profile)+':'+key,'mchose',kind,choices,labels,
            minimum=low,maximum=high,step=50 if cap.name=='dpi_config' and kind=='number' else 1,
            source=cap.source,writable=writable,factory=lambda v,k=key,p=cap.plan:p({k:v}),
            capability=cap.name,key_index=key,batch_factory=cap.plan,profile=profile,
            note='' if writable else 'Получено неизвестное или неподдерживаемое значение; запись недоступна.'))
    return result


def dock_controls(device,cap):
    """Presentation descriptors over one native dock-record plan."""
    specs=[('enabled','Подсветка','bool',[],[]),
           ('mode','Эффект подсветки','choice',['static','breathing','battery','flash','cycle','stars','wave'],
            ['Статичный цвет','Дыхание','Уровень заряда','Вспышки','Цикл цветов','Звёзды','Волны']),
           ('brightness','Яркость','number',[],[]),('color','Цвет','color',[],[]),
           ('duration','Длительность','choice',[0,1,2],['Короткая','Средняя','Долгая']),
           ('direction','Направление','choice',[0,1],['По часовой стрелке','Против часовой стрелки'])]
    return [Control('mchose:dock:'+key,label,'dock',deepcopy(cap.value.get(key)),
        'device:'+device.id+':dock:'+key,'mchose',kind,choices,labels,
        minimum=0,maximum=100,step=1,source=cap.source,writable=cap.writable and cap.plan is not None,
        factory=lambda value,k=key,plan=cap.plan:plan({k:value}),capability='dock_lighting',key_index=key,
        batch_factory=cap.plan) for key,label,kind,choices,labels in specs]


def mouse_actions():
    return {'Левый щелчок':['button','1'],'Правый щелчок':['button','2'],'Нажатие колёсика':['button','3'],
        'Назад':['button','4'],'Вперёд':['button','5'],'Переключать чувствительность':['special','resolution-cycle-up'],
        'Уменьшить DPI':['special','resolution-down'],'Увеличить DPI':['special','resolution-up'],
        'Снижение DPI при удержании':['special','resolution-alternate'],'Следующий профиль':['special','profile-cycle-up'],
        'G-Shift':['special','second-mode'],'Наклон колёсика вправо':['special','wheel-right'],'Наклон колёсика влево':['special','wheel-left'],
        'Копировать':['macro','+KEY_LEFTCTRL','KEY_C','-KEY_LEFTCTRL'],'Вставить':['macro','+KEY_LEFTCTRL','KEY_V','-KEY_LEFTCTRL'],
        'Вырезать':['macro','+KEY_LEFTCTRL','KEY_X','-KEY_LEFTCTRL'],'Отменить':['macro','+KEY_LEFTCTRL','KEY_Z','-KEY_LEFTCTRL'],
        'Выделить всё':['macro','+KEY_LEFTCTRL','KEY_A','-KEY_LEFTCTRL'],
        **{'Клавиша F'+str(i):['key','KEY_F'+str(i)] for i in range(1,13)},'Отключить кнопку':['disabled']}


def ratbag_controls(device,data):
    targets=device.targets.get('ratbagctl',[])
    if len(targets)!=1:return [],[]
    target=targets[0];active=next((p for p in data['profiles'] if p['index']==data['active']),None)
    if active is None:return [],[]
    prefix=['ratbagctl',target,'profile',str(active['index'])]
    scope='mouse:'+target+':profile:'+str(active['index']);result=[];buttons=[]
    def choice(ident,label,group,value,values,command,key=None,labels=None):
        field=Control('ratbagctl:'+ident,label,group,value,key or scope+'/'+canonical_text(label),'ratbagctl','choice',values,labels or [],
            source='backend_cache',writable=True,factory=lambda v,c=command:plan_for([*c,str(v)]),profile=active['index'],encode=str,decode=lambda v:type(value)(v))
        result.append(field);return field
    if len(data['profiles'])>1:
        f=choice('profiles','Встроенный профиль','profiles',active['index'],[p['index'] for p in data['profiles']],['ratbagctl',target,'profile','active','set'],key='mouse:'+target+'/'+canonical_text('Встроенный профиль'),labels=['Профиль '+str(p['index']+1) for p in data['profiles']])
        f.encode=lambda v:canonical_text('Профиль '+str(v+1));f.decode=lambda v:int(str(v).rsplit(' ',1)[-1])-1
    resolution=next((r for r in active['resolutions'] if r['active']),None)
    if resolution and data.get('dpis'):
        choice('dpi','Чувствительность DPI','pointer',resolution['dpi'],sorted(set(data['dpis']+[resolution['dpi']])),[*prefix,'resolution',str(resolution['index']),'dpi','set'])
    if active.get('rate') and data.get('rates'):choice('polling_rate','Частота опроса, Гц','pointer',active['rate'],data['rates'],[*prefix,'rate','set'])
    enabled=[r for r in active['resolutions'] if not r['disabled']]
    if resolution and len(enabled)>1:
        labels=['Уровень '+str(r['index']+1)+' · '+str(r['dpi'])+' DPI' for r in enabled];values=[r['index'] for r in enabled]
        f=choice('stage','Активный уровень чувствительности','pointer',resolution['index'],values,[*prefix,'resolution','active','set'],labels=labels)
        f.encode=lambda v:canonical_text(labels[values.index(v)]);f.decode=lambda v:values[[canonical_text(label) for label in labels].index(v)]
    from logi_center.core.devices.mouse_models import action_allowed
    from logi_center.core.services.operations import read_action
    for button in active['buttons']:
        index=button['index'];types=data.get('button_types',{}).get(index,[])
        current=read_action(('macro ' if button['macro'] else '')+button['action'])
        actions=[{'label':label,'value':value} for label,value in mouse_actions().items() if action_allowed(value,types)]
        buttons.append({'index':index,'action':current,'actions':actions,'macroSupported':4 in types,'types':types})
    rgb_owner=any(c.backend=='openrgb' and c.writable and c.name in ('lighting','lighting_mode') for c in device.capabilities)
    # Only the wired G502 HERO has the documented onboard effect timing used
    # below. A name alone is insufficient evidence for device-specific values.
    g502_hero=bool(re.search(r'^\s*Model:\s*usb:046d:c08b(?::|\s|$)',data.get('text',''),re.M))
    for led in ([] if rgb_owner else active['leds']):
        index=led['index'];modes=data.get('led_modes',{}).get(index,[])
        if not modes:continue
        command=[*prefix,'led',str(index),'set'];key=scope+'/led:'+str(index)
        mode_field=choice('led:'+str(index)+':mode','Зона подсветки '+str(index+1),'lighting',led['mode'],modes,[*command,'mode'],key=key+':mode')
        if g502_hero:
            mode_field.label='LED '+str(index+1)+' · ratbagd'
            mode_field.note='Аппаратный режим · физическое подтверждение требуется' if index==0 else 'Дополнительный слот ratbagd · назначение не подтверждено'
        if led.get('depth')=='rgb':
            color=led.get('color');rgb=[int(color[i:i+2],16) for i in (0,2,4)] if isinstance(color,str) and re.fullmatch('[0-9a-fA-F]{6}',color) else None
            result.append(Control('ratbagctl:led:'+str(index)+':color','Цвет'+(' · LED '+str(index+1) if g502_hero else ''),'lighting',rgb,key+':color','ratbagctl','color',source='backend_cache',writable=True,
                factory=lambda v,c=command:plan_for([*c,'color',''.join(f'{x:02x}' for x in v)]),profile=active['index'],encode=lambda v:None if v is None else 'rgb('+','.join(str(x) for x in v)+')',decode=lambda v:None if v is None else rgb_value(v)))
        if g502_hero:
            for effect in ('cycle','breathing'):
                if effect not in modes:continue
                for parameter,label,low,high,step in (('duration','Период эффекта, мс',1000,10000,100),
                                                       ('brightness','Яркость эффекта',1,255,1)):
                    observed=led.get(parameter) if led['mode']==effect else None
                    result.append(Control('ratbagctl:led:'+str(index)+':'+parameter+':'+effect,label+' · LED '+str(index+1),'lighting',observed,
                        key+':'+effect+':'+parameter,'ratbagctl','number',minimum=low,maximum=high,step=step,
                        source='backend_cache' if observed is not None else 'unavailable',writable=True,
                        factory=lambda v,c=command,p=parameter:plan_for([*c,p,str(v)]),profile=active['index'],
                        note='Меньший период — быстрее' if parameter=='duration' else 'Уровень, сообщаемый ratbagd'))
    return result,buttons


def rgb_value(value):
    if isinstance(value,list):return value
    if isinstance(value,str) and re.fullmatch('#?[0-9a-fA-F]{6}',value):
        value=value.removeprefix('#');return [int(value[i:i+2],16) for i in (0,2,4)]
    if isinstance(value,str) and value.startswith('rgb'):
        values=re.findall(r'[\d.]+',value);return [round(float(v)) for v in values[:3]]
    raise ValueError('Invalid color draft')


def keyboard_keys():
    from logi_center.adapters.mchose.ace68_adapter import LAYOUT
    from logi_center.protocols.ace68_protocol import KEY_INDICES
    widths=[{'Backspace':2},{'Tab':1.5,'\\':1.5},{'Caps':1.75,'Enter':2.25},{'LShift':2.25,'RShift':1.75},{'LCtrl':1.25,'Super':1.25,'LAlt':1.25,'Space':6.25}]
    rows=[];ids=iter(KEY_INDICES)
    for row,labels in enumerate(LAYOUT):
        x=0
        for label in labels:
            width=widths[row].get(label,1);rows.append({'id':str(next(ids)),'label':label,'x':x,'y':row,'w':width});x+=width
    return rows


def key_controls(device,index):
    caps={c.name:c for c in device.capabilities if c.backend=='mchose-ace68'}
    if not all(name in caps for name in (*KEY_LABELS,'profiles','key_details')):return []
    profile=caps['profiles'].value;details=caps['key_details'].value.get(index)
    if details is None:return []
    result=[]
    for name,label in KEY_LABELS.items():
        cap=caps[name];base=details['press_base' if name=='rt_press' else 'release_base'] if name in ('rt_press','rt_release') else 100
        low,high=(.1,3.3) if name=='actuation' else (0,.5) if name.endswith('dead_zone') else (2/base,min(3.3,500/base))
        result.append(Control('key:'+index+':'+name,label,'keys',cap.value[index],f'ace68:{device.id}:profile:{profile}:key:{index}:{name}',cap.backend,
            'choice' if name=='rapid_trigger' else 'number',choices=[0,1,2] if name=='rapid_trigger' else [],choice_labels=['Выключено','Rapid Trigger','Непрерывный RT'] if name=='rapid_trigger' else [],
            minimum=low,maximum=high,step=1/base,source=cap.source,writable=cap.writable,
            factory=lambda v,c=cap,k=index:c.plan({k:v}),capability=name,profile=profile,key_index=index))
    return result


def ace_binding_controls(device):
    from logi_center.adapters.mchose.ace68_bindings import validate_action
    cap=next((c for c in device.capabilities if c.backend=='mchose-ace68' and c.name=='key_remap' and isinstance(c.value,dict)),None)
    if cap is None:return []
    profile=next(c.value for c in device.capabilities if c.backend=='mchose-ace68' and c.name=='profiles')
    result=[]
    for slot,value in cap.value.items():
        writable=cap.writable and cap.plan is not None
        try:validate_action(value)
        except ValueError:writable=False
        result.append(Control('ace:binding:'+slot,'Назначение клавиши','key_assignments',deepcopy(value),
            f'ace68:{device.id}:profile:{profile}:binding:{slot}','mchose-ace68','acebinding',source=cap.source,
            writable=writable,factory=lambda v,k=slot,p=cap.plan:p({k:v}),capability='key_remap',profile=profile,
            key_index=slot,batch_factory=cap.plan))
    return result


def g515_controls(settings,saved,identity='G515',target='G515',sources=None):
    """Existing G515 saved-setting UI, with honest local provenance."""
    result=[]
    sources=sources or {}
    labels={'rgb_control':'Управление подсветкой из приложения','brightness_control':'Яркость подсветки',
            'rgb_idle_timeout':'Приглушать подсветку при бездействии','rgb_sleep_timeout':'Выключать подсветку при бездействии'}
    captions={'true':'Включено','false':'Выключено','Disabled':'Никогда','15 Seconds':'Через 15 секунд','30 Seconds':'Через 30 секунд','1 Minute':'Через минуту','2 Minutes':'Через 2 минуты','5 Minutes':'Через 5 минут','10 Minutes':'Через 10 минут','15 Minutes':'Через 15 минут','30 Minutes':'Через 30 минут'}
    for setting in settings:
        key=setting['key']
        if key not in labels:continue
        if key=='brightness_control':
            try:value=int(setting['value'])
            except (ValueError,TypeError):continue
            if not 0<=value<=100:continue
            result.append(Control('g515:'+key,labels[key],'lighting',value,'keyboard:G515/'+canonical_text(labels[key]),
                'solaar','number',minimum=0,maximum=100,step=1,source=sources.get(key,'local_saved_settings'),
                writable=True,factory=lambda v:plan_for(['solaar','config',target,'brightness_control',str(v)]),
                encode=lambda v:str(v)+'%',decode=lambda v:int(str(v).rstrip('%'))))
            continue
        values=setting.get('choices') or (['0','12','25','50','100'] if key=='brightness_control' else [])
        value=setting['value'].lower() if values==['true','false'] else setting['value']
        if not values:continue
        text=['Выключена' if c=='0' else c+'%' for c in values] if key=='brightness_control' else [captions.get(c,c) for c in values]
        group='keyboard_settings' if key in ('rgb_control','rgb_idle_timeout','rgb_sleep_timeout') else 'lighting'
        result.append(Control('g515:'+key,labels[key],group,value,'keyboard:G515/'+canonical_text(labels[key]),'solaar','choice',values,text,
            source=sources.get(key,'local_saved_settings'),writable=True,factory=lambda v,k=key:plan_for(['solaar','config',target,k,v]),
            encode=lambda v,choices=values,displayed=text:canonical_text(displayed[choices.index(v)])))
        result[-1].decode=lambda v,choices=values,displayed=text:next((c for c,t in zip(choices,displayed) if canonical_text(t)==v),v)
    rgb=saved.get('rgb_zone_1')
    if isinstance(rgb,dict):
        try:effect=int(rgb.get('ID',1));color=int(str(rgb.get('color','0xffffff')),0)
        except (ValueError,TypeError):return result
        result.append(Control('g515:effect','Режим подсветки','lighting',effect,'keyboard:G515/effect','solaar','choice',[1,10,21,0],['Статичный цвет','Дыхание','Цикл цветов','Выключено'],source=sources.get('rgb_zone_1','local_saved_settings'),writable=True,factory=lambda v:None))
        result.append(Control('g515:color','Цвет','lighting',[(color>>shift)&255 for shift in (16,8,0)],'keyboard:G515/color','solaar','color',source=sources.get('rgb_zone_1','local_saved_settings'),writable=True,factory=lambda v:None,encode=lambda v:'rgb('+','.join(str(x) for x in v)+')',decode=rgb_value))
        for key,label,low,high,default in [('period','Период эффекта, мс',1000,20000,3000),('intensity','Интенсивность эффекта, %',0,100,100)]:
            try:value=int(rgb[key])
            except (ValueError,TypeError,KeyError):value=None
            valid=value is not None and low<=value<=high
            # Static/Off omit timing in Solaar's saved record. Keep animation
            # controls available, explicitly labeling their initial values.
            for mode in (10,21):
                known=valid and effect==mode
                result.append(Control(f'g515:{key}:{mode}',label,'lighting',value if known else default,
                    f'keyboard:{identity}/effect:{mode}/{key}','solaar','number',minimum=low,maximum=high,step=1,
                    source=sources.get('rgb_zone_1','local_saved_settings') if known else 'unavailable',writable=True,factory=lambda v:None,
                    note='' if known else 'Начальное значение эффекта; аппаратное считывание недоступно.'))
        from logi_center.adapters.logitech.g515_layout import saved_colors
        for key,value in saved_colors(saved).items():
            result.append(Control('g515:key:'+key,'Цвет выбранных клавиш','freestyle',value,
                f'keyboard:{identity}/key-color:{key}','solaar','color',source=sources.get('per-key-lighting','local_saved_settings'),writable=True,
                factory=lambda v,k=key:plan_for(['solaar','config',target,'per-key-lighting',k,str((v[0]<<16)|(v[1]<<8)|v[2])]),
                key_index=key))
    return result


def g515_lighting_plans(effect,color,period=3000,intensity=100,target='G515'):
    if type(effect) is not int or effect not in (1,10,21,0) or len(color)!=3 or any(type(v) is not int or not 0<=v<=255 for v in color):raise ValueError('Invalid lighting setting')
    if type(period) is not int or not 1000<=period<=20000 or type(intensity) is not int or not 0<=intensity<=100:raise ValueError('Invalid animation parameters')
    # Static and Off do not accept animation parameters. Solaar validates the
    # effect against the actual zone's capability list before any effect write.
    params=['ID: '+str(effect)]
    if effect in (1,10):params.append('color: 0x'+''.join(f'{v:02x}' for v in color))
    if effect in (10,21):params.extend(['period: '+str(period),'intensity: '+str(intensity)])
    value='!LEDEffectSetting {'+', '.join(params)+'}'
    return [plan_for(['solaar','config',target,'rgb_control','true']),plan_for(['solaar','config',target,'rgb_zone_1',value])]


def operation_message(result):
    from logi_center.core.services.operations import State
    texts={State.LOCAL:'Локальная настройка сохранена',State.UNSUPPORTED:'Эта настройка не поддерживается',State.PERMISSION:'Нет доступа к устройству',State.CONFIRMED:'Изменение применено',State.SENT:'Изменение отправлено, но устройство его не подтвердило',State.MISMATCH:'Устройство вернуло другое значение',State.ERROR:'Не удалось применить изменение',State.DISCONNECTED:'Устройство отключено',State.CANCELLED:'Операция отменена'}
    text=_('Изменение подтверждено аудиосистемой') if result.state==State.CONFIRMED and result.source=='audio_server' else _(texts[result.state])
    if result.source=='backend_cache' and result.state==State.SENT:text+=' · '+_('Подтверждение устройства недоступно')
    if result.state==State.MISMATCH:text+='\n'+_('Запрошено: ')+display(result.requested)[:120]+' · '+_('Получено: ')+display(result.actual)[:120]
    if result.fault:text+='\n'+fault_message(result.fault)
    return text


def fault_message(error):
    """Localized recovery text for normal editors; raw detail stays in diagnostics."""
    from logi_center.core.services.diagnostics import fault_for,REMEDIES
    fault=fault_for(error)
    if fault.component=='mchose' and fault.message.startswith('Empty identity reply'):
        return _('Мышь не ответила на запрос состояния. Разбуди её движением, проверь подключение и нажми «Прочитать настройки».')
    if fault.component=='mchose' and fault.message.startswith('Profile or DPI stage changed'):
        return _('Профиль или ступень DPI изменились. Прочитай настройки заново; черновик сохранён.')
    if fault.component=='mchose' and fault.message.startswith('Dock lighting changed'):
        return _('Подсветка дока изменилась. Прочитай настройки заново; черновик сохранён.')
    if fault.component=='mchose' and fault.message.startswith('K7 configuration changed'):
        return _('Конфигурация K7 изменилась. Прочитай настройки заново; черновик сохранён.')
    title,hint=REMEDIES[fault.code]
    return _(title)+'\n'+_(hint)



def editor_result_message(result):
    """UI feedback only: a daemon cache never proves the hardware applied RGB."""
    from logi_center.core.services.operations import State
    if result.state != State.SENT:return operation_message(result)
    if result.source == 'backend_cache':
        text=_('Отправлено · кэш backend совпал. Подтверждение устройства недоступно.')
    elif result.fault:
        text=_('Отправлено · прочитать результат не удалось.')
    else:
        text=_('Отправлено · проверка результата не поддерживается.')
    if result.fault:text+='\n'+fault_message(result.fault)
    return text


def eweadn_controls(device,cap):
    """Shared descriptors for actual ByteTech fields, independent of QML."""
    from logi_center.protocols.eweadn_protocol import RATES,validate_action
    values={c.name:c.value for c in device.capabilities if c.backend=='eweadn'}
    profile=values.get('profiles');maximum=values.get('max_dpi',26000)
    result=[]
    for key,value in cap.value.items():
        if key=='axes_available':continue
        kind='number';choices=[];labels=[];low=0;high=255;step=1;writable=cap.writable
        group={'dpi_config':'pointer','button_bindings':'buttons','sensor_config':'advanced'}[cap.name]
        title='Чувствительность DPI'
        if cap.name=='dpi_config':
            if key=='count':title='Количество ступеней DPI';low=1;high=8
            elif key=='active':title='Активная ступень DPI';kind='choice';choices=list(range(8));labels=[str(i+1) for i in choices]
            elif key.startswith('color'):title='Цвет';kind='color'
            else:
                low=50;high=maximum;step=50
                if cap.value.get('axes_available'):title=NAMES['dpi_x' if key.startswith('x') else 'dpi_y']
        elif cap.name=='button_bindings':
            title='Назначение кнопки';kind='ewebinding';writable=writable and int(key) in values.get('writable_buttons',[])
        elif key in ('motion_sync','angle_snap','ripple'):title=NAMES[key];kind='bool'
        elif key=='polling_rate':
            title='Частота опроса, Гц';kind='choice';group='performance'
            code=values.get('max_report');choices=sorted(v for v in RATES if type(code) is int and 0<=code<7 and v<=RATES[code])
            writable=writable and bool(choices) and value in choices
        elif key=='performance_mode':
            title='Режим работы сенсора';kind='choice';choices=[0,1,2,3]
            labels=['Обычный','Высокая скорость','Игровой','Максимальная производительность'];group='performance'
            writable=writable and device.connection!='usb'
        elif key=='lod':
            title='Высота отрыва';kind='choice'
            choices=[1,2,3] if values.get('model_id') in ('s9ultra','s9ultra+') else [1,2]
            labels=['0.7 mm','1.0 mm','2.0 mm'] if len(choices)==3 else ['1.0 mm','2.0 mm']
        elif key=='debounce':title='Задержка устранения дребезга, мс';high=20
        elif key=='sleep':title='Сон через, с';high=3000;step=30
        def factory(v,k=key,c=cap):return c.plan({k:v})
        result.append(Control(f'eweadn:{cap.name}:{key}',title,group,value,
            f'eweadn:{device.id}:profile:{profile}:{cap.name}:{key}','eweadn',kind,
            choices=choices,choice_labels=labels,minimum=low,maximum=high,step=step,
            source=cap.source,writable=writable,factory=factory,capability=cap.name,
            profile=profile,key_index=key,batch_factory=cap.plan))
    return result
