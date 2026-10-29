"""Audio presentation over pactl plans and the existing opt-in AudioSession."""
import json,math
from pathlib import Path
from PySide6.QtCore import QObject,Property,Signal,Slot,QUrl
from discovery import Epoch
from execution import CURRENT_CANCEL,Fault,FaultCode
from operations import perform,plan_for
from audio_status import device_available,endpoint_labels
from control_service import operation_message


class AudioController(QObject):
    changed=Signal()
    _ready=Signal(str,object,object,object)
    _stream=Signal(int,str,object)
    def __init__(self,owner,pool,simulation=False,runner=None,session=None):
        super().__init__(owner)
        from audio_pipeline import AudioSession
        self.owner=owner;self.pool=pool;self.simulation=simulation;self.runner=runner
        self.fixture=None
        if simulation and runner is None:
            from .audio_simulation import AudioSimulation
            self.fixture=AudioSimulation();self.runner=self.fixture.run
        self.session=session or (None if simulation else AudioSession())
        self.epoch=Epoch();self._closed=False;self._busy=False;self._message='';self._state='idle';self._level=0.;self._clips=[];self._request=0
        self._items={'sink':[],'source':[]};self._default={'sink':'','source':''};self._selection={'sink':'','source':''};self._drafts={}
        self._presets={'output':[],'input':[]};self._preferences={};self._prepared=False
        self._preset_state='idle';self._effects_available=False
        self._discarded=set()
        self._ready.connect(self._accept);self._stream.connect(self._accept_stream)
    def tr(self,text):return self.owner.tr(text)
    @Property(bool,notify=changed)
    def busy(self):return self._busy
    @Property(str,notify=changed)
    def message(self):return self._message
    @Property(str,notify=changed)
    def testState(self):return self._state
    @Property(float,notify=changed)
    def level(self):return self._level
    @Property('QVariantList',notify=changed)
    def clips(self):return self._clips
    @Property(bool,notify=changed)
    def captureAvailable(self):return self.session is not None and bool(self.selectedInput)
    @Property('QVariantList',notify=changed)
    def outputs(self):return self._rows('sink')
    @Property('QVariantList',notify=changed)
    def inputs(self):return self._rows('source')
    @Property('QVariantMap',notify=changed)
    def selectedOutput(self):return self._selected('sink')
    @Property('QVariantMap',notify=changed)
    def selectedInput(self):return self._selected('source')
    @Property('QVariantMap',notify=changed)
    def presets(self):return self._presets
    @Property(str,notify=changed)
    def presetState(self):return self._preset_state
    @Property(bool,notify=changed)
    def effectsAvailable(self):return self._effects_available
    def _rows(self,kind):
        rows=[]
        for item,identity in zip(self._items[kind],endpoint_labels(self._items[kind],kind,self.tr)):
            name=item['name'];volumes=item.get('volume',{})
            volume=next(iter(volumes.values())).get('value_percent','') if isinstance(volumes,dict) and volumes else ''
            value=int(volume.rstrip('%')) if isinstance(volume,str) and volume.rstrip('%').isdigit() else None
            draft_key='audio:'+kind+':'+name+':volume'
            if draft_key in self._discarded:draft,conflict=value,False
            elif draft_key in self._drafts:
                draft,base=self._drafts[draft_key];conflict=value!=base and value!=draft
            else:draft,conflict=self.owner._editor.store.get(draft_key,value)
            available=device_available(item)
            rows.append({'name':name,'index':item.get('index'),**identity,'available':available is not False,'availability':self.tr('Недоступно' if available is False else 'Доступно' if available is True else 'Доступность не подтверждена'),
                'volume':value,'desiredVolume':draft,'dirty':draft!=value,'conflict':conflict,'mute':item.get('mute'), 'default':name==self._default[kind]})
        return rows
    def _selected(self,kind):return next((r for r in self._rows(kind) if r['name']==self._selection[kind]),{})
    def sync(self,data):
        if self.fixture and 'sinks' not in data:data={**data,**self.fixture.snapshot()}
        previous={(kind,d['name'],d.get('index')) for kind,items in self._items.items() for d in items}
        old=next((r for r in self._items['source'] if r['name']==self._selection['source']),{})
        for key,collection,default in (('sink','sinks','default_sink'),('source','sources','default_source')):
            try:items=json.loads(data.get(collection,'[]'))
            except (ValueError,TypeError):items=[]
            self._items[key]=[d for d in items if isinstance(d,dict) and isinstance(d.get('name'),str) and not d['name'].endswith('.monitor') and not d['name'].startswith('easyeffects_')] if isinstance(items,list) else []
            previous_default=self._default[key]
            self._default[key]=str(data.get(default,previous_default)).strip()
            names=[d['name'] for d in self._items[key]]
            if self._selection[key] not in names or self._selection[key]==previous_default:self._selection[key]=self._default[key] if self._default[key] in names else next(iter(names),'')
        current=next((r for r in self._items['source'] if r['name']==self._selection['source']),{})
        identities={(kind,d['name'],d.get('index')) for kind,items in self._items.items() for d in items}
        if previous and identities!=previous:self.epoch.invalidate();self._busy=False;self._prepared=False
        if (old.get('name'),old.get('index'))!=(current.get('name'),current.get('index')):self.stopTest()
        self.changed.emit()
        if not self._prepared and not self._busy:
            self._prepared=True
            if self.simulation:
                self._preset_state='unavailable';self.changed.emit()
            else:
                self._preset_state='loading'
                def prepare():
                    from shutil import which
                    from audio_pipeline import preset_lists
                    from backend import load_preferences
                    return preset_lists(),load_preferences(),which('easyeffects') is not None
                self._submit('prepare',prepare)
    def _submit(self,action,work):
        if self._closed or self._busy:return
        token=self.epoch.token();self._busy=True;self.changed.emit()
        def task():
            ctx=CURRENT_CANCEL.set(token)
            try:
                if token.is_set():raise Fault(FaultCode.CANCELLED,'audio','Cancelled')
                return work(token)
            finally:CURRENT_CANCEL.reset(ctx)
        # Accept no-argument read helpers, while command closures receive a token.
        if action in ('prepare','import','preset'): 
            original=work;work=lambda token:original()
        future=self.pool.submit(task)
        def done(f):
            if self._closed:return
            try:value,error=f.result(),None
            except Exception as exc:value,error=None,exc
            try:self._ready.emit(action,value,error,token)
            except RuntimeError:pass
        future.add_done_callback(done)
    def _run(self,args,token,kind=None,name=None,**kwargs):
        if token.is_set():raise Fault(FaultCode.CANCELLED,'audio','Audio endpoints changed')
        if kind and name not in [d['name'] for d in self._items[kind]]:raise Fault(FaultCode.DISCONNECTED,'audio','Audio device disconnected')
        if self.simulation and self.runner is None:raise Fault(FaultCode.BACKEND_UNSUPPORTED,'simulation','Audio fixture transport unavailable')
        from backend import run
        return (self.runner or run)(args,**kwargs)
    @Slot(str,str)
    def selectEndpoint(self,kind,name):
        if self._busy and self._state!='preparing':return
        if kind not in self._items or name not in [d['name'] for d in self._items[kind]]:return
        if kind=='source' and self._selection[kind]!=name:self.stopTest()
        self._selection[kind]=name;self.changed.emit()
    @Slot(str,int)
    def editVolume(self,kind,value):
        if kind not in self._items or not 0<=value<=100 or self._busy:return
        row=self._selected(kind)
        if not row or row['volume'] is None:return
        key='audio:'+kind+':'+row['name']+':volume';base=self._drafts.get(key,(None,row['volume']))[1]
        self._discarded.discard(key);self._drafts[key]=(value,base)
        self.owner._preferences_pool.submit(self.owner._editor.store.edit,key,row['volume'],value);self.changed.emit()
    @Slot(str)
    def discardVolume(self,kind):
        row=self._selected(kind)
        if not row:return
        key='audio:'+kind+':'+row['name']+':volume';self._drafts.pop(key,None)
        self._discarded.add(key)
        self.owner._preferences_pool.submit(self.owner._editor.store.discard,key);self.changed.emit()
    @Slot(str,str)
    def applyEndpoint(self,kind,action):
        if kind not in self._items or self._busy:return
        if self._other_write_busy():return
        row=self._selected(kind)
        if not row or not row['available']:return
        name=row['name'];key=None
        if action=='default':command=['pactl','set-default-'+kind,name]
        elif action=='mute' and type(row['mute']) is bool:command=['pactl','set-'+kind+'-mute',name,'0' if row['mute'] else '1']
        elif action=='volume' and type(row['desiredVolume']) is int and 0<=row['desiredVolume']<=100 and not row['conflict']:
            command=['pactl','set-'+kind+'-volume',name,str(row['desiredVolume'])+'%'];key='audio:'+kind+':'+name+':volume'
        else:return
        self._submit('write',lambda token:(perform(plan_for(command),lambda args,**kw:self._run(args,token,kind,name,**kw),token),key))
    @Slot(str,str)
    def loadPreset(self,kind,name):
        if self._busy or not self._effects_available or self._preset_state not in ('ready','empty') or kind not in ('input','output') or not name or name not in self._presets[kind]:return
        if self._other_write_busy():return
        def load():
            if self.simulation and self.runner is None:raise ValueError('No simulation effects transport')
            from audio_pipeline import load_preset
            return load_preset(kind,name,runner=self.runner),kind,name
        self._submit('preset',load)
    @Slot(str)
    def importPreset(self,url):
        path=QUrl(url).toLocalFile() if QUrl(url).isLocalFile() else url
        def install():
            if self.simulation:raise ValueError('Preset import is disabled in simulation')
            from backend import import_preset
            from audio_pipeline import preset_lists
            result=import_preset(path);return result,preset_lists()
        self._submit('import',install)
    @Slot(bool)
    def setBypass(self,enabled):
        if not self._effects_available or self._other_write_busy():return
        self._submit('write',lambda token:(perform(plan_for(['easyeffects','-b','1' if enabled else '2']),lambda args,**kw:self._run(args,token,**kw),token),None))
    def _other_write_busy(self):
        if any(getattr(getattr(self.owner,name,None),'busy',False) is True for name in ('_backups','_editor')):
            self._message=self.tr('Дождись завершения текущей операции.');self.changed.emit();return True
        return False
    @Slot(str)
    def startTest(self,mode):
        if mode not in ('meter','record') or not self.captureAvailable or self._busy:return
        row=self.selectedInput
        if not row.get('available'):return
        self.stopTest();request=self._request;source=row['name'];self._state='preparing';self.changed.emit()
        def prepare(token):
            from audio_pipeline import processed_route
            sources=json.loads(self._run(['pactl','-f','json','list','sources'],token))
            outputs=json.loads(self._run(['pactl','-f','json','list','source-outputs'],token))
            return request,mode,source,processed_route(sources,outputs,source)
        self._submit('test',prepare)
    @Slot()
    def stopTest(self):
        if self._state!='idle' or self._clips:self._message=self.tr('Тест остановлен, временные образцы удалены.')
        self._request+=1
        if self.session:self.session.stop()
        self._clips=[];self._level=0.;self._state='idle';self.changed.emit()
    @Slot(str)
    def play(self,label):
        if not self.session or label not in self._clips:return
        request=self._request
        self._submit('play',lambda token:self.session.play(label,lambda error:self._stream.emit(request,'error',error)))
    @Slot(int,str,object)
    def _accept_stream(self,request,kind,value):
        if self._closed or request!=self._request:return
        if kind=='level':self._level=value;self._message=('−∞' if value<=0 else str(round(20*math.log10(value),1)))+' dBFS'
        elif kind=='clips':self._clips=sorted(value);self._state='ready';self._message=self.tr('Образец готов. Можно прослушать доступные сигналы.')
        else:
            from control_service import fault_message
            self.stopTest();self._state='error';self._message=fault_message(value)
        self.changed.emit()
    @Slot(str,object,object,object)
    def _accept(self,action,value,error,token):
        if self._closed or token.is_set():return
        self._busy=False
        if error:
            from control_service import fault_message
            self._message=fault_message(error);self._state='error'
            if action=='prepare':self._preset_state='error'
            self.changed.emit();return
        if action=='prepare':
            self._presets,self._preferences,self._effects_available=value
            self._preset_state=('ready' if any(self._presets.values()) else 'empty') if self._effects_available else 'unavailable'
        elif action=='write':
            result,key=value;self._message=operation_message(result)
            if key and result.accepted:
                self.owner._preferences_pool.submit(self.owner._editor.store.submitted,key,result.state.value)
                if result.state.value=='confirmed':self._drafts.pop(key,None);self._discarded.add(key)
            if result.accepted or result.state.value=='disconnected':self.owner.refresh()
        elif action=='import':
            self._presets=value[1];self._preset_state='ready' if self._effects_available else 'unavailable'
            self._message=self.tr('Эффект добавлен: ')+value[0][0]
        elif action=='preset':
            result,kind,name=value;self._message=operation_message(result)
            if result.accepted:
                self._preferences.setdefault('presets',{})[kind]=name
                from backend import save_preferences
                if not self.simulation:self.owner._preferences_pool.submit(save_preferences,dict(self._preferences))
        elif action=='test':
            request,mode,source,processed=value
            if request!=self._request:self.changed.emit();return
            if mode=='meter':self._state='meter';self.session.meter(source,lambda level:self._stream.emit(request,'level',level),lambda error:self._stream.emit(request,'error',error))
            else:
                self._state='recording';self._message=self.tr('Идёт запись исходного и обработанного сигнала…' if processed else 'Идёт запись только исходного сигнала: маршрут обработки не подтверждён.')
                self.session.record(source,processed,lambda clips:self._stream.emit(request,'clips',clips),lambda error:self._stream.emit(request,'error',error),seconds=8)
        self.changed.emit()
    def invalidate(self):
        self.epoch.invalidate();self._busy=False;self._prepared=False;self.stopTest()
    def shutdown(self):self._closed=True;self.invalidate()
