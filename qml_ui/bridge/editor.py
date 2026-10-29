"""Qt facade for shared controls, drafts and existing backend operations."""
from copy import deepcopy
from pathlib import Path
import tempfile
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer, QCoreApplication, QEvent, Qt
from discovery import Epoch
from drafts import DraftStore
from execution import CURRENT_CANCEL, Fault, FaultCode
from operations import perform, State, plan_for, same
from control_service import (binding, capability_controls, ratbag_controls, key_controls,
                             keyboard_keys, ace_binding_controls, GROUPS, display, is_k7_ultra, k7_dpi_indicator)
from .models import CapabilityListModel


class ActiveProfileChanged(ValueError):
    """The physical ratbag profile changed after editor data was loaded."""


class EditorController(QObject):
    changed=Signal()
    _ready=Signal(str,object,object,object)
    _stateReady=Signal(object,object,object)

    def __init__(self,owner,pool,simulation=False,store=None,runner=None):
        super().__init__(owner)
        self.owner=owner;self.pool=pool;self.simulation=simulation;self.runner=runner
        self.reader=None
        self._temp=tempfile.TemporaryDirectory(prefix='logi-editor-') if simulation and store is None else None
        self.store=store or DraftStore(Path(self._temp.name)/'drafts.json' if self._temp else None)
        self.fields=CapabilityListModel(self);self.epoch=Epoch();self._closed=False
        self._g515_key_model=CapabilityListModel(self)
        self._ewe_dpi_model=CapabilityListModel(self);self._ewe_button_model=CapabilityListModel(self)
        self.device=None;self._manager=None;self._binding=None;self._controls=[];self._key_controls=[]
        self._buttons=[];self._ratbag=None;self._pending={};self._states={};self._sections={};self._keys={};self._button_selection={}
        self._macro_conflict=False
        self._k7_axes={}
        self._k7_button_selection={}
        self._ace_selections={};self._editing_selection=False
        self._ace_remaps=[];self._ace_layer=0;self._ace_binding_cap=None;self._ace_binding_profile=None
        self._ace_advanced_cap=None;self._ace_advanced_profile=None;self._ace_advanced_controls=[]
        self._ace_color_cap=None;self._ace_color_profile=None
        self._g515=[]
        self._ewe_state=None
        self._g515_target='G515'
        self.keyboard_reader=None
        self._g515_selections={}
        self._discarded=set()
        self._device_messages={}
        self._reference_layout='tkl'
        self._section='pointer';self._key='50';self._button=0;self._busy=False;self._message='';self._result='';self._recording=False
        self._macro=None;self._warning_tokens=None;self._macro_states={};self._job=None
        self._capture_window=None;self._capture_item=None;self._capture_time=None;self._capture_pauses=True
        self._library_selected='';self._library_name='';self._library_error=False
        from macro_library import load
        try:self._library=load(self.store)
        except ValueError:self._library=[];self._library_error=True
        self._g502_view='top'
        self._draft_timer=QTimer(self);self._draft_timer.setSingleShot(True);self._draft_timer.setInterval(250);self._draft_timer.timeout.connect(self.flush)
        self._ready.connect(self._accept)
        self._observing=False;self._state_busy=False;self._state_error=''
        self._state_epoch=Epoch()
        self._state_timer=QTimer(self);self._state_timer.setSingleShot(True)
        self._state_timer.timeout.connect(self._poll_state)
        self._stateReady.connect(self._accept_state)
        self.changed.connect(self._schedule_state)
        self.changed.connect(self._update_g515_keys)
        self.changed.connect(self._update_ewe_models)

    def tr(self,text):return self.owner.tr(text)
    @Property('QVariant',constant=True)
    def fieldModel(self):return self.fields
    @Property(bool,notify=changed)
    def busy(self):return self._busy
    @Property(bool,notify=changed)
    def available(self):return self.device is not None and self.device.connected is True
    @Property(str,notify=changed)
    def message(self):return self.tr(self._message)
    @Property(str,notify=changed)
    def resultState(self):return self._result
    @Property(str,notify=changed)
    def section(self):return self._section
    @Property(bool,notify=changed)
    def observing(self):return self._observing
    @observing.setter
    def observing(self,value):
        value=bool(value)
        if value==self._observing:return
        self._observing=value
        if not value:self._state_epoch.invalidate();self._state_timer.stop()
        else:self._schedule_state(0)
        self.changed.emit()
    @Property(str,notify=changed)
    def liveReadError(self):return self._state_error
    @Property('QVariantList',notify=changed)
    def sections(self):
        if self.eweadnEditor:
            return [{'id':key,'label':self.tr(title)} for key,title in
                    [('buttons','Кнопки и макросы'),('pointer','Чувствительность и скорость'),
                     ('performance','Производительность'),('macros','Библиотека макросов'),
                     ('advanced','Параметры сенсора'),('other','Прочее')]]
        if self.g515Editor:
            sections=[{'id':key,'label':self.tr(title)} for key,title in
                    [('lighting','Подсветка'),('freestyle','Поклавишные цвета'),('animations','Анимации'),
                     ('assignments','Назначения'),('keyboard_settings','Настройки клавиатуры')]]
            used={s['id'] for s in sections}|{'keys'}
            groups={f.group for f in self._controls}
            return sections+[{'id':key,'label':self.tr(title)} for key,title in GROUPS.items() if key in groups-used]
        if self.aceEditor:
            return [{'id':key,'label':self.tr(label)} for key,label in
                    [('lighting','Подсветка'),('keys','Срабатывание'),('key_assignments','Назначения'),
                     ('advanced_keys','Расширенные клавиши'),('performance','Производительность'),('profiles','Прочее')]]
        groups={f.group for f in self._controls}
        if self.device and is_k7_ultra(self.device):
            groups.add('indicators')
            if self.device.pid=='1001' or any(c.name=='dock_lighting' for c in self.device.capabilities):groups.add('dock')
        if self._buttons:groups.add('buttons')
        if self.device and 'mchose-ace68' in self.device.backends:groups.add('keys')
        if self.device and self.device.kind=='keyboard':groups.add('keys')
        return [{'id':key,'label':self.tr(title)} for key,title in GROUPS.items() if key in groups]

    @Property(bool,notify=changed)
    def g515Editor(self):return bool(self.device and self.device.kind=='keyboard' and 'G515' in self.device.name)

    @Property(bool,notify=changed)
    def eweadnEditor(self):return bool(self.device and self.device.kind=='mouse' and 'eweadn' in self.device.backends)

    @Property('QVariant',notify=changed)
    def eweadnFields(self):return {row['id']:row for row in self.fields._rows if row['id'].startswith('eweadn:')}

    @Property('QVariant',notify=changed)
    def eweadnState(self):
        state=self._ewe_state or {}
        return {k:v for k,v in state.items() if k not in ('pages','button_bindings','dpi_config','sensor_config')}

    @Property(str,notify=changed)
    def eweadnContext(self):
        if not self.eweadnEditor or not self._ewe_state:return ''
        from eweadn_adapter import fingerprint
        from devices import identity
        return identity(repr(self._binding))+':'+fingerprint(self._ewe_state)

    @Property('QVariantList',notify=changed)
    def eweadnDpi(self):
        count=self._field('eweadn:dpi_config:count');active=self._field('eweadn:dpi_config:active')
        if not count or not active:return []
        return [{'id':str(i),'index':i,'active':self._desired(active)[0]==i,'x':self.eweadnFields.get(f'eweadn:dpi_config:x{i}'),
                 'y':self.eweadnFields.get(f'eweadn:dpi_config:y{i}') if self._ewe_state and self._ewe_state['dpi_config']['axes_available'] else None,
                 'color':self.eweadnFields.get(f'eweadn:dpi_config:color{i}')} for i in range(self._desired(count)[0])]

    @Property('QVariantList',notify=changed)
    def eweadnButtons(self):
        if not self.eweadnEditor:return []
        return [{'id':str(i),'index':i,'label':self.tr(label),'x':x,'y':y,'selected':i==self._button,
                 'field':self.eweadnFields.get('eweadn:button_bindings:'+str(i))} for i,label,x,y in
                [(0,'Левая кнопка',.32,.22),(1,'Правая кнопка',.68,.22),(2,'Нажатие колеса',.5,.29),
                 (4,'Вперёд',.08,.40),(3,'Назад',.08,.53)]]

    @Property(QObject,constant=True)
    def eweadnDpiModel(self):return self._ewe_dpi_model
    @Property(QObject,constant=True)
    def eweadnButtonModel(self):return self._ewe_button_model
    def _update_ewe_models(self):
        self._ewe_dpi_model.update(self.eweadnDpi if self.eweadnEditor else [])
        self._ewe_button_model.update(self.eweadnButtons)

    @Property('QVariantList',notify=changed)
    def eweadnActions(self):
        if not self.eweadnEditor:return []
        mouse=[{'group':'mouse','label':self.tr(label),'value':[1,i+1,0,0]} for i,label in enumerate(
               ['Левый щелчок','Правый щелчок','Нажатие колёсика','Назад','Вперёд'])]
        keyboard=[{'group':'keyboard','label':c,'value':[2,i+4,0,0]} for i,c in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ')]
        keyboard += [{'group':'keyboard','label':c,'value':[2,i+30,0,0]} for i,c in enumerate('1234567890')]
        keyboard += [{'group':'keyboard','label':'F'+str(i+1),'value':[2,i+58,0,0]} for i in range(12)]
        keyboard += [{'group':'keyboard','label':label,'value':[2,code,0,0]} for code,label in
                     [(40,'Enter'),(41,'Esc'),(42,'Backspace'),(43,'Tab'),(44,'Space'),(79,'→'),(80,'←'),(81,'↓'),(82,'↑')]]
        media=[{'group':'media','label':self.tr(label),'value':[3,code&255,code>>8,0]} for code,label in
               [(0xe2,'Без звука'),(0xe9,'Громче'),(0xea,'Тише'),(0xcd,'Воспроизведение / пауза'),
                (0xb5,'Следующий трек'),(0xb6,'Предыдущий трек'),(0xb7,'Остановить воспроизведение')]]
        return mouse+keyboard+media

    @Slot(bool,str)
    def resetEweadn(self,confirmed,context):
        if not confirmed or not context or context!=self.eweadnContext or not self.eweadnEditor or not self.available or self._busy or not self._ewe_state or self._other_write_busy():return
        expected=self._binding;token=self.epoch.token()
        device=self.device;target=device.targets['eweadn'][0];state=deepcopy(self._ewe_state)
        def reset():
            from backend import run
            from eweadn_adapter import reset_plan
            def guarded(args,**kwargs):
                self._guard(expected,token);self._manager.guard_command(args)
                if self.simulation and self.runner is None:raise ValueError('Simulation transport unavailable')
                return (self.runner or run)(args,**kwargs)
            self._manager.route(device.id,'factory_reset','eweadn')
            return [(None,None,perform(reset_plan(target,state,True),guarded,token))]
        self._submit('apply',reset)

    @Property('QVariant',notify=changed)
    def g515Fields(self):return {row['id']:row for row in self.fields._rows if row['id'].startswith('g515:')}

    @Property(QObject,constant=True)
    def g515KeyModel(self):return self._g515_key_model

    def _update_g515_keys(self):self._g515_key_model.update(self.g515Keys)

    @Property('QVariantList',notify=changed)
    def g515Keys(self):
        if not self.g515Editor:return []
        from g515_layout import keys
        selected=self._g515_selections.get(self.device.id,set())
        rows=[]
        for key in keys():
            field=self._field('g515:key:'+key['id'])
            value,conflict=self._desired(field) if field else (None,False)
            rows.append(dict(key,selected=key['id'] in selected,available=bool(field and field.writable and self.available),
                             color='#'+''.join(f'{v:02x}' for v in value) if value else '',
                             dirty=bool(field and not same(value,field.observed)),conflict=conflict))
        return rows

    @Property('QVariantList',notify=changed)
    def g515Palette(self):
        counts={}
        for key in self.g515Keys:
            if key['color']:counts[key['color']]=counts.get(key['color'],0)+1
        return [{'color':color,'count':count} for color,count in sorted(counts.items())]

    @Property(int,notify=changed)
    def g515SelectionCount(self):return len(self._g515_selections.get(self.device.id,set())) if self.device else 0

    @Slot(str,bool)
    def selectG515Key(self,key,additive):
        if not self.g515Editor or self._busy or key not in [r['id'] for r in self.g515Keys if r['available']]:return
        selected=self._g515_selections.setdefault(self.device.id,set())
        if not additive:selected.clear()
        if key in selected:selected.remove(key)
        else:selected.add(key)
        self.changed.emit()

    @Slot(str)
    def selectG515Group(self,name):
        if not self.g515Editor or self._busy:return
        from g515_layout import group_ids
        available={r['id'] for r in self.g515Keys if r['available']}
        self._g515_selections[self.device.id]=group_ids(name)&available;self.changed.emit()

    @Slot('QVariant')
    def paintG515(self,color):
        if not self.g515Editor or self._busy:return
        if hasattr(color,'toVariant'):color=color.toVariant()
        selected=self._g515_selections.get(self.device.id,set())
        self._editing_selection=True
        try:
            for key in selected:self.edit('g515:key:'+key,color)
        finally:self._editing_selection=False
        self._render()
    @Property('QVariant',notify=changed)
    def k7Status(self):
        if not self.device or not is_k7_ultra(self.device):return {}
        caps={c.name:c for c in self.device.capabilities if c.backend=='mchose'}
        from battery_presentation import battery_display
        battery=battery_display(self.device)
        profile=caps.get('profiles')
        linked=self.device.connected is True
        stage=caps.get('stage')
        stage_indicator=k7_dpi_indicator(stage.value) if linked and stage and stage.readable else None
        return {
            'link': self.tr('Мышь подключена') if linked else
                    self.tr('Мышь не подключена') if self.device.connected is False else self.tr('Нет данных'),
            'charging': (self.tr('Заряжается') if battery['charging'] else self.tr('Не заряжается'))
                        if linked and battery['chargingKnown'] else self.tr('Нет данных'),
            'profile': self.tr('Профиль')+' '+str(profile.value+1)
                       if linked and profile and profile.readable and type(profile.value) is int else self.tr('Нет данных'),
            'stageNumber':stage.value+1 if stage_indicator else 0,
            'stageColor':stage_indicator[1] if stage_indicator else '',
            'stageName':self.tr(stage_indicator[0]) if stage_indicator else '',
        }

    @Property('QVariant',notify=changed)
    def dockState(self):
        cap=next((c for c in self.device.capabilities if c.backend=='mchose' and c.name=='dock_lighting'),None) if self.device else None
        state=deepcopy(cap.value) if cap and isinstance(cap.value,dict) else {}
        state.update({f.key_index:self._desired(f)[0] for f in self._controls if f.capability=='dock_lighting'})
        state['available']=bool(cap and cap.readable)
        state['writable']=bool(cap and cap.writable and self.available and not self._busy)
        return state

    @Property('QVariantList',notify=changed)
    def dockModes(self):
        field=self._field('mchose:dock:mode')
        return [{'value':value,'label':self.tr(label)} for value,label in zip(field.choices,field.choice_labels)] if field else []

    @Property('QVariant',notify=changed)
    def k7Fields(self):return {row['id']:row for row in self.fields._rows if row['id'].startswith('mchose:')}

    @Property(bool,notify=changed)
    def k7Editor(self):return bool(self.device and is_k7_ultra(self.device) and self._field('mchose:dpi_config:count'))

    def _k7_scope(self):
        profile=next((c.value for c in self.device.capabilities if c.backend=='mchose' and c.name=='profiles'),None) if self.device else None
        return (self.device.id if self.device else '',profile)

    @Property(bool,notify=changed)
    def k7SeparateAxes(self):
        if not self.k7AxesAvailable:return False
        scope=self._k7_scope()
        if scope in self._k7_axes:return self._k7_axes[scope]
        return any(self._field('mchose:dpi_config:x'+str(i)) and self._field('mchose:dpi_config:y'+str(i)) and
                   self._desired(self._field('mchose:dpi_config:x'+str(i)))[0]!=self._desired(self._field('mchose:dpi_config:y'+str(i)))[0] for i in range(6))

    @Property(bool,notify=changed)
    def k7AxesAvailable(self):
        cap=next((c for c in self.device.capabilities if c.backend=='mchose' and c.name=='dpi_config'),None) if self.device else None
        return bool(cap and isinstance(cap.value,dict) and cap.value.get('axes_available'))

    @Slot(bool)
    def setK7SeparateAxes(self,value):
        if not self.k7Editor or self._busy or not self.k7AxesAvailable:return
        self._k7_axes[self._k7_scope()]=value
        if not value:
            for i in range(6):
                field=self._field('mchose:dpi_config:x'+str(i))
                self.edit('mchose:dpi_config:y'+str(i),self._desired(field)[0])
        self.changed.emit()

    @Property(int,notify=changed)
    def k7SelectedButton(self):return self._k7_button_selection.get(self.device.id if self.device else '',0)

    @Slot(int)
    def selectK7Button(self,index):
        if self.device and index in (0,1,2,3,4):self._k7_button_selection[self.device.id]=index;self.changed.emit()

    @Property('QVariantList',notify=changed)
    def k7Buttons(self):
        from k7_settings import BUTTONS,action_label
        rows=[]
        for index,label,x,y in BUTTONS:
            field=self._field('mchose:button_bindings:'+str(index))
            if field:
                desired=self._desired(field)[0]
                caption=self.tr(action_label(desired))
                rows.append({'index':index,'label':self.tr(label),'x':x,'y':y,'assignment':caption,'dirty':not same(desired,field.observed)})
        return rows

    @Property('QVariantList',notify=changed)
    def k7Actions(self):
        from k7_settings import actions
        return [{**row,'label':self.tr(row['label'])} for row in actions()]

    @Property(bool,notify=changed)
    def aceEditor(self):return bool(self.device and 'mchose-ace68' in self.device.backends)

    def _ace_scope(self):
        profile=next((c.value for c in self.device.capabilities if c.backend=='mchose-ace68' and c.name=='profiles'),None) if self.device else None
        return (self.device.id if self.device else '',profile)

    def _ace_rgb_owned(self,device=None):
        device=device or self.device
        return bool(device and any(c.backend=='openrgb' and c.writable and c.name in ('lighting','lighting_mode','brightness','lighting_speed','lighting_palette') for c in device.capabilities))

    def _guard_ace_rgb(self,args,device):
        if (args[:3]==['logi-sdk','mchose-ace68','set'] and len(args)>4 and
                args[4].rsplit('/',1)[-1] in ('lighting','lighting_mode','brightness','lighting_speed','lighting_palette','lighting_direction','key_lighting') and self._ace_rgb_owned(device)):
            raise Fault(FaultCode.CONFIG,'editor','OpenRGB owns lighting; competing Ace68 writes are disabled')

    @Property('QVariantList',notify=changed)
    def aceSelectedKeys(self):
        return sorted(self._ace_selections.get(self._ace_scope(),{self._key})) if self.aceEditor else []

    @Property('QVariant',notify=changed)
    def aceFields(self):return {row['id']:row for row in self.fields._rows} if self.aceEditor else {}

    @Property('QVariant',notify=changed)
    def aceKeyValues(self):
        result={}
        for field in self._key_controls:
            result.setdefault(field.key_index,{})[field.capability]=self._desired(field)[0]
        return result

    @Property('QVariant',notify=changed)
    def aceLightOptions(self):
        from ace68_protocol import MODES,NO_COLOR_EFFECTS,NO_SPEED_EFFECTS,DIRECTION_EFFECTS
        field=self._field('mchose-ace68:lighting_mode')
        mode=next((key for key,value in MODES.items() if field and value==self._desired(field)[0]),None)
        return {'color':mode is not None and mode not in NO_COLOR_EFFECTS,
                'speed':mode is not None and mode not in NO_SPEED_EFFECTS,
                'brightness':mode is not None and mode!=255,'direction':mode in DIRECTION_EFFECTS}

    @Property('QVariant',notify=changed)
    def aceColorSelection(self):
        fields=[f for f in self._controls if f.capability=='key_lighting' and f.key_index in self.aceSelectedKeys]
        values=[self._desired(f)[0] for f in fields]
        mode=self._field('mchose-ace68:lighting_mode')
        return {'available':bool(self._ace_color_cap),'value':values[0] if values else [255,255,255],
                'mixed':bool(values) and any(v!=values[0] for v in values),
                'writable':bool(fields) and all(f.writable for f in fields) and self.available and bool(mode and mode.observed=='Custom' and self._desired(mode)[0]=='Custom')}

    @Property('QVariant',notify=changed)
    def aceKeyColors(self):return {f.key_index:self._desired(f)[0] for f in self._controls if f.capability=='key_lighting'}

    @Slot('QVariant')
    def editAceColor(self,value):
        if not self.aceColorSelection['writable'] or self._busy:return
        if hasattr(value,'toVariant'):value=value.toVariant()
        self._editing_selection=True
        try:
            for field in self._controls:
                if field.capability=='key_lighting' and field.key_index in self.aceSelectedKeys:self.edit(field.id,value)
        finally:self._editing_selection=False
        self._render()

    @Slot()
    def readAceColors(self):self._read_ace('colors')

    @Property(int,notify=changed)
    def aceLayer(self):return self._ace_layer

    @Property(str,notify=changed)
    def aceContext(self):return repr((self._binding,self._ace_scope(),self._ace_layer)) if self.aceEditor else ''

    @Property('QVariantList',notify=changed)
    def aceAdvancedBindings(self):
        rows=[]
        for field in self._ace_advanced_controls:
            desired,conflict=self._desired(field)
            rows.append({'id':field.key_index,'spec':desired,'observed':field.observed,
                         'dirty':not same(desired,field.observed),'conflict':conflict})
        return rows

    @Property(bool,notify=changed)
    def aceAdvancedReady(self):return bool(self._ace_advanced_cap and self._ace_advanced_cap.writable and self.available)

    def _advanced_control(self,identifier):
        from control_service import Control
        cap=self._ace_advanced_cap
        profile=self._ace_scope()[1]
        return Control('ace:advanced:'+identifier,'Расширенная привязка','advanced_keys',deepcopy(cap.value.get(identifier)),
                       f'ace68:{self.device.id}:profile:{profile}:advanced:{identifier}', 'mchose-ace68','aceadvanced',
                       source=cap.source,writable=cap.writable,factory=lambda v:cap.plan({identifier:v}),
                       capability='advanced_keys',profile=profile,key_index=identifier,batch_factory=cap.plan)

    @Slot('QVariant',str)
    def stageAceAdvanced(self,spec,context):
        if hasattr(spec,'toVariant'):spec=spec.toVariant()
        if not self.aceAdvancedReady or self._busy or context!=self.aceContext:return
        try:
            # Qt JavaScript numbers are doubles. Convert exact integers only.
            def native(value):
                if isinstance(value,list):return [native(v) for v in value]
                if isinstance(value,dict):return {k:native(v) for k,v in value.items()}
                return int(value) if type(value) is float and value.is_integer() else value
            spec=native(spec)
            identifier=str(spec['layer'])+':'+str(min(spec['keys']))
            self._ace_advanced_cap.plan({identifier:spec})
        except (ValueError,TypeError,KeyError):
            self._message=self.tr('Привязка недоступна: проверь клавиши, действия и параметры. Существующие данные сохранены.');self.changed.emit();return
        if not any(f.key_index==identifier for f in self._ace_advanced_controls):self._ace_advanced_controls.append(self._advanced_control(identifier))
        self.edit('ace:advanced:'+identifier,spec)

    @Slot(str,str)
    def removeAceAdvanced(self,identifier,context):
        if not self.aceAdvancedReady or self._busy or context!=self.aceContext:return
        field=next((f for f in self._ace_advanced_controls if f.key_index==identifier),None)
        if not field:return
        if field.observed is None:
            self._pending.pop(field.draft_key,None);self._discarded.add(field.draft_key)
            self.owner._preferences_pool.submit(self.store.discard,field.draft_key);self._render();return
        try:self._ace_advanced_cap.plan({identifier:None})
        except ValueError:
            self._message=self.tr('Неизвестный формат привязки сохранён без изменений.');self.changed.emit();return
        self.edit(field.id,None)

    @Slot(int)
    def setAceLayer(self,layer):
        if self.aceEditor and not self._busy and 0<=layer<4:self._ace_layer=layer;self._render()

    @Property('QVariantList',notify=changed)
    def aceActions(self):
        from ace68_bindings import actions
        return [{**action,'label':self.tr(action['label'])} for action in actions()]

    @Property('QVariant',notify=changed)
    def aceBindingSelection(self):
        from ace68_bindings import label
        selected=[f for f in self._ace_remaps if f.key_index.split(':')[0]==str(self._ace_layer) and f.key_index.split(':')[1] in self.aceSelectedKeys]
        names=[self.tr(label(self._desired(f)[0])) for f in selected]
        return {'available':bool(self._ace_binding_cap),'writable':bool(selected) and all(f.writable for f in selected) and self.available,
                'label':names[0] if names and all(n==names[0] for n in names) else self.tr('Разные значения') if names else self.tr('Нет данных')}

    @Slot('QVariant')
    def editAceBinding(self,value):
        if hasattr(value,'toVariant'):value=value.toVariant()
        if not self.aceEditor or self._busy or not self.available:return
        if isinstance(value,list):value=[int(v) if type(v) is float and v.is_integer() else v for v in value]
        fields=[f for f in self._ace_remaps if f.key_index.startswith(str(self._ace_layer)+':') and f.key_index.split(':')[1] in self.aceSelectedKeys]
        try:
            for field in fields:field.validate(value)
        except ValueError:self._message=self.tr('Назначение недоступно для выбранных клавиш.');self.changed.emit();return
        self._editing_selection=True
        try:
            for field in fields:self.edit(field.id,value)
        finally:self._editing_selection=False
        self._render()

    @Slot()
    def readAceBindings(self):
        self._read_ace('bindings')

    @Slot()
    def readAceAdvanced(self):
        self._read_ace('advanced')

    def _read_ace(self,action):
        if not self.aceEditor or self._busy or not self.available:return
        targets=self.device.targets.get('mchose-ace68',[])
        if len(targets)!=1:return
        expected=self._binding;token=self.epoch.token();target=targets[0]
        def read():
            import json
            self._guard(expected,token)
            if self.simulation and self.runner is None:raise ValueError('No simulation keyboard transport')
            from backend import run
            observed=json.loads((self.runner or run)(['logi-sdk','mchose-ace68',action,target]))
            self._guard(expected,token)
            return observed
        self._submit('ace-'+action+'-read',read)

    @Slot(str)
    def toggleAceKey(self,index):
        if not self.aceEditor or self._busy or index not in {k['id'] for k in self.keyModel}:return
        selected=set(self.aceSelectedKeys)
        if index in selected:selected.remove(index)
        else:selected.add(index)
        self._ace_selections[self._ace_scope()]=selected
        if index in selected:self._key=index
        elif selected:self._key=next(k['id'] for k in self.keyModel if k['id'] in selected)
        self._keys[self.device.id]=self._key;self._render()

    @Slot(str)
    def selectAceKeys(self,mode):
        if not self.aceEditor or self._busy:return
        keys=self.keyModel;all_keys={k['id'] for k in keys}
        if mode=='all':selected=all_keys
        elif mode=='none':selected=set()
        elif mode=='inverse':selected=all_keys-set(self.aceSelectedKeys)
        elif mode=='wasd':selected={k['id'] for k in keys if k['label'] in ('W','A','S','D')}
        else:return
        self._ace_selections[self._ace_scope()]=selected
        if selected:self._key=next(k['id'] for k in keys if k['id'] in selected)
        self._keys[self.device.id]=self._key;self._render()

    @Slot(str,'QVariant')
    def editAceKeys(self,parameter,value):
        if not self.aceEditor or self._busy or not self.available:return
        if hasattr(value,'toVariant'):value=value.toVariant()
        fields=[f for f in self._key_controls if f.capability==parameter and f.key_index in self.aceSelectedKeys]
        if not fields:return
        try:
            from ace68_protocol import validate_key_value
            details=next(c.value for c in self.device.capabilities if c.name=='key_details' and c.backend=='mchose-ace68')
            for field in fields:validate_key_value({'key_details':details},parameter,field.key_index,field.validate(value))
        except (ValueError,TypeError,StopIteration):
            self._message=self.tr('Значение не подходит всем выбранным клавишам.');self.changed.emit();return
        self._editing_selection=True
        try:
            for field in fields:self.edit(field.id,value)
        finally:self._editing_selection=False
        self._render()

    @Property('QVariantList',notify=changed)
    def k7LegacyDrafts(self):
        """Keep pre-grid DPI/stage drafts visible without guessing their context."""
        if not self.k7Editor:return []
        import re
        prefix='device:'+self.device.id+':'
        rows=[]
        saved={**self.store.values,**{key:{'base':base,'desired':desired} for key,(base,desired) in self._pending.items()}}
        for key,draft in saved.items():
            if key in self._discarded or not key.startswith(prefix) or not isinstance(draft,dict) or 'desired' not in draft:continue
            match=re.fullmatch(r'(dpi|stage)(?:@mchose)?(?::profile:([0-2]))?(?::stage:([0-5]))?',key[len(prefix):])
            if not match:continue
            name,profile,stage=match.groups();value=draft['desired']
            label=self.tr('Чувствительность DPI' if name=='dpi' else 'Активная ступень DPI')
            if profile is not None:label+=' · '+self.tr('Профиль')+' '+str(int(profile)+1)
            if stage is not None:label+=' · '+self.tr('Уровень DPI')+' '+str(int(stage)+1)
            if name=='stage' and type(value) is int:value+=1
            rows.append({'key':key,'label':label,'value':display(value)})
        return rows

    @Slot(str)
    def discardK7LegacyDraft(self,key):
        if self._busy or key not in {row['key'] for row in self.k7LegacyDrafts}:return
        self._pending.pop(key,None);self._discarded.add(key)
        self.owner._preferences_pool.submit(self.store.discard,key);self.changed.emit()

    def telemetryUpdated(self):
        """Notify K7 read-only labels without rebuilding settings or drafts."""
        if self.device and is_k7_ultra(self.device):self.changed.emit()
    @Property('QVariantList',notify=changed)
    def keyModel(self):
        if self.device and 'mchose-ace68' in self.device.backends:return keyboard_keys()
        if self.device and self.device.kind=='keyboard':
            from keyboard_layouts import LAYOUTS
            return [{'id':str(i),'label':k.label,'x':k.x,'y':k.y,'w':k.width,'h':k.height} for i,k in enumerate(LAYOUTS[self._reference_layout].keys)]
        return []
    @Property(bool,notify=changed)
    def referenceKeyboard(self):return bool(self.device and self.device.kind=='keyboard' and 'mchose-ace68' not in self.device.backends)
    @Property(float,notify=changed)
    def keyboardUnits(self):
        from keyboard_layouts import LAYOUTS
        return LAYOUTS[self._reference_layout].width_u if self.referenceKeyboard else 16.
    @Property(float,notify=changed)
    def keyboardRows(self):
        from keyboard_layouts import LAYOUTS
        return LAYOUTS[self._reference_layout].height_u if self.referenceKeyboard else 5.
    @Slot(str)
    def setReferenceLayout(self,name):
        if name in ('tkl','full','60','laptop'):self._reference_layout=name;self.changed.emit()
    @Property(str,notify=changed)
    def selectedKey(self):return self._key
    @Property('QVariantList',notify=changed)
    def buttons(self):
        from mouse_models import layout
        entry=self._model_artwork()
        model='G502' if entry and entry.get('anchors')=='g502' else self.device.name if self.device else ''
        anchors=layout(model,len(self._buttons))
        from mouse_models import editor_callouts,button_caption
        callouts=editor_callouts(len(self._buttons))
        return [dict(b,label=str(b['index']+1)+' · '+self.tr(button_caption(model,b['index'])),cx=callouts[b['index']][0],cy=callouts[b['index']][1],x=anchors.get(b['index'],(.5,.5))[0],y=anchors.get(b['index'],(.5,.5))[1]) for b in self._buttons]
    def _model_artwork(self):
        if not self.device:return None
        provider=getattr(self.owner,'_artwork',None)
        return getattr(provider,'product_models',{}).get((self.device.vid.lower(),self.device.pid.lower()))

    @Property(bool,notify=changed)
    def g502Editor(self):
        return bool(self.device and self.device.vid.lower()=='046d' and self.device.pid.lower() in ('c08b','c08d','407f') and 'ratbagctl' in self.device.backends)

    @Property(str,notify=changed)
    def deviceName(self):return self.device.name if self.device else ''

    @Property(str,notify=changed)
    def g502View(self):return self._g502_view

    @Slot(str)
    def setG502View(self,view):
        if view not in ('top','side') or self._busy:return
        self._g502_view=view
        if self.g502Buttons and self._button not in [b['index'] for b in self.g502Buttons]:self.selectButton(self.g502Buttons[0]['index'])
        self.changed.emit()

    @Property('QVariantList',notify=changed)
    def g502Buttons(self):
        from mouse_models import G502_ART,button_caption
        anchors=G502_ART[self._g502_view]['anchors'];rows=[]
        left=[0,7,6,10];right=[1,2,9,8]
        for button in self._buttons:
            index=button['index']
            if index not in anchors:continue
            side='right' if index in right else 'left'
            row=(right if side=='right' else left).index(index) if self._g502_view=='top' else {4:0,3:1,5:2}[index]
            rows.append({**button,'label':self.tr(button_caption('G502',index)),'x':anchors[index][0],'y':anchors[index][1],'side':side,'row':row})
        return rows

    @Property('QVariant',notify=changed)
    def g502Canvas(self):
        from mouse_models import G502_ART,g502_wireless
        data={k:v for k,v in G502_ART[self._g502_view].items() if k!='anchors'}
        if g502_wireless(self.device):data['file']=data['wireless_file']
        return data

    @Property('QVariant',notify=changed)
    def ratbagProfileStatus(self):
        data=self._ratbag or {};live=data.get('live_profile',{})
        return {'profile':data.get('active'),'daemonProfile':data.get('daemon_active',data.get('active')),
                'mismatch':data.get('profile_mismatch',False),'live':'daemon_active' in data,
                'host':live.get('mode')=='host','failed':data.get('live_profile_error',False)}

    @Slot()
    def syncRatbagProfile(self):
        if not self.available or self._busy or not self._ratbag or not self._ratbag.get('profile_mismatch') or self._other_write_busy():return
        expected=self._binding;token=self.epoch.token();profile=self._ratbag['active'];target=self.device.targets['ratbagctl'][0]
        def work():
            import json,re
            model=re.search(r'Model:\s*(usb:046d:c08b:[0-9a-fA-F]+)',self._ratbag.get('text',''))
            if not model:raise ValueError('Exact model unavailable')
            def run(args,**kwargs):
                self._guard(expected,token);self._manager.guard_command(args)
                from backend import run
                if self.simulation and self.runner is None:raise ValueError('No simulation transport')
                return (self.runner or run)(args,**kwargs)
            live=json.loads(run(['logi-sdk','logitech-status','read',model[1]]))
            if live.get('mode')!='onboard' or live.get('profile')!=profile:raise ActiveProfileChanged('Physical profile changed')
            return [(None,None,perform(plan_for(['ratbagctl',target,'profile','active','set',str(profile)]),run,token))]
        self._submit('profile-sync',work)
    @Property(str,notify=changed)
    def buttonDiagram(self):
        if self.g502Editor:return '../assets/devices/exact/'+self.g502Canvas['file']
        entry=self._model_artwork()
        if entry and entry.get('editor_diagram'):
            return '../assets/devices/exact/'+entry['editor_diagram']
        return '../assets/diagrams/'+('g502.svg' if self.device and 'G502' in self.device.name else 'generic.svg')
    @Property(int,notify=changed)
    def selectedButton(self):return self._button
    @Property('QVariantList',notify=changed)
    def assignments(self):
        button=self._button_data()
        return [{'label':self.tr(a['label']),'value':a['value']} for a in button.get('actions',[])]
    @Property('QVariantList',notify=changed)
    def macroEvents(self):
        from mouse_models import friendly
        rows=[]
        for i,token in enumerate(self._macro.tokens if self._macro else []):
            if token.startswith('t'):label=self.tr('Пауза')+' '+token[1:]+' ms'
            else:
                name=token.lstrip('+-')
                mouse={'BTN_LEFT':'Левый щелчок','BTN_RIGHT':'Правый щелчок','BTN_MIDDLE':'Нажатие колёсика','BTN_SIDE':'Назад','BTN_EXTRA':'Вперёд'}
                label=self.tr('Нажать' if token.startswith('+') else 'Отпустить' if token.startswith('-') else 'Нажать и отпустить')+' '+(self.tr(mouse[name]) if name in mouse else friendly(token).split(' ',1)[-1])
            rows.append({'index':i,'token':token,'label':label})
        return rows
    @Property(str,notify=changed)
    def currentAssignment(self):
        from operations import same
        action=self._button_data().get('action')
        for item in self.assignments:
            if same(item['value'],action):return item['label']
        if isinstance(action,list) and action:
            if action[0]=='button' and len(action)>1:return self.tr('Кнопка')+' '+str(action[1])
            if action[0]=='key' and len(action)>1:return self.tr('Клавиша')+' '+str(action[1]).removeprefix('KEY_')
            if action[0]=='macro':return self.tr('Макрос')
        return display(action)
    @Property(int,notify=changed)
    def assignmentIndex(self):
        state=self._macro_states.get(self._macro_key(),{})
        value=state.get('choices',{}).get(str(self._button),self._button_data().get('action'))
        return next((i for i,a in enumerate(self.assignments) if a['value']==value),-1)
    @Property(bool,notify=changed)
    def macroConflict(self):return self._macro_conflict
    @Property(bool,notify=changed)
    def macroSupported(self):return bool(self._button_data().get('macroSupported'))
    @Property(bool,notify=changed)
    def macroCaptureAvailable(self):return self.macroSupported or self.eweadnEditor
    @Property(bool,notify=changed)
    def recording(self):return self._recording
    @Property(int,notify=changed)
    def dirtyCount(self):
        if self.g515Editor and self._section=='freestyle':
            return sum(not same(self._desired(f)[0],f.observed) for f in self._g515 if f.group=='freestyle')
        if self.aceEditor and self._section=='keys':return sum(not same(self._desired(f)[0],f.observed) for f in self._key_controls)
        if self.aceEditor and self._section=='key_assignments':return sum(not same(self._desired(f)[0],f.observed) for f in self._ace_remaps)
        if self.aceEditor and self._section=='advanced_keys':return sum(not same(self._desired(f)[0],f.observed) for f in self._ace_advanced_controls)
        if self.aceEditor and self._section=='lighting':return sum(not same(self._desired(f)[0],f.observed) for f in self._controls if f.group=='lighting' and self._dock_applicable(f))
        return sum(row.get('dirty',False) for row in self.fields._rows)

    def bind(self,manager,device,reload=False):
        self._manager=manager
        new_binding=binding(device) if device and device.connected is True else None
        different=new_binding!=self._binding
        if different:self.invalidate()
        if different and self.device:self._device_messages[self.device.id]=(self._message,self._result)
        self.device=device;self._binding=new_binding
        if different:
            self._library_selected='';self._library_name=''
            self._ace_binding_cap=None;self._ace_binding_profile=None;self._ace_remaps=[]
            self._ace_advanced_cap=None;self._ace_advanced_profile=None;self._ace_advanced_controls=[]
            self._ace_color_cap=None;self._ace_color_profile=None
            self._state_error=''
            self._ratbag=None;self._buttons=[];self._controls=[];self._key_controls=[];self._g515=[]
            self._g515_target='G515'
            self._ewe_state=None
            if device:
                self._message,self._result=self._device_messages.get(device.id,('',''))
                self._section=self._sections.get(device.id,'pointer');self._key=self._keys.get(device.id,'50');self._button=self._button_selection.get(device.id,0)
        if not self.available:self._message=self.tr('Устройство сейчас недоступно');self._render();return
        self._build()
        if device.faults and not self._controls:
            from control_service import fault_message
            self._message=fault_message(device.faults[0]);self.changed.emit()
        if (different or reload) and ('ratbagctl' in device.backends or 'eweadn' in device.backends or device.kind=='keyboard' and 'G515' in device.name):self.reload()

    def invalidate(self):
        was_busy=self._busy
        self.stopRecording();self.epoch.invalidate();self._busy=False
        self._state_epoch.invalidate();self._state_timer.stop()
        if was_busy:self._message=self.tr('Операция прервана. Проверь состояние устройства перед повторным применением.')
        self._result='cancelled' if was_busy else '';self.changed.emit()

    def _build(self):
        if not self.device:return
        if self.aceEditor and self._ace_color_cap and self._ace_scope()[1]!=self._ace_color_profile:
            self.device.capabilities=[c for c in self.device.capabilities if c.backend!='mchose-ace68' or c.name!='key_lighting']
            self._ace_color_cap=None;self._ace_color_profile=None
        if self.aceEditor and self._ace_color_cap:
            self.device.capabilities=[c for c in self.device.capabilities if c.backend!='mchose-ace68' or c.name!='key_lighting']+[self._ace_color_cap]
        if self.aceEditor and self._ace_advanced_cap and self._ace_scope()[1]!=self._ace_advanced_profile:
            self.device.capabilities=[c for c in self.device.capabilities if c.backend!='mchose-ace68' or c.name!='advanced_keys']
            self._ace_advanced_cap=None;self._ace_advanced_profile=None
        if self.aceEditor and self._ace_advanced_cap:
            self.device.capabilities=[c for c in self.device.capabilities if c.backend!='mchose-ace68' or c.name!='advanced_keys']+[self._ace_advanced_cap]
            prefix=f'ace68:{self.device.id}:profile:{self._ace_scope()[1]}:advanced:'
            identifiers=set(self._ace_advanced_cap.value)
            identifiers.update(key[len(prefix):] for key in set(self._pending)|set(self.store.values) if key.startswith(prefix))
            self._ace_advanced_controls=[self._advanced_control(identifier) for identifier in sorted(identifiers)]
        else:self._ace_advanced_controls=[]
        if self.aceEditor and self._ace_binding_cap and self._ace_scope()[1]!=self._ace_binding_profile:
            self.device.capabilities=[c for c in self.device.capabilities if c.backend!='mchose-ace68' or c.name!='key_remap']
            self._ace_binding_cap=None;self._ace_binding_profile=None
        if self.aceEditor and self._ace_binding_cap and self._ace_scope()[1]==self._ace_binding_profile:
            self.device.capabilities=[c for c in self.device.capabilities if c.backend!='mchose-ace68' or c.name!='key_remap']+[self._ace_binding_cap]
        if self.aceEditor and self._ace_rgb_owned():
            for cap in self.device.capabilities:
                if cap.backend=='mchose-ace68' and cap.name in ('lighting','lighting_mode','brightness','lighting_speed','lighting_palette','lighting_direction','key_lighting'):cap.writable=False
        self._controls=capability_controls(self.device)
        if self.aceEditor and self._ace_color_cap:
            from control_service import Control
            cap=self._ace_color_cap;profile=self._ace_color_profile
            self._controls.extend(Control('ace:color:'+key,'Цвет выбранных клавиш','lighting',deepcopy(value),
                f'ace68:{self.device.id}:profile:{profile}:color:{key}','mchose-ace68','color',source=cap.source,
                writable=cap.writable,factory=lambda v,k=key,p=cap.plan:p({k:v}),capability='key_lighting',
                profile=profile,key_index=key,batch_factory=cap.plan) for key,value in cap.value.items())
        self._controls+=self._g515
        if self.eweadnEditor:
            self._buttons=[{'index':i,'action':[],'macroSupported':False} for i in range(5)]
            self._load_macro()
        if self._ratbag:
            controls,self._buttons=ratbag_controls(self.device,self._ratbag);self._controls+=controls
            if self._buttons and self._button not in [b['index'] for b in self._buttons]:self._button=self._buttons[0]['index']
            self._load_macro()
        if self.aceEditor:
            self._key_controls=[field for key in keyboard_keys() for field in key_controls(self.device,key['id'])]
            self._ace_remaps=ace_binding_controls(self.device)
        options=[item['id'] for item in self.sections]
        if self._section not in options:self._section=options[0] if options else 'advanced'
        self._render()

    @Slot()
    def reload(self):
        if not self.available or self._busy:return
        if self.eweadnEditor:
            targets=self.device.targets.get('eweadn',[])
            if len(targets)!=1 or self.simulation and self.runner is None:return
            target=targets[0];expected=self._binding;token=self.epoch.token()
            def read_eweadn():
                import json
                from backend import run
                self._guard(expected,token)
                value=json.loads((self.runner or run)(['logi-sdk','eweadn','read',target]))
                self._guard(expected,token);return value
            self._submit('eweadn-read',read_eweadn);return
        if self.aceEditor:
            self._read_ace('advanced' if self._ace_advanced_cap or self._section=='advanced_keys' else 'bindings');return
        if self.device and is_k7_ultra(self.device):
            targets=self.device.targets.get('mchose',[])
            if len(targets)!=1:self._message=self.tr('Устройство сейчас недоступно');self.changed.emit();return
            expected=self._binding;token=self.epoch.token();target=targets[0]
            self._submit('mchose-read',lambda:self._read_mchose(target,expected,token));return
        if self.g515Editor:
            if self.simulation and self.keyboard_reader is None:return
            peers=[d for d in self._manager.devices if d.kind=='keyboard' and d.connected is True and 'G515' in d.name]
            if len(peers)!=1:self._message=self.tr('Устройство сейчас недоступно');self.changed.emit();return
            name=self.device.name
            def read_keyboard():
                if self.keyboard_reader:return self.keyboard_reader()
                from backend import saved_keyboard
                from g515_adapter import read_snapshot
                cached=saved_keyboard()
                target=cached.get('_NAME') or ('G515 LS TKL' if 'LS TKL' in name else 'G515')
                return read_snapshot(target,runner=self.runner,cache=cached)
            self._submit('g515',read_keyboard);return
        if 'ratbagctl' not in self.device.backends:self.owner.refresh();return
        targets=self.device.targets.get('ratbagctl',[])
        if len(targets)!=1:self._message=self.tr('Устройство сейчас недоступно');self.changed.emit();return
        target=targets[0]
        def read():
            from backend import read_mouse
            if self.reader:return self.reader(target)
            if self.simulation and self.runner is None:raise ValueError('Simulation ratbag transport is unavailable')
            return read_mouse(target,runner=self.runner)
        self._submit('read',read)

    def _read_mchose(self,target,expected,token):
        import json
        from backend import run
        self._guard(expected,token)
        if self.simulation and self.runner is None:raise ValueError('Simulation MCHOSE transport is unavailable')
        value=json.loads((self.runner or run)(['logi-sdk','mchose','read',target]))
        self._guard(expected,token)
        if (not isinstance(value,dict) or not isinstance(value.get('raw'),list) or
                type(value.get('profiles')) is not int or not 0<=value['profiles']<=2 or
                type(value.get('stage')) is not int or not 0<=value['stage']<6):
            raise ValueError('Invalid MCHOSE configuration read')
        return value

    def _can_observe(self):
        return (not self._closed and not self.simulation and self._observing and self.available
                and (is_k7_ultra(self.device) and len(self.device.targets.get('mchose',[]))==1 or
                     self.g502Editor and len(self.device.targets.get('ratbagctl',[]))==1 or
                     self.eweadnEditor and len(self.device.targets.get('eweadn',[]))==1))

    def _schedule_state(self,delay=5000):
        if not self._can_observe():self._state_timer.stop();return
        if self.g502Editor and delay==5000:delay=10000
        if self.eweadnEditor and delay==5000:delay=15000
        if not self._state_busy and not self._busy and not self._state_timer.isActive():
            self._state_timer.start(15000 if self._state_error else delay)

    def _poll_state(self):
        if not self._can_observe():return
        if self._state_busy or self._busy or self._recording or any(getattr(self.owner,name,False) is True for name in ('_busy','_battery_busy')) or any(
                getattr(getattr(self.owner,name,None),'busy',False) is True for name in ('_backups','_audio')):
            self._schedule_state(1000);return
        ratbag=self.g502Editor
        eweadn=self.eweadnEditor
        target=self.device.targets['ratbagctl' if ratbag else 'eweadn' if eweadn else 'mchose'][0];expected=self._binding;token=self._state_epoch.token()
        self._state_busy=True
        def read():
            context=CURRENT_CANCEL.set(token)
            try:
                if ratbag:
                    from backend import read_mouse
                    self._guard(expected,token)
                    result=self.reader(target) if self.reader else read_mouse(target,runner=self.runner)
                    self._guard(expected,token)
                    return {'ratbag_state':result}
                if eweadn:
                    import json
                    from backend import run
                    self._guard(expected,token)
                    result=json.loads((self.runner or run)(['logi-sdk','eweadn','read',target]))
                    self._guard(expected,token);return {'eweadn_state':result}
                return self._read_mchose(target,expected,token)
            finally:CURRENT_CANCEL.reset(context)
        future=self.pool.submit(read)
        def done(result):
            if self._closed:return
            try:value,error=result.result(),None
            except Exception as exc:value,error=None,exc
            try:self._stateReady.emit(value,error,token)
            except RuntimeError:pass
        future.add_done_callback(done)

    @Slot(object,object,object)
    def _accept_state(self,value,error,token):
        if self._closed:return
        self._state_busy=False
        if not token.is_set() and self._can_observe():
            if error:
                from control_service import fault_message
                self._state_error=fault_message(error)
                self._render()
            else:
                if 'eweadn_state' in value:
                    from eweadn_adapter import capabilities
                    observed=value['eweadn_state'];was_error=bool(self._state_error);self._state_error=''
                    if not same(self._ewe_state,observed):
                        self._ewe_state=observed
                        self.device.capabilities=[c for c in self.device.capabilities if c.backend!='eweadn']+capabilities(self.device.targets['eweadn'][0],observed)
                        if hasattr(self.owner,'_refresh_artwork_row'):self.owner._refresh_artwork_row(self.device)
                        self._build()
                    elif was_error:self._render()
                    self._schedule_state();return
                if 'ratbag_state' in value:
                    observed=value['ratbag_state']
                    was_error=bool(self._state_error);self._state_error=''
                    changed=not same(self._ratbag,observed)
                    if self._recording and self._ratbag and self._ratbag['active']==observed['active']:
                        self._schedule_state();return
                    if changed:
                        self.stopRecording()
                        if self._ratbag and self._ratbag['active']!=observed['active']:
                            self._library_selected='';self._library_name=''
                        self._ratbag=observed;self._state_error=''
                        from devices import mouse_capabilities,DeviceManager
                        self.device.capabilities=[c for c in self.device.capabilities if c.backend!='ratbagctl']+mouse_capabilities(observed,target=self.device.targets['ratbagctl'][0])
                        DeviceManager.merge([self.device])
                        if hasattr(self.owner,'_refresh_artwork_row'):self.owner._refresh_artwork_row(self.device)
                        self._build()
                    if was_error and not changed:self._render()
                    self._schedule_state();return
                from mchose_adapter import update_observed
                was_error=bool(self._state_error);self._state_error=''
                changed=update_observed(self.device,value)
                if changed or was_error:
                    if hasattr(self.owner,'_refresh_artwork_row'):self.owner._refresh_artwork_row(self.device)
                    self._build()
        self._schedule_state()

    def _submit(self,action,work):
        if self._closed or self._busy:return
        self._state_epoch.invalidate();self._state_timer.stop()
        token=self.epoch.token();self._busy=True
        if action not in ('read','g515') or not self._result:self._message=self.tr('Выполняется…')
        self.changed.emit()
        def run():
            context=CURRENT_CANCEL.set(token)
            try:
                if token.is_set():raise Fault(FaultCode.CANCELLED,'editor','Device binding changed')
                return work()
            finally:CURRENT_CANCEL.reset(context)
        future=self._job=self.pool.submit(run)
        def done(f):
            if self._closed:return
            try:value,error=f.result(),None
            except Exception as exc:value,error=None,exc
            try:self._ready.emit(action,value,error,token)
            except RuntimeError:pass
        future.add_done_callback(done)

    def _desired(self,field):
        if field.draft_key in self._discarded:return field.observed,False
        pending=self._pending.get(field.draft_key)
        base=field.encode(field.observed)
        if pending:encoded,conflict=pending[1],base!=pending[0] and base!=pending[1]
        else:encoded,conflict=self.store.get(field.draft_key,base)
        try:return field.decode(encoded),conflict
        except (ValueError,TypeError,IndexError):return field.observed,True

    def _dock_applicable(self,field):
        if field.backend=='eweadn' and field.capability=='dpi_config':
            key=field.key_index
            if key.startswith(('x','y','color')):
                count=self._field('eweadn:dpi_config:count')
                return bool(count and int(key[5:] if key.startswith('color') else key[1:])<self._desired(count)[0])
        if field.id.startswith('g515:'):
            mode=self._field('g515:effect')
            effect=self._desired(mode)[0] if mode else None
            if field.id=='g515:color':return effect in (1,10)
            if field.id.startswith(('g515:period:','g515:intensity:')):return effect==int(field.id.rsplit(':',1)[1])
        if field.backend=='mchose-ace68' and field.group=='lighting':
            if field.capability=='key_lighting':
                mode=self._field('mchose-ace68:lighting_mode')
                return bool(mode and self._desired(mode)[0]=='Custom')
            option={'lighting':'color','lighting_palette':'color','lighting_speed':'speed','brightness':'brightness','lighting_direction':'direction'}.get(field.capability)
            if option:return self.aceLightOptions.get(option,False)
        if field.capability!='dock_lighting' or field.key_index in ('enabled','mode'):return True
        state=self.dockState
        if not state.get('enabled'):return False
        return (field.key_index=='brightness' or
                field.key_index=='color' and state.get('mode') in ('static','breathing','flash','stars') or
                field.key_index=='duration' and state.get('mode') in ('flash','stars') or
                field.key_index=='direction' and state.get('mode')=='wave')

    def _render(self):
        controls=[f for f in self._key_controls if f.key_index==self._key] if self._section=='keys' else [f for f in self._controls if f.group==self._section]
        if self.g515Editor and self._section=='freestyle':controls=[]
        if self.aceEditor and self._section=='key_assignments':controls=[f for f in self._ace_remaps if f.key_index==str(self._ace_layer)+':'+self._key]
        if self.aceEditor and self._section=='keys' and not self.aceSelectedKeys:controls=[]
        rows=[]
        for field in controls:
            if field.capability=='key_lighting' and field.key_index!=self._key:continue
            if not self._dock_applicable(field):continue
            if field.id.startswith('ratbagctl:led:'):
                parts=field.id.split(':')
                mode=self._field('ratbagctl:led:'+parts[2]+':mode')
                selected=self._desired(mode)[0] if mode else None
                if len(parts)==5 and selected!=parts[4]:continue
                if parts[3]=='color' and selected not in ('on','breathing'):continue
            desired,conflict=self._desired(field)
            writable=field.writable and self.available
            if field.backend=='mchose-ace68' and field.capability=='win_lock':
                mode=self._field('mchose-ace68:keyboard_mode')
                writable=writable and (mode is None or self._desired(mode)[0]!='Mac')
            if field.id.startswith('ratbagctl:led:') and field.id.endswith(':color'):
                mode=self._field(field.id.removesuffix(':color')+':mode')
                writable=writable and mode is not None and self._desired(mode)[0] in ('on','breathing')
            note=self.tr(field.note) if field.note else ''
            if field.id.startswith('ratbagctl:led:') and ':duration:' in field.id and field.observed==0:
                note=self.tr('Нулевая длительность: выбери скорость для анимации.')
            proposed=field.id.startswith('ratbagctl:led:') and len(field.id.split(':'))==5 and field.observed is None
            if field.id.startswith('g515:') and field.source=='unavailable':proposed=True
            label=self.tr('Зона подсветки')+' '+field.label.rsplit(' ',1)[-1] if field.label.startswith('Зона подсветки ') else self.tr(field.label)
            if ' · LED ' in field.label:
                title,number=field.label.rsplit(' · LED ',1);label=self.tr(title)+' · LED '+number
            k7_stage=field.id=='mchose:stage' and self.device and is_k7_ultra(self.device)
            indicator=k7_dpi_indicator(desired) if k7_stage else None
            if k7_stage:
                choice_labels=[]
                for value in field.choices:
                    color=k7_dpi_indicator(value)
                    choice_labels.append(str(value+1)+(' · '+self.tr(color[0]) if color else ''))
            elif field.choice_labels:choice_labels=[self.tr(v) for v in field.choice_labels]
            else:choice_labels=[__import__('control_service').choice_caption(v) for v in field.choices]
            legacy_draft=''
            if field.backend in ('mchose','mchose-ace68') and ':profile:' in field.draft_key:
                old_key=field.draft_key.rsplit(':profile:',1)[0]
                old_pending=self._pending.get(old_key)
                old_saved=self.store.values.get(old_key,{})
                if not isinstance(old_saved,dict):old_saved={}
                old_value=old_pending[1] if old_pending else old_saved.get('desired')
                if old_pending or 'desired' in old_saved:
                    legacy_draft=str(old_value+1) if k7_stage and k7_dpi_indicator(old_value) else display(old_value)
            rows.append({'id':field.id,'label':label,'kind':field.kind if field.writable else 'readonly','value':desired,
                'observed':str(field.observed+1) if k7_stage and k7_dpi_indicator(field.observed) else display(field.observed),
                'source':self.tr({'device':'Прочитано с устройства','backend_cache':'Кэш приложения','local_saved_settings':'Локальные настройки','simulation':'Симуляция','audio_server':'Аудиосистема'}.get(field.source,'Нет данных')),
                'choices':field.choices,'choiceLabels':choice_labels,'indicatorColor':indicator[1] if indicator else '',
                'minimum':field.minimum,'maximum':field.maximum,'step':field.step,'writable':writable,
                'dirty':not same(desired,field.observed),'conflict':conflict,'state':self._states.get(field.draft_key,''),'backend':field.backend,
                'cached':field.source=='backend_cache','stale':not self.available or bool(self._state_error) and field.backend in ('mchose','ratbagctl','eweadn'),'note':note,'proposed':proposed,'legacyDraft':legacy_draft})
            if field.capability=='sensor_config' and field.choice_labels and field.observed in field.choices:
                rows[-1]['observed']=self.tr(field.choice_labels[field.choices.index(field.observed)])
            if field.backend=='mchose-ace68' and field.kind=='choice' and field.observed in field.choices:
                rows[-1]['observed']=choice_labels[field.choices.index(field.observed)]
            if field.id.startswith('g515:') and field.kind=='choice' and field.observed in field.choices:
                rows[-1]['observed']=choice_labels[field.choices.index(field.observed)]
            if self.aceEditor and self._section=='keys':
                peers=[f for f in self._key_controls if f.capability==field.capability and f.key_index in self.aceSelectedKeys]
                desired_values=[self._desired(f)[0] for f in peers]
                observed_values=[f.observed for f in peers]
                mixed=any(not same(v,desired_values[0]) for v in desired_values)
                rows[-1].update(minimum=max(f.minimum for f in peers),maximum=min(f.maximum for f in peers),
                    step=max(f.step for f in peers),writable=all(f.writable for f in peers) and self.available,
                    dirty=any(not same(self._desired(f)[0],f.observed) for f in peers),
                    conflict=any(self._desired(f)[1] for f in peers),mixed=mixed,
                    value=None if mixed else desired_values[0])
                if any(not same(v,observed_values[0]) for v in observed_values):rows[-1]['observed']=self.tr('Разные значения')
        self.fields.update(rows);self.changed.emit()

    def _field(self,ident):return next((f for f in [*self._controls,*self._key_controls,*self._ace_remaps,*self._ace_advanced_controls] if f.id==ident),None)
    @Slot(str,'QVariant')
    def edit(self,ident,value):
        field=self._field(ident)
        if not field or self._busy:return
        if hasattr(value,'toVariant'):value=value.toVariant()
        if field.backend=='mchose-ace68' and field.capability=='win_lock' and value is True:
            mode=self._field('mchose-ace68:keyboard_mode')
            if mode and self._desired(mode)[0]=='Mac':
                self._message=self.tr('Блокировка Win недоступна в режиме Mac.');self.changed.emit();return
        # QML Number is a double even after Math.round(). Convert only exact
        # integral RGB channels at the Qt boundary; Control.validate remains
        # strict for every other caller and rejects fractional/out-of-range RGB.
        if field.kind in ('color','binding','acebinding','ewebinding') and isinstance(value,list):
            value=[int(channel) if type(channel) is float and channel.is_integer() else channel for channel in value]
        try:value=field.validate(value)
        except (ValueError,TypeError):self._message=self.tr('Значение вне допустимого диапазона');self.changed.emit();return
        if field.backend=='mchose' and field.capability=='dpi_config':self._k7_axes.setdefault(self._k7_scope(),self.k7SeparateAxes)
        observed=field.encode(field.observed)
        previous=self._pending.get(field.draft_key)
        if previous is None:
            stored=self.store.values.get(field.draft_key,{})
            if 'base' in stored and 'desired' in stored:previous=(stored['base'],stored['desired'])
        base=previous[0] if previous else observed
        if previous and previous[1]==observed:
            # A new deliberate edit is based on the newly displayed observation,
            # even when the preceding submission was only cache-confirmed.
            base=observed;self.owner._preferences_pool.submit(self.store.discard,field.draft_key)
        self._discarded.discard(field.draft_key)
        self._pending[field.draft_key]=(base,field.encode(value));self._states[field.draft_key]='draft'
        if field.backend=='mchose-ace68' and field.capability=='keyboard_mode' and value=='Mac':
            win=self._field('mchose-ace68:win_lock')
            if win and win.writable:self.edit(win.id,False)
        if field.capability=='dpi_config':
            if field.backend=='eweadn':
                if field.key_index=='count':
                    active=self._field('eweadn:dpi_config:active')
                    if self._desired(active)[0]>=value:self.edit(active.id,value-1)
                if field.key_index.startswith('x') and self._ewe_state and not self._ewe_state['dpi_config']['axes_available']:
                    self.edit('eweadn:dpi_config:y'+field.key_index[1:],value)
            else:
                if field.key_index=='count':
                    active=self._field('mchose:dpi_config:active')
                    if self._desired(active)[0]>=value:self.edit(active.id,value-1)
                if field.key_index.startswith('x') and not self.k7SeparateAxes:
                    self.edit('mchose:dpi_config:y'+field.key_index[1:],value)
        if field.id.startswith('ratbagctl:led:') and field.id.endswith(':mode') and value in ('cycle','breathing'):
            zone=field.id.split(':')[2]
            for parameter,default in (('duration',8000),('brightness',255)):
                companion=self._field('ratbagctl:led:'+zone+':'+parameter+':'+value)
                if companion is None:continue
                current,conflict=self._desired(companion)
                if conflict or type(current) is int and current>0:continue
                self._discarded.discard(companion.draft_key)
                self._pending[companion.draft_key]=(companion.encode(companion.observed),default)
                self._states[companion.draft_key]='draft'
        if ':duration:' in field.id and field.id.startswith('ratbagctl:led:'):
            zone,effect=field.id.split(':')[2],field.id.split(':')[4]
            companion=self._field('ratbagctl:led:'+zone+':brightness:'+effect)
            if companion and self._desired(companion)[0] in (None,0):
                self._discarded.discard(companion.draft_key)
                self._pending[companion.draft_key]=(companion.encode(companion.observed),255)
                self._states[companion.draft_key]='draft'
        self._draft_timer.start()
        if not self._editing_selection:self._render()

    @Slot()
    def flush(self):
        pending=deepcopy(self._pending)
        if pending:self.owner._preferences_pool.submit(lambda:[self.store.edit(k,b,v) for k,(b,v) in pending.items()])

    @Slot(str)
    def setSection(self,key):
        if key not in [s['id'] for s in self.sections]:return
        self.stopRecording();self._section=key
        if self.device:self._sections[self.device.id]=key
        self._render()
        if self.aceEditor and key=='key_assignments' and self._ace_binding_cap is None:self.readAceBindings()
        if self.aceEditor and key=='advanced_keys' and self._ace_advanced_cap is None:self.readAceAdvanced()

    @Slot(str)
    def selectKey(self,index):
        if self._busy or index not in [k['id'] for k in self.keyModel]:return
        self._key=index;self._keys[self.device.id]=index
        if self.aceEditor:self._ace_selections[self._ace_scope()]={index}
        else:self._key_controls=key_controls(self.device,index)
        self._render()

    @Slot()
    def discardGroup(self):
        controls=self._key_controls if self._section=='keys' else [f for f in self._controls if f.group==self._section]
        if self.aceEditor and self._section=='key_assignments':controls=self._ace_remaps
        if self.aceEditor and self._section=='advanced_keys':controls=self._ace_advanced_controls
        for field in controls:
            self._pending.pop(field.draft_key,None);self._states.pop(field.draft_key,None)
            self._discarded.add(field.draft_key)
            self.owner._preferences_pool.submit(self.store.discard,field.draft_key)
        self._render()

    def _guard(self,expected,token):
        if token.is_set():raise Fault(FaultCode.CANCELLED,'editor','Device binding changed')
        device=next((d for d in self._manager.devices if d.id==expected[0]),None) if self._manager else None
        if device is None or device.connected is not True or binding(device)!=expected:raise Fault(FaultCode.DISCONNECTED,'editor','Device binding changed')
        return device

    def _guard_g515(self,expected,token):
        device=self._guard(expected,token)
        peers=[d for d in self._manager.devices if d.kind=='keyboard' and d.connected is True and 'G515' in d.name]
        if len(peers)!=1 or peers[0].id!=device.id:
            raise Fault(FaultCode.DISCONNECTED,'solaar','G515 target is unavailable or ambiguous')
        return device

    def _guard_live_ratbag_profile(self,run,profile):
        # A daemon-only fixture/device keeps the existing daemon guard. Once
        # live onboard evidence was obtained, require it again before writing.
        if not self._ratbag or 'daemon_active' not in self._ratbag:return
        import json,re
        model=re.search(r'Model:\s*(usb:046d:c08b:[0-9a-fA-F]+)',self._ratbag.get('text',''))
        if not model:raise ActiveProfileChanged('Live profile identity unavailable')
        observed=json.loads(run(['logi-sdk','logitech-status','read',model[1]]))
        if observed.get('mode')!='onboard' or observed.get('profile')!=profile:
            raise ActiveProfileChanged('Physical profile changed')

    @Slot()
    def applyGroup(self):
        if not self.available or self._busy:return
        if self._other_write_busy():return
        controls=self._key_controls if self._section=='keys' else [f for f in self._controls if f.group==self._section]
        if self.aceEditor and self._section=='key_assignments':controls=self._ace_remaps
        if self.aceEditor and self._section=='advanced_keys':controls=self._ace_advanced_controls
        pending=[(f,deepcopy(self._desired(f)[0])) for f in controls if not same(self._desired(f)[0],f.observed)]
        pending=[(f,v) for f,v in pending if self._dock_applicable(f)]
        pending=[(f,v) for f,v in pending if not (f.id.startswith('ratbagctl:led:') and f.id.endswith(':color')) or self._desired(self._field(f.id.removesuffix(':color')+':mode'))[0] in ('on','breathing')]
        pending=[(f,v) for f,v in pending if not (f.id.startswith('ratbagctl:led:') and len(f.id.split(':'))==5)
                 or self._desired(self._field('ratbagctl:led:'+f.id.split(':')[2]+':mode'))[0]==f.id.split(':')[4]]
        # Re-activate the selected firmware effect after changing its timing or
        # intensity. Each command is still guarded and serialized individually.
        pending_ids={f.id for f,v in pending}
        for field,value in list(pending):
            parts=field.id.split(':')
            if len(parts)!=5 or parts[0]!='ratbagctl' or parts[1]!='led' or parts[3] not in ('duration','brightness'):continue
            mode=self._field('ratbagctl:led:'+parts[2]+':mode')
            if mode and mode.id not in pending_ids:
                pending.append((mode,deepcopy(self._desired(mode)[0])));pending_ids.add(mode.id)
        def order(pair):
            parts=pair[0].id.split(':')
            if len(parts)<4 or parts[:2]!=['ratbagctl','led']:return (1,0,0)
            mode=self._field('ratbagctl:led:'+parts[2]+':mode')
            dynamic=mode and self._desired(mode)[0] in ('cycle','breathing')
            sequence={'duration':0,'brightness':1,'mode':2,'color':3} if dynamic else {'mode':0,'color':1}
            return (0,int(parts[2]),sequence.get(parts[3],4))
        pending.sort(key=order)
        for field,value in pending:
            if not field.id.startswith('ratbagctl:led:') or not field.id.endswith(':mode') or value not in ('on','breathing'):
                continue
            color=self._field(field.id.removesuffix(':mode')+':color')
            if color and color.observed is None and self._desired(color)[0] is None:
                self._message=self.tr('Выбери цвет для этой зоны перед включением подсветки.')
                self.changed.emit();return
        if not pending:return
        colors=[(f,v) for f,v in pending if f.capability=='key_lighting']
        if colors:pending=colors
        if self.aceEditor and self._section=='advanced_keys' and len(pending)>1:
            pending=pending[:1]
        if any(self._desired(f)[1] for f,v in pending):
            self._message=self.tr('Черновик конфликтует с текущим значением. Отмени его и проверь настройку.');self.changed.emit();return
        if self._section=='buttons' and self.k7Editor:
            actions={f.key_index:self._desired(f)[0] for f in self._controls if f.capability=='button_bindings'}
            if not any(v==[1,0x010000] or k=='0' and v==[0,0] for k,v in actions.items()):
                self._message=self.tr('Сохрани хотя бы одну кнопку с левым щелчком.');self.changed.emit();return
        switches=[(f,v) for f,v in pending if (f.capability in ('stage','profiles','lighting_mode') or f.id in ('ratbagctl:stage','ratbagctl:profiles'))
                  and not (f.backend=='mchose-ace68' and f.capability=='lighting_mode')]
        if len(pending)>1 and switches:pending=[switches[0]]
        self.flush();expected=self._binding;token=self.epoch.token()
        def write():
            results=[]
            try:
                mappings=[(f,v) for f,v in pending if f.backend=='mchose-ace68' and f.capability in ('key_remap','advanced_keys','key_lighting')]
                if mappings:
                    if len(mappings)!=len(pending):raise ValueError('Apply key mappings separately')
                    device=self._guard(expected,token);self._manager.route(device.id,mappings[0][0].capability,'mchose-ace68')
                    def run_mapping(args,**kwargs):
                        live=self._guard(expected,token);self._guard_ace_rgb(args,live);self._manager.guard_command(args)
                        if self.simulation and self.runner is None:raise ValueError('No simulation keyboard transport')
                        from backend import run
                        return (self.runner or run)(args,**kwargs)
                    changes={f.key_index:f.validate(v) for f,v in mappings}
                    result=perform(mappings[0][0].batch_factory(changes),run_mapping,token)
                    return [(f,v,result) for f,v in mappings]
                ace=[(f,v) for f,v in pending if f.backend=='mchose-ace68' and f.key_index]
                if ace:
                    if len(ace)!=len(pending):raise ValueError('Apply selected keys separately')
                    from ace68_adapter import setting_plan
                    from ace68_protocol import validate_key_value,KEY_FIELDS
                    device=self._guard(expected,token)
                    details=next(c.value for c in device.capabilities if c.backend=='mchose-ace68' and c.name=='key_details')
                    for field,value in ace:validate_key_value({'key_details':details},field.capability,field.key_index,field.validate(value))
                    def run_ace(args,**kwargs):
                        self._guard(expected,token);self._manager.guard_command(args)
                        if self.simulation and self.runner is None:raise ValueError('No simulation keyboard transport')
                        from backend import run
                        return (self.runner or run)(args,**kwargs)
                    for parameter in KEY_FIELDS:
                        fields=[(f,v) for f,v in ace if f.capability==parameter]
                        if not fields:continue
                        self._manager.route(device.id,parameter,'mchose-ace68')
                        values={f.key_index:v for f,v in fields}
                        result=perform(setting_plan(device.targets['mchose-ace68'][0],parameter,values,fields[0][0].profile),run_ace,token)
                        results.extend((f,v,result) for f,v in fields)
                        if not result.accepted:break
                    return results
                batches={(f.backend,f.capability) for f,v in pending if f.batch_factory is not None}
                for backend,capability in sorted(batches):
                    batch=[(f,v) for f,v in pending if f.backend==backend and f.capability==capability and f.batch_factory is not None]
                    device=self._guard(expected,token)
                    self._manager.route(device.id,capability,backend)
                    changes={field.key_index:field.validate(value) for field,value in batch}
                    def run_batch(args,**kwargs):
                        self._guard(expected,token);self._manager.guard_command(args)
                        from backend import run
                        if self.simulation and self.runner is None:raise ValueError('No simulation MCHOSE transport')
                        return (self.runner or run)(args,**kwargs)
                    result=perform(batch[0][0].batch_factory(changes),run_batch,token)
                    results.extend((field,value,result) for field,value in batch)
                    if not result.accepted:return results
                lighting=[(f,v) for f,v in pending if f.id in ('g515:effect','g515:color')]
                lighting+=[(f,v) for f,v in pending if f.id.startswith(('g515:period:','g515:intensity:'))]
                perkey=[(f,v) for f,v in pending if f.id.startswith('g515:key:')]
                if lighting or perkey:
                    from control_service import g515_lighting_plans
                    effect=self._desired(self._field('g515:effect'))[0];color=self._desired(self._field('g515:color'))[0]
                    period=self._field('g515:period:'+str(effect));intensity=self._field('g515:intensity:'+str(effect))
                    def run_g515(args,**kwargs):
                        self._guard_g515(expected,token)
                        from backend import run
                        if self.simulation and self.runner is None:raise ValueError('No simulation G515 transport')
                        self._manager.guard_command(args);return (self.runner or run)(args,**kwargs)
                    # Freestyle explicitly claims static RGB on Apply only.
                    # No key painting or page navigation sends hardware writes.
                    for plan in g515_lighting_plans(1 if perkey else effect,color,
                            self._desired(period)[0] if period else 3000,self._desired(intensity)[0] if intensity else 100,target=self._g515_target):
                        result=perform(plan,run_g515,token)
                        results.append((None,None,result))
                        if not result.accepted:return results
                    results.extend((f,v,result) for f,v in lighting)
                    for field,value in pending:
                        if (field,value) in lighting:continue
                        for plan in field.plans(value):
                            result=perform(plan,run_g515,token);results.append((field,value,result))
                            if not result.accepted:return results
                    return results
                for field,value in pending:
                    if field.batch_factory is not None:continue
                    device=self._guard(expected,token)
                    if field.profile is not None and field.backend=='mchose-ace68':
                        profile=next(c.value for c in device.capabilities if c.backend==field.backend and c.name=='profiles')
                        if profile!=field.profile:raise ActiveProfileChanged('Profile changed')
                    if field.capability and field.backend!='simulation':
                        cap=self._manager.route(device.id,field.capability,field.backend)
                        if field.key_index and field.backend=='mchose-ace68':
                            from ace68_protocol import validate_key_value
                            details=next(c.value for c in device.capabilities if c.name=='key_details')
                            validate_key_value({'key_details':details},field.capability,field.key_index,value)
                        from dataclasses import replace
                        # Keep the MCHOSE context captured by this draft even if
                        # discovery replaces the current capability meanwhile.
                        if field.backend!='mchose':
                            field=replace(field,factory=(lambda v,c=cap,k=field.key_index:c.plan({k:v})) if field.key_index else cap.plan)
                    if self.simulation and field.backend=='simulation':
                        result=self.owner._simulation_adapter.apply(device.target,field.capability,value)
                        results.append((field,value,result));
                        if not result.accepted:break
                        continue
                    def run(args,**kwargs):
                        live=self._guard(expected,token);self._guard_ace_rgb(args,live);self._manager.guard_command(args)
                        if field.id.startswith('g515:'):self._guard_g515(expected,token)
                        if self.simulation and self.runner is None:raise ValueError('Simulation transport is unavailable')
                        from backend import run as real_run
                        return (self.runner or real_run)(args,**kwargs)
                    if field.backend=='ratbagctl' and field.profile is not None and field.id!='ratbagctl:profiles':
                        from operations import first_number
                        target=device.targets['ratbagctl'][0]
                        self._guard_live_ratbag_profile(run,field.profile)
                        if first_number(run(['ratbagctl',target,'profile','active','get']))!=field.profile:raise ActiveProfileChanged('Profile changed')
                    for plan in field.plans(value):
                        result=perform(plan,run,token);results.append((field,value,result))
                        if not result.accepted:break
                    if not result.accepted:break
            except ActiveProfileChanged:
                raise
            except Exception as error:
                from diagnostics import fault_for
                from operations import Result, fault_state
                fault=fault_for(error)
                results.append((None,None,Result(fault_state(fault),fault.component,fault=fault)))
            return results
        self._submit('apply',write)

    @Slot(str,object,object,object)
    def _accept(self,action,value,error,token):
        if self._closed or token.is_set():return
        self._busy=False
        if error:
            if isinstance(error,ActiveProfileChanged):
                self._message=self.tr('Профиль устройства изменился. Обновляю настройки; черновик сохранён.')
                self._result='stale';self.changed.emit();self.reload();return
            from control_service import fault_message
            self._message=fault_message(error);self._result='error'
            if action=='eweadn-read':self._state_error=self._message;self._render()
            else:self.changed.emit()
            return
        if action=='read':
            self._ratbag=value
            from devices import mouse_capabilities
            if self.device:
                self.device.capabilities=[c for c in self.device.capabilities if c.backend!='ratbagctl']+mouse_capabilities(value,self.device.targets['ratbagctl'][0])
                from devices import DeviceManager
                DeviceManager.merge(self._manager.devices)
                if hasattr(self.owner,'_refresh_artwork_row'):self.owner._refresh_artwork_row(self.device)
            if not self._result:self._message=''
            self._build();return
        if action=='mchose-read':
            from mchose_adapter import update_observed
            self._state_error=''
            update_observed(self.device,value)
            if hasattr(self.owner,'_refresh_artwork_row'):self.owner._refresh_artwork_row(self.device)
            self._message='Настройки прочитаны с устройства.'
            self._build();return
        if action=='g515':
            from control_service import g515_controls,fault_message
            self._g515_target=value['target']
            self._g515=g515_controls(value['settings'],value['saved'],self.device.id,value['target'],value['sources'])
            if value['errors']:
                self._message=self.tr('Часть настроек Solaar недоступна; показаны доступные данные.')+' '+fault_message(value['errors'][0])
            elif value['reachable']:self._message=self.tr('Настройки получены через Solaar. Цвета и таймеры могут быть кэшированными.')
            self._build();return
        if action=='eweadn-read':
            from eweadn_adapter import capabilities
            self._state_error=''
            self._ewe_state=value;self.device.name=value['name']
            self.device.capabilities=[c for c in self.device.capabilities if c.backend!='eweadn']+capabilities(self.device.targets['eweadn'][0],value)
            if hasattr(self.owner,'_refresh_artwork_row'):self.owner._refresh_artwork_row(self.device)
            self._message=self.tr('Настройки прочитаны с устройства.');self._build();return
        if action in ('ace-bindings-read','ace-advanced-read','ace-colors-read'):
            from ace68_adapter import binding_capability,advanced_capability,color_capability,setting_plan
            from devices import now
            target=self.device.targets['mchose-ace68'][0]
            for cap in self.device.capabilities:
                if cap.backend=='mchose-ace68' and cap.name in value and cap.name not in ('key_remap','advanced_keys','key_lighting'):
                    cap.value=deepcopy(value[cap.name]);cap.source='device';cap.observed_at=now()
                    from ace68_protocol import KEY_FIELDS
                    writable=cap.name in ('profiles','polling_rate','brightness','lighting_mode','lighting_speed','lighting_palette','lighting_direction','lighting','win_lock','stability_mode','key_debounce','adaptive_calibration','keyboard_mode',*KEY_FIELDS)
                    cap.writable=writable and value.get('firmware_version')=='121'
                    if cap.name=='win_lock' and value.get('keyboard_mode')=='Mac':cap.writable=False
                    if cap.name=='key_debounce' and type(value.get(cap.name)) is not bool:cap.writable=False
                    if not cap.writable:cap.plan=None
                    if cap.writable:cap.plan=lambda desired,f=cap.name,p=value['profiles']:setting_plan(target,f,desired,p)
            if 'raw_bindings' in value:
                self._ace_binding_cap=binding_capability(target,value);self._ace_binding_profile=value['profiles']
            if action=='ace-colors-read':
                self._ace_color_cap=color_capability(target,value);self._ace_color_profile=value['profiles']
            if action=='ace-advanced-read':
                self._ace_advanced_cap=advanced_capability(target,value);self._ace_advanced_profile=value['profiles']
            elif action=='ace-bindings-read':
                self._ace_advanced_cap=None;self._ace_advanced_profile=None
                self.device.capabilities=[c for c in self.device.capabilities if c.backend!='mchose-ace68' or c.name!='advanced_keys']
            self._message='Настройки прочитаны с устройства.'
            self._build();return
        if action in ('apply','button','profile-sync'):
            for field,desired,result in value:
                if field:
                    self._states[field.draft_key]=result.state.value
                    if result.actual is not None:
                        observed=deepcopy(result.actual.get(field.key_index,field.observed) if field.key_index and isinstance(result.actual,dict) else result.actual)
                        if field.kind=='color':
                            from control_service import rgb_value
                            observed=rgb_value(observed)
                        field.observed=observed
                        current_field=self._field(field.id)
                        if current_field:current_field.observed=observed;current_field.source=result.source
                        if self.device and field.capability:
                            from devices import now
                            for cap in self.device.capabilities:
                                if cap.backend==field.backend and cap.name==field.capability:
                                    cap.value={**cap.value,**result.actual} if isinstance(cap.value,dict) and isinstance(result.actual,dict) else result.actual
                                    cap.source=result.source;cap.observed_at=now();cap.last_operation={'state':result.state.value,'source':result.source,'at':now()}
                    if result.state==State.CONFIRMED:
                        self._discarded.add(field.draft_key)
                        self._pending.pop(field.draft_key,None);self.owner._preferences_pool.submit(self.store.submitted,field.draft_key,'confirmed')
                    elif result.accepted:self.owner._preferences_pool.submit(self.store.submitted,field.draft_key,result.state.value)
                self._result=result.state.value
                if result.state==State.DISCONNECTED and self.device:self.device.connected=False
                from control_service import editor_result_message
                self._message=editor_result_message(result)
            if action=='button' and value and value[-1][2].accepted:
                self.owner._preferences_pool.submit(self.store.submitted,self._macro_key(),value[-1][2].state.value)
            if len(value)>1 and not value[-1][2].accepted and any(r.accepted for f,v,r in value[:-1]):
                self._message=self.tr('Некоторые изменения применены. Проверь результат.')+' '+self._message
            self._render()
            if value and all(r.accepted for f,v,r in value):
                if all(f and f.capability=='advanced_keys' and f.backend=='mchose-ace68' for f,v,r in value):self.readAceAdvanced()
                elif all(f and f.capability=='key_lighting' and f.backend=='mchose-ace68' for f,v,r in value):self.readAceColors()
                elif all(f and f.capability=='key_remap' and f.backend=='mchose-ace68' for f,v,r in value):self.readAceBindings()
                elif all(f and f.backend in ('mchose','eweadn') for f,v,r in value):self.reload()
                elif self._ratbag:
                    if all(f and f.id.startswith('ratbagctl:led:') for f,v,r in value):
                        self._update_led_cache(value)
                    else:self.reload()
                else:self.owner.refresh()
            elif value and value[-1][2].state==State.DISCONNECTED:self.owner.refresh()

    def _update_led_cache(self,results):
        """Refresh only affected daemon-cache fields; never claim device proof."""
        if not self._ratbag:return
        active=next((p for p in self._ratbag['profiles'] if p['index']==self._ratbag['active']),None)
        if active is None:return
        for field,requested,result in results:
            if result.actual is None:continue
            parts=field.id.split(':')
            led=next((item for item in active['leds'] if item['index']==int(parts[2])),None)
            if led is None:continue
            led[parts[3]]=result.actual
        self._build()

    def _button_data(self):return next((b for b in self._buttons if b['index']==self._button),{})
    def _macro_key(self):
        if self.eweadnEditor:
            profile=next((c.value for c in self.device.capabilities if c.backend=='eweadn' and c.name=='profiles'),None)
            return 'eweadn:'+self.device.id+':profile:'+str(profile)+'/visual-editor'
        if not self.device or not self._ratbag:return ''
        return 'mouse:'+self.device.targets['ratbagctl'][0]+':profile:'+str(self._ratbag['active'])+'/visual-editor'
    def _load_macro(self):
        from mouse_models import MacroDraft
        if self.eweadnEditor:
            state,unused=self.store.get(self._macro_key(),[])
            state=self._macro_states.setdefault(self._macro_key(),state if isinstance(state,dict) else {'tokens':{}})
            self._macro=MacroDraft(tokens=list(state.get('tokens',{}).get(str(self._button),[])))
            self._macro_conflict=False;return
        key=self._macro_key();active=next((p for p in self._ratbag['profiles'] if p['index']==self._ratbag['active']),{})
        baseline=[{'index':b['index'],'action':b['action'],'macro':b['macro']} for b in active.get('buttons',[])]
        state,conflict=self.store.get(key,baseline)
        state=self._macro_states.setdefault(key,state if isinstance(state,dict) else {'dirty':False,'tokens':{},'choices':{}})
        current=self._button_data().get('action',[])
        self._macro=MacroDraft(tokens=list(state.get('tokens',{}).get(str(self._button),current[1:] if current[:1]==['macro'] else [])))
        stored=self.store.values.get(key,{})
        original=next((b for b in stored.get('base',[]) if isinstance(b,dict) and b.get('index')==self._button),None) if isinstance(stored.get('base'),list) else None
        from operations import read_action
        original_action=read_action(('macro ' if original.get('macro') else '')+original['action']) if original else current
        desired=state.get('choices',{}).get(str(self._button)) or ['macro',*self._macro.tokens]
        self._macro_conflict=conflict and original_action!=current and not same(desired,current)
        if self._macro_conflict:self._message=self.tr('Черновик сохранён, но состояние устройства изменилось. Проверь значения или загрузи текущее.')
    def _save_macro(self):
        if not self._macro:return
        key=self._macro_key();state=self._macro_states.setdefault(key,{'dirty':True,'tokens':{},'choices':{}})
        state.setdefault('tokens',{})[str(self._button)]=list(self._macro.tokens);state['selected']=self._button;state.setdefault('choices',{})[str(self._button)]=None
        active=next(p for p in self._ratbag['profiles'] if p['index']==self._ratbag['active']) if self._ratbag else None
        baseline=[{'index':b['index'],'action':b['action'],'macro':b['macro']} for b in active['buttons']] if active else []
        saved=deepcopy(state);self.owner._preferences_pool.submit(self.store.edit,key,baseline,saved);self.changed.emit()
    @Slot(int)
    def selectButton(self,index):
        if self._busy or index not in [b['index'] for b in self._buttons]:return
        self.stopRecording()
        if index!=self._button:
            if self._library_selected:self.saveLibraryMacro(self._library_name)
            self._library_selected='';self._library_name=''
        self._button=index;self._button_selection[self.device.id]=index;self._load_macro();self.changed.emit()
    @Slot(bool)
    def setRecording(self,enabled):
        if not enabled:self.stopRecording();return
        self._recording=bool(self.macroCaptureAvailable and not self._busy)
        self._capture_time=None
        if self._recording and QCoreApplication.instance():QCoreApplication.instance().installEventFilter(self)
        self.changed.emit()
    @Slot()
    def stopRecording(self):
        if self._recording:
            self._recording=False
            if QCoreApplication.instance():QCoreApplication.instance().removeEventFilter(self)
            if self._macro:
                for key in list(self._macro.held):self._macro.release(key)
                self._save_macro()
                if self._library_selected:self.saveLibraryMacro(self._library_name)
            if self._capture_window:
                try:self._capture_window.removeEventFilter(self)
                except RuntimeError:pass  # Window destruction also ends capture.
            self._capture_window=None;self._capture_item=None;self._capture_time=None
            self.changed.emit()
    @staticmethod
    def _event_name(event):
        from mouse_models import scan_key
        from PySide6.QtGui import QGuiApplication
        app=QCoreApplication.instance()
        physical=scan_key(event.nativeScanCode(),QGuiApplication.platformName() if isinstance(app,QGuiApplication) else '')
        if physical:return physical
        native={0xffe2:'Shift_R',0xffe4:'Control_R',0xffea:'Alt_R',0xffec:'Super_R',0xfe03:'Alt_R'}
        if event.nativeVirtualKey() in native:return native[event.nativeVirtualKey()]
        key=event.key()
        if Qt.Key.Key_A<=key<=Qt.Key.Key_Z or Qt.Key.Key_0<=key<=Qt.Key.Key_9:return chr(key)
        if Qt.Key.Key_F1<=key<=Qt.Key.Key_F24:return 'F'+str(key-Qt.Key.Key_F1+1)
        names={Qt.Key.Key_Control:'Control_L',Qt.Key.Key_Shift:'Shift_L',Qt.Key.Key_Alt:'Alt_L',Qt.Key.Key_Meta:'Super_L',Qt.Key.Key_Return:'Return',Qt.Key.Key_Enter:'Return',Qt.Key.Key_Escape:'Escape',Qt.Key.Key_Space:'space',Qt.Key.Key_Tab:'Tab',Qt.Key.Key_Backspace:'BackSpace',Qt.Key.Key_Left:'Left',Qt.Key.Key_Right:'Right',Qt.Key.Key_Up:'Up',Qt.Key.Key_Down:'Down',Qt.Key.Key_Delete:'Delete',Qt.Key.Key_Insert:'Insert',Qt.Key.Key_Home:'Home',Qt.Key.Key_End:'End',Qt.Key.Key_PageUp:'Page_Up',Qt.Key.Key_PageDown:'Page_Down'}
        return names.get(key,event.text())
    def eventFilter(self,watched,event):
        if not self._recording:return False
        if event.type()==QEvent.Type.ApplicationDeactivate:self.stopRecording();return False
        if event.type() not in (QEvent.Type.ShortcutOverride,QEvent.Type.KeyPress,QEvent.Type.KeyRelease,
                                QEvent.Type.MouseButtonPress,QEvent.Type.MouseButtonRelease,QEvent.Type.MouseButtonDblClick):return False
        from PySide6.QtGui import QGuiApplication,QWindow
        window=watched if isinstance(watched,QWindow) else watched.window() if callable(getattr(watched,'window',None)) else None
        capture=self._capture_window or QGuiApplication.focusWindow()
        if window is not capture:return False
        if event.type()==QEvent.Type.ShortcutOverride:event.accept();return True
        if event.type() in (QEvent.Type.KeyPress,QEvent.Type.KeyRelease):
            if not event.isAutoRepeat():self.recordKey(self._event_name(event),event.type()==QEvent.Type.KeyPress)
            event.accept();return True
        if self._capture_item and event.type() in (QEvent.Type.MouseButtonPress,QEvent.Type.MouseButtonRelease,QEvent.Type.MouseButtonDblClick):
            point=self._capture_item.mapFromGlobal(event.globalPosition())
            if self._capture_item.contains(point):
                names={Qt.MouseButton.LeftButton:'BTN_LEFT',Qt.MouseButton.RightButton:'BTN_RIGHT',Qt.MouseButton.MiddleButton:'BTN_MIDDLE',Qt.MouseButton.BackButton:'BTN_SIDE',Qt.MouseButton.ForwardButton:'BTN_EXTRA'}
                name=names.get(event.button())
                if name:self._record_event(name,event.type()!=QEvent.Type.MouseButtonRelease)
                event.accept();return True
        return False
    @Slot(str,bool)
    def recordKey(self,name,pressed):
        if not self._recording or not self._macro:return
        from mouse_models import linux_key
        name={'-':'minus','=':'equal',',':'comma','.':'period','/':'slash',';':'semicolon',"'":'apostrophe','[':'bracketleft',']':'bracketright','\\':'backslash','`':'grave'}.get(name,name)
        key=linux_key(name)
        if key:self._record_event(key,pressed)
        else:self._message=self.tr('Эта клавиша пока не поддерживается редактором.');self.changed.emit()

    def _record_event(self,key,pressed):
        import time
        if not self._recording or not self._macro:return
        if len(self._macro.tokens)+len(self._macro.held)+3>=510:self.stopRecording();return
        if pressed and key in self._macro.held or not pressed and key not in self._macro.held:return
        now=time.monotonic()
        if self._capture_pauses and self._capture_time is not None:
            delay=round((now-self._capture_time)*1000)
            if delay>=10:self._macro.tokens.append('t'+str(min(delay,10000)))
        self._capture_time=now
        (self._macro.press if pressed else self._macro.release)(key);self._save_macro()

    @Slot(QObject,QObject)
    def beginMacroCapture(self,window,item):
        self._capture_window=window;self._capture_item=item;self.setRecording(True)
        if self._recording:window.installEventFilter(self)

    @Property(bool,notify=changed)
    def capturePauses(self):return self._capture_pauses

    @Slot(bool)
    def setCapturePauses(self,value):
        if not self._recording:self._capture_pauses=bool(value);self.changed.emit()

    @Property('QVariantList',notify=changed)
    def macroLibrary(self):return [{'id':e['id'],'name':e['name'],'count':len(e['tokens'])} for e in self._library]

    @Property(str,notify=changed)
    def selectedLibraryMacro(self):return self._library_selected

    @Property(str,notify=changed)
    def libraryMacroName(self):return self._library_name

    @Property(bool,notify=changed)
    def macroLibraryAvailable(self):return not self._library_error

    @Property(str,notify=changed)
    def libraryRepeatMode(self):
        entry=next((e for e in self._library if e['id']==self._library_selected),{})
        return entry.get('repeat_mode','once')

    @Slot(str)
    def setLibraryRepeatMode(self,mode):
        if mode not in ('once','toggle','held') or self._recording or self._library_error:return
        entry=next((e for e in self._library if e['id']==self._library_selected),None)
        if not entry:return
        entry['repeat_mode']=mode;self._save_library();self.changed.emit()

    def _save_library(self):
        from macro_library import KEY
        data=deepcopy(self._library)
        self.owner._preferences_pool.submit(self.store.edit,KEY,[],data)

    @Slot(str)
    def saveLibraryMacro(self,name):
        if self._library_error or self._recording or not self._macro:return
        from mouse_models import validate_macro
        try:
            validate_macro(self._macro.tokens,allow_empty=True)
            if not isinstance(name,str) or not 1<=len(name.strip())<=64:raise ValueError('Invalid name')
        except ValueError:self._message=self.tr('Проверь имя и завершённость нажатий макроса.');self.changed.emit();return
        entry=next((e for e in self._library if e['id']==self._library_selected),None)
        if entry is None:
            if len(self._library)>=100:return
            from macro_library import create
            entry=create(name);self._library.append(entry);self._library_selected=entry['id']
        entry.update(name=name.strip(),tokens=list(self._macro.tokens));self._library_name=entry['name'];self._save_library();self.changed.emit()

    @Slot(str)
    def createLibraryMacro(self,name):
        if self._recording or self._library_error or len(self._library)>=100:return
        if self._library_selected:self.saveLibraryMacro(self._library_name)
        from macro_library import create
        try:entry=create(name)
        except ValueError:return
        self._library.append(entry);self._library_selected=entry['id'];self._library_name=entry['name']
        self.clearMacro();self._save_library();self.changed.emit()

    @Slot(str)
    def selectLibraryMacro(self,identifier):
        if self._recording:return
        entry=next((e for e in self._library if e['id']==identifier),None)
        if not entry:return
        if self._library_selected:self.saveLibraryMacro(self._library_name)
        from mouse_models import MacroDraft
        self._macro=MacroDraft(tokens=list(entry['tokens']));self._library_selected=identifier;self._library_name=entry['name'];self._save_macro()

    @Slot(str)
    def deleteLibraryMacro(self,identifier):
        if self._recording or self._library_error:return
        self._library=[e for e in self._library if e['id']!=identifier]
        if self._library_selected==identifier:self._library_selected='';self._library_name=''
        self._save_library();self.changed.emit()
    @Slot(int)
    def addPause(self,delay):
        if self._macro and 1<=delay<=10000:self._macro.tokens.append('t'+str(delay));self._save_macro()
    @Slot(int)
    def removeEvent(self,index):
        if self._macro and 0<=index<len(self._macro.tokens):self._macro.tokens.pop(index);self._save_macro()
    @Slot()
    def clearMacro(self):
        if self._macro:self._macro.tokens=[];self._macro.held.clear();self._save_macro()
    @Slot()
    def resetMacro(self):
        key=self._macro_key();state=self._macro_states.setdefault(key,{'tokens':{},'choices':{}})
        state.setdefault('tokens',{}).pop(str(self._button),None);state.setdefault('choices',{}).pop(str(self._button),None)
        if state.get('tokens') or state.get('choices'):
            active=next(p for p in self._ratbag['profiles'] if p['index']==self._ratbag['active'])
            baseline=[{'index':b['index'],'action':b['action'],'macro':b['macro']} for b in active['buttons']]
            self.owner._preferences_pool.submit(self.store.edit,key,baseline,deepcopy(state))
        else:self.owner._preferences_pool.submit(self.store.discard,key)
        self._macro_conflict=False;self._load_macro();self.changed.emit()
    @Slot(int)
    def chooseAssignment(self,index):
        if not 0<=index<len(self.assignments):return
        key=self._macro_key();state=self._macro_states.setdefault(key,{'dirty':True,'tokens':{},'choices':{}})
        state['choices'][str(self._button)]=deepcopy(self.assignments[index]['value'])
        active=next(p for p in self._ratbag['profiles'] if p['index']==self._ratbag['active'])
        baseline=[{'index':b['index'],'action':b['action'],'macro':b['macro']} for b in active['buttons']]
        self.owner._preferences_pool.submit(self.store.edit,key,baseline,deepcopy(state));self.changed.emit()
    @Slot(int)
    def applyAssignment(self,index):
        if 0<=index<len(self.assignments):self._apply_button(self.assignments[index]['value'])
    @Slot()
    def applyMacro(self):
        self.stopRecording()
        if not self._macro:return
        if any(token.lstrip('+-').startswith('BTN_') for token in self._macro.tokens):
            self._message=self.tr('Щелчки записаны в библиотеку, но запись мышиных событий в аппаратный макрос G502 этим backend не подтверждена. Макрос не отправлен.')
            self._result='unsupported';self.changed.emit();return
        from mouse_models import conflicts
        try:self._macro.validate()
        except ValueError:self._message=self.tr('Макрос содержит незавершённые нажатия клавиш.');self.changed.emit();return
        if conflicts(self._macro.tokens) and self._warning_tokens!=tuple(self._macro.tokens):
            self._warning_tokens=tuple(self._macro.tokens);self._message=self.tr('Сочетание может конфликтовать с рабочим столом. Нажми «Применить» повторно для подтверждения.');self.changed.emit();return
        self._apply_button(['macro',*self._macro.tokens])
    def _apply_button(self,action):
        from mouse_models import action_allowed
        if not self.available or self._busy or not action_allowed(action,self._button_data().get('types',[])):return
        if self._other_write_busy():return
        if self._macro_conflict:self._message=self.tr('Черновик конфликтует с текущим значением. Отмени его и проверь настройку.');self.changed.emit();return
        expected=self._binding;token=self.epoch.token();target=self.device.targets['ratbagctl'][0]
        profile=self._ratbag['active']
        plan=plan_for(['ratbagctl',target,'profile',str(profile),'button',str(self._button),'action','set',*action])
        def write():
            def run(args,**kwargs):
                self._guard(expected,token);self._manager.guard_command(args)
                from backend import run as real_run
                if self.simulation and self.runner is None:raise Fault(FaultCode.BACKEND_UNSUPPORTED,'simulation','Fixture does not provide a ratbag transport')
                return (self.runner or real_run)(args,**kwargs)
            from operations import first_number
            self._guard_live_ratbag_profile(run,profile)
            if first_number(run(['ratbagctl',target,'profile','active','get']))!=profile:raise ActiveProfileChanged('Profile changed')
            return [(None,None,perform(plan,run,token))]
        self._submit('button',write)
    def _other_write_busy(self):
        if any(getattr(getattr(self.owner,name,None),'busy',False) is True for name in ('_backups','_audio')):
            self._message=self.tr('Дождись завершения текущей операции.');self.changed.emit();return True
        return False
    @Slot()
    def cancel(self):self.invalidate();self.changed.emit()
    def shutdown(self):
        if self._closed:return
        self.stopRecording();self.flush();self._closed=True;self.epoch.invalidate();self._draft_timer.stop()
        self._state_epoch.invalidate();self._state_timer.stop()
        if self._temp:
            temporary=self._temp;self._temp=None
            self.owner._preferences_pool.submit(temporary.cleanup)
