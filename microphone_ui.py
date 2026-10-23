"""Microphone testing UI. No stream is opened by construction or refresh."""
import json,math
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gtk,GLib
from audio_pipeline import processed_route
from backend import run
from i18n import tr as _

class MicrophonePanel(Gtk.Box):
    def __init__(self,sources,session,job,fault_handler=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=10)
        self.session=session;self.job=job;self.fault_handler=fault_handler;self.request=0
        self.sources=[s for s in sources if not s['name'].endswith('.monitor') and not s['name'].startswith('easyeffects_')]
        self.choice=Gtk.DropDown.new_from_strings([s.get('description',s['name']) for s in self.sources] or [_('Микрофон не найден')]);self.append(self.choice)
        self.choice.connect('notify::selected',lambda *unused:self.clear())
        self.level=Gtk.LevelBar(min_value=0,max_value=1,value=0);self.append(self.level)
        self.status=Gtk.Label(label=_('Микрофон не прослушивается. Нажми кнопку для начала.'),wrap=True);self.append(self.status)
        self.meter=Gtk.ToggleButton(label=_('Показать уровень микрофона'));self.meter.connect('toggled',self.toggle_meter);self.append(self.meter)
        self.record=Gtk.Button(label=_('Записать образец — до 8 секунд'));self.record.connect('clicked',self.record_clicked);self.append(self.record)
        stop=Gtk.Button(label=_('Завершить запись'));stop.connect('clicked',lambda *unused:self.session.finish_recording());self.append(stop)
        play=Gtk.Box(spacing=8)
        self.original=Gtk.Button(label=_('Прослушать исходный'),sensitive=False);self.processed=Gtk.Button(label=_('Прослушать обработанный'),sensitive=False)
        self.original.connect('clicked',lambda *unused:self.play('original'));self.processed.connect('clicked',lambda *unused:self.play('processed'))
        play.append(self.original);play.append(self.processed);self.append(play)
        delete=Gtk.Button(label=_('Удалить образцы и остановить тест'));delete.connect('clicked',lambda *unused:self.clear());self.append(delete)
        self.append(Gtk.Label(label=_('Запись временная: удаляется при обновлении, отключении устройства или закрытии приложения. Обработанный образец доступен только при подтверждённом маршруте EasyEffects от выбранного микрофона.'),wrap=True))
        if not self.sources:self.record.set_sensitive(False);self.meter.set_sensitive(False);self.status.set_text(_('Подключи микрофон и проверь диагностику компонентов.'))
    def dispatch(self,callback,*args):
        def deliver():
            if self.get_root() is not None:callback(*args)
            return False
        GLib.idle_add(deliver)
    def clear(self):
        self.request+=1
        self.session.stop();self.meter.set_active(False)
        self.original.set_sensitive(False);self.processed.set_sensitive(False);self.level.set_value(0)
        self.record.set_sensitive(bool(self.sources));self.meter.set_sensitive(bool(self.sources))
        self.status.set_text(_('Тест остановлен, временные образцы удалены.'))
    def error(self,error):
        if self.fault_handler:self.dispatch(self.fault_handler,error)
        self.dispatch(self.meter.set_active,False)
        self.dispatch(self.status.set_text,str(error));self.dispatch(self.record.set_sensitive,bool(self.sources));self.dispatch(self.meter.set_sensitive,bool(self.sources))
    def preflight(self):
        source=self.sources[self.choice.get_selected()]['name']
        def inspect():
            sources=json.loads(run(['pactl','-f','json','list','sources']))
            outputs=json.loads(run(['pactl','-f','json','list','source-outputs']))
            return source,processed_route(sources,outputs,source)
        return inspect
    def toggle_meter(self,button):
        if not button.get_active():
            if not self.session.recording:self.session.stop()
            return
        self.request+=1;request=self.request
        self.original.set_sensitive(False);self.processed.set_sensitive(False)
        def start(route):
            if request!=self.request or not button.get_active() or self.get_root() is None:return
            def value(level):
                self.dispatch(self.level.set_value,level)
                self.dispatch(self.status.set_text,('−∞' if level<=0 else str(round(20*math.log10(level),1)))+' dBFS')
            self.session.meter(route[0],value,self.error)
        self.job(self.preflight(),start,failed=self.error)
    def record_clicked(self,*unused):
        self.request+=1;request=self.request
        self.meter.set_active(False);self.session.stop()
        self.original.set_sensitive(False);self.processed.set_sensitive(False);self.record.set_sensitive(False);self.meter.set_sensitive(False)
        def start(route):
            if request!=self.request or self.get_root() is None:return
            self.status.set_text(_('Идёт запись исходного и обработанного сигнала…') if route[1] else _('Идёт запись только исходного сигнала: маршрут обработки не подтверждён.'))
            def complete(clips):
                self.dispatch(self.original.set_sensitive,'original' in clips);self.dispatch(self.processed.set_sensitive,'processed' in clips)
                self.dispatch(self.record.set_sensitive,True);self.dispatch(self.meter.set_sensitive,True)
                self.dispatch(self.status.set_text,_('Образец готов. Можно прослушать доступные сигналы.'))
            self.session.record(route[0],route[1],complete,self.error)
        self.job(self.preflight(),start,failed=self.error)
    def play(self,label):
        try:self.session.play(label,self.error)
        except Exception as error:self.error(error)
