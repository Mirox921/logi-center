"""Read-only inventory, explicit Solaar probes and existing public reports."""
import json
from PySide6.QtCore import QObject,Property,Signal,Slot,QUrl
from discovery import Epoch
from execution import CURRENT_CANCEL


class DiagnosticController(QObject):
    changed=Signal()
    _ready=Signal(str,object,object,object)
    def __init__(self,owner,pool):
        super().__init__(owner);self.owner=owner;self.pool=pool;self.epoch=Epoch();self._busy=False;self._closed=False;self._components=[];self._message='';self._report=''
        self._ready.connect(self._accept)
    @Property(bool,notify=changed)
    def busy(self):return self._busy
    @Property(str,notify=changed)
    def message(self):return self._message
    @Property(str,notify=changed)
    def reportText(self):return self._report
    @Property('QVariantList',notify=changed)
    def components(self):return self._components
    @Property('QVariantList',notify=changed)
    def inventory(self):
        from device_presentation import model_name
        from control_service import NAMES
        rows=[]
        for d in self.owner._current_devices():
            if d.kind=='interface':continue
            details=[]
            for c in d.capabilities:
                name=c.name.rsplit(':',1)[-1]
                details.append(self.owner.tr(NAMES.get(name,name))+' · '+c.backend+' · '+self.owner.tr('Чтение')+': '+str(c.readable)+' · '+self.owner.tr('Изменение')+': '+str(c.writable)+' · readback: '+str(c.verifiable)+' · '+c.source+(' · '+c.limitation if c.limitation else ''))
            from diagnostics import describe
            details.extend(describe(f) for f in d.faults)
            rows.append({'id':d.id,'name':model_name(d),'kind':d.kind,'source':' · '.join(d.backends),
                'status':self.owner.tr('Подключено' if d.connected is True else 'Отключено' if d.connected is False else 'Подключение не подтверждено'),
                'details':'\n'.join(details),'canProbe':d.backend=='solaar-local' and not self.owner.simulation})
        return rows
    def sync(self):
        if self.owner._manager:
            from reports import build_report
            self._report=json.dumps(build_report(self.owner._manager,self._components),ensure_ascii=False,indent=2)
        self.changed.emit()
    def _submit(self,action,work):
        if self._busy or self._closed:return
        token=self.epoch.token();self._busy=True;self.changed.emit()
        def task():
            context=CURRENT_CANCEL.set(token)
            try:return work()
            finally:CURRENT_CANCEL.reset(context)
        future=self.pool.submit(task)
        def done(f):
            if self._closed:return
            try:value,error=f.result(),None
            except Exception as exc:value,error=None,exc
            try:self._ready.emit(action,value,error,token)
            except RuntimeError:pass
        future.add_done_callback(done)
    @Slot()
    def collect(self):
        if self.owner.simulation:self._components=[{'component':'simulation','state':'available','description':self.owner.tr('Симуляция: аппаратные настройки не изменены.')}];self.sync();return
        from diagnostics import collect
        self._submit('collect',collect)
    @Slot(str)
    def exportReport(self,path):
        url=QUrl(path)
        if url.scheme() and not url.isLocalFile():return
        path=url.toLocalFile() if url.isLocalFile() else path
        from drafts import atomic_json
        report=json.loads(self._report) if self._report else None
        if report:self._submit('export',lambda:atomic_json(path,report))
    @Slot()
    def copyReport(self):
        from PySide6.QtGui import QGuiApplication
        if self._report:QGuiApplication.clipboard().setText(self._report)
    @Slot(str)
    def probeSolaar(self,identifier):
        if self.owner.simulation:return
        device=self.owner._find_device(identifier)
        if not device or device.backend!='solaar-local':return
        def inspect():
            from backend import saved_solaar_devices
            from solaar_adapter import probe
            records=[r for r in saved_solaar_devices() if r.get('_NAME')==device.name]
            if len(records)!=1:raise ValueError('Ambiguous saved device')
            return identifier,probe(records[0])
        self._submit('probe',inspect)
    @Slot(str,object,object,object)
    def _accept(self,action,value,error,token):
        if self._closed or token.is_set():return
        self._busy=False
        if error:
            from diagnostics import describe
            self._message=describe(error)
        elif action=='collect':self._components=value;self._message=''
        elif action=='export':self._message=self.owner.tr('Отчёт сохранён')
        elif action=='probe':
            identifier,(target,caps,faults)=value;device=self.owner._find_device(identifier)
            if device:
                device.target=target;device.backend='solaar';device.backends=['solaar'];device.targets={'solaar':[target]};device.capabilities=caps;device.faults=faults;device.connected=True if caps else None
                if self.owner.selectedDeviceId==identifier:self.owner._editor.bind(self.owner._manager,device)
                self.owner._refresh_artwork_row(device)
                self._message=self.owner.tr('Готово')
        self.sync()
    def invalidate(self):self.epoch.invalidate();self._busy=False;self.changed.emit()
    def shutdown(self):self._closed=True;self.invalidate()
