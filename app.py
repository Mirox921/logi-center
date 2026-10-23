#!/usr/bin/env python3
import concurrent.futures, subprocess, re, json, sys
from pathlib import Path
import gi
gi.require_version('Gtk','4.0');gi.require_version('Adw','1')
from gi.repository import Gtk, Adw, GLib, Gio, Gdk
from diagnostics import SafeLog,collect as collect_diagnostics,fault_for,describe as describe_fault
from audio_pipeline import AudioSession,preset_lists,load_preset
from microphone_ui import MicrophonePanel
from mouse_editor import MouseEditor
from mouse_models import assignment_label,action_allowed
from backups import snapshot, write_backup, read_backup, preview as backup_preview, restore as restore_backup
from operations import perform, plan_for, Result, State
from execution import Fault, FaultCode, CURRENT_CANCEL
from discovery import Epoch,DeviceMonitor,MousePresence
from drafts import DraftStore,atomic_json
from i18n import EN,canonical_text
from devices import mouse_capabilities,DeviceManager,InputAdapter,RatbagAdapter,PulseAdapter,HeadsetAdapter,SavedSolaarAdapter
from device_ui import populate_inventory
from keyboard_ui import KeyboardDiagram
from reports import build_report
from i18n import tr as _, set_language
from backend import run, mouse_list, solaar_settings, audio_devices, volume, wireless_batteries, battery_label, load_preferences, save_preferences, saved_keyboard, import_preset, keyboard_online, keyboard_saved_settings, read_mouse

class Center(Adw.Application):
    def __init__(self):
        simulation='--simulate' in sys.argv
        super().__init__(application_id='local.mirox.LogiCenter.Simulation' if simulation else 'local.mirox.LogiCenter')
        self.simulation=simulation
        self.device_manager=DeviceManager();self.page_fingerprints={};self.ambiguous_mouse_targets=set()
        if self.simulation:
            from simulation import SimulationAdapter
            self.simulation_adapter=SimulationAdapter()
        self.audio_session=AudioSession()
        self.draft_store=DraftStore();self.draft_scope="global";self.submitting_drafts=()
        self.log=SafeLog()
        self.pool=concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.epoch=Epoch();self.closed=False;self.hotplug_timer=None;self.ui_generation=0
        self.scroll_positions={};self.mouse_request=0;self.refresh_revision=0
        self.current_mouse_name=''
        self.mouse_presence=MousePresence()
        self.keyboard_connected=None
        self.keyboard_polling=False
        self.preferences=load_preferences()
        set_language(self.preferences.get('language','ru'))
        self.connect('activate',self.activate)
        self.connect('shutdown',self.shutdown_resources)
        self.monitor=DeviceMonitor(lambda reason:GLib.idle_add(self.hardware_event,reason))
        self.monitor_started=False
    def activate(self,*unused):
        if hasattr(self,'win'):self.win.present();return
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        self.win=Adw.ApplicationWindow(application=self,title='Logi Center'+(' · '+_('СИМУЛЯЦИЯ') if self.simulation else ''),default_width=1000,default_height=780)
        self.toast=Adw.ToastOverlay();self.win.set_content(self.toast)
        layout=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);self.toast.set_child(layout)
        header=Adw.HeaderBar();header.set_title_widget(Adw.WindowTitle(title='Logi Center',subtitle=_('Твои устройства · один центр управления')))
        refresh=Gtk.Button(icon_name='view-refresh-symbolic',tooltip_text=_('Обновить устройства'));refresh.connect('clicked',lambda *unused:self.refresh());header.pack_end(refresh)
        diagnostic=Gtk.Button(icon_name='dialog-information-symbolic',tooltip_text=_('Диагностика'))
        diagnostic.connect('clicked',lambda *unused:self.job(collect_diagnostics,self.show_diagnostics));header.pack_end(diagnostic)
        languages=Gtk.DropDown.new_from_strings(['Русский','English']);languages.set_tooltip_text('Язык / Language')
        languages.set_selected(1 if self.preferences.get('language','ru')=='en' else 0)
        languages.connect('notify::selected',self.change_language)
        header.pack_start(languages);layout.append(header)
        self.stack=Adw.ViewStack();switcher=Adw.ViewSwitcherBar(stack=self.stack,reveal=True);layout.append(switcher)
        self.pages={}
        for key,title,icon in [('devices',_('Устройства'),'computer-symbolic'),('mouse',_('Мышь'),'input-mouse-symbolic'),('keyboard',_('Клавиатуры'),'input-keyboard-symbolic'),('audio',_('Звук'),'audio-headphones-symbolic')]:
            box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=20,margin_top=24,margin_bottom=24,margin_start=32,margin_end=32)
            clamp=Adw.Clamp(maximum_size=860);clamp.set_child(box)
            scroll=Gtk.ScrolledWindow(vexpand=True);scroll.set_child(clamp)
            self.stack.add_titled_with_icon(scroll,key,title,icon);self.pages[key]=box
        self.battery_box=Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,min_children_per_line=1,max_children_per_line=3,row_spacing=6,column_spacing=18,halign=Gtk.Align.CENTER,margin_top=10,margin_bottom=12)
        self.battery_widgets={};self.battery_keys=()
        layout.append(self.battery_box)
        self.update_batteries()
        self.battery_timer=GLib.timeout_add_seconds(30,self.poll_keyboard) if not self.simulation else 0
        layout.append(self.stack)
        if '--keyboard' in sys.argv:self.stack.set_visible_child_name('keyboard')
        if '--audio' in sys.argv:self.stack.set_visible_child_name('audio')
        self.operation_result=Gtk.Label(wrap=True,selectable=True,margin_start=20,margin_end=20)
        layout.append(self.operation_result)
        self.status=Gtk.Label(label=_('Чтение устройств…'),margin_bottom=12,wrap=True);layout.append(self.status)
        self.stack.connect('notify::visible-child-name',lambda *unused:self.audio_session.stop() if self.stack.get_visible_child_name()!='audio' else None)
        self.refresh();self.win.present()
        if not self.monitor_started and not self.simulation:self.monitor.start();self.monitor_started=True
        if '--smoke' in sys.argv:GLib.timeout_add_seconds(12,lambda:(self.quit(),False)[1])
    def change_language(self,dropdown,param):
        self.ui_generation+=1
        language=['ru','en'][dropdown.get_selected()]
        if language==self.preferences.get('language','ru'):return
        self.preferences['language']=language;save_preferences(self.preferences);set_language(language)
        if getattr(self,'battery_timer',0):GLib.source_remove(self.battery_timer)
        old_window=self.win
        page=self.stack.get_visible_child_name()
        del self.win
        self.activate()
        self.stack.set_visible_child_name(page)
        old_window.destroy()
    def job(self,fn,done=None,failed=None):
        self.status.set_label(_('Выполняется…'))
        token=self.epoch.token();ui_generation=self.ui_generation
        def worker():
            CURRENT_CANCEL.set(token)
            if token.is_set():raise Fault(FaultCode.CANCELLED,'application','Operation cancelled')
            return fn()
        future=self.pool.submit(worker)
        def finish(f):
            try: value=f.result();error=None
            except Exception as exc:value=None;error=exc
            def deliver():
                if self.closed or token.is_set() or ui_generation!=self.ui_generation:return False
                if error:
                    self.present_fault(error)
                    if failed:failed(error)
                else:
                    self.status.set_label(_('Готово'))
                    if done:done(value)
                return False
            GLib.idle_add(deliver)
        future.add_done_callback(finish)
    def present_fault(self,error):
        fault=fault_for(error);self.log.fault(fault)
        message=describe_fault(fault)
        self.status.set_text(message);self.operation_result.set_text(message)
        self.toast.add_toast(Adw.Toast(title=message.split('\n')[0]))
    def show_diagnostics(self,report):
        dialog=Adw.Dialog(title=_('Диагностика компонентов'),content_width=760,content_height=560)
        content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,margin_start=20,margin_end=20,margin_top=20,margin_bottom=20)
        text=json.dumps(build_report(self.device_manager,report),ensure_ascii=False,indent=2)
        view=Gtk.TextView(editable=False,wrap_mode=Gtk.WrapMode.WORD_CHAR);view.get_buffer().set_text(text)
        scroll=Gtk.ScrolledWindow(vexpand=True);scroll.set_child(view);content.append(scroll)
        copy=Gtk.Button(label=_('Скопировать отчёт без личных данных'));copy.connect('clicked',lambda *unused:Gdk.Display.get_default().get_clipboard().set(text));content.append(copy)
        export=Gtk.Button(label=_('Экспортировать отчёт JSON'))
        def save_report(*unused):
            chooser=Gtk.FileDialog(title=_('Экспортировать отчёт JSON'),initial_name='logi-center-diagnostics.json')
            def chosen(chooser,result):
                try:path=chooser.save_finish(result).get_path()
                except GLib.Error:return
                if path:self.job(lambda:atomic_json(path,json.loads(text)))
            chooser.save(self.win,None,chosen)
        export.connect('clicked',save_report);content.append(export)
        close=Gtk.Button(label=_('Закрыть'));close.connect('clicked',lambda *unused:dialog.close());content.append(close)
        dialog.set_child(content);dialog.present(self.win)
    def operation_text(self,result):
        states={State.LOCAL:_('Доступно только локальное значение'),State.UNSUPPORTED:_('Операция не поддерживается'),State.PERMISSION:_('Нет доступа'),State.CONFIRMED:_('Подтверждено устройством'),State.SENT:_('Команда отправлена, подтверждение недоступно'),State.MISMATCH:_('Значение не совпадает'),State.ERROR:_('Ошибка применения'),State.DISCONNECTED:_('Устройство отключено'),State.CANCELLED:_('Операция отменена')}
        text=result.component+' · '+(_('Подтверждено звуковым сервером') if result.state==State.CONFIRMED and result.source=='audio_server' else states[result.state])
        if result.source=='backend_cache':text+=' · '+_('Ответ из кэша backend, не аппаратное подтверждение')
        if result.state==State.MISMATCH:
            text+='\n'+_('Запрошено: ')+str(result.requested)[:120]+' · '+_('Получено: ')+str(result.actual)[:120]
        if result.fault:text+='\n'+describe_fault(result.fault)
        return text
    def show_operation(self,result):
        text=self.operation_text(result)
        self.operation_result.set_text(text)
        self.toast.add_toast(Adw.Toast(title=text.split(' · ',1)[-1].split('\n')[0]))
    def apply(self,args,after=None,verified_plan=None):
        if self.simulation:self.present_fault(Fault(FaultCode.BACKEND_UNSUPPORTED,'simulation','Real hardware writes are disabled in simulation mode'));return
        draft_keys=self.submitting_drafts
        def write():
            result=perform(verified_plan or plan_for(args))
            self.log.operation(result)
            if result.accepted:
                if args[0]=='headsetcontrol' and '-s' in args:self.preferences['sidetone']=args[-1]
                if args[0]=='easyeffects' and '-l' in args:self.preferences['preset']=args[-1]
                save_preferences(self.preferences)
            return result
        def completed(result):
            self.device_manager.record_operation(args,result)
            self.show_operation(result)
            if result.accepted:
                for key in draft_keys:self.draft_store.submitted(key,result.state.value)
            if after and result.accepted:after(result)
        self.job(write,completed)
    def apply_batch(self,commands,after=None):
        if self.simulation:self.present_fault(Fault(FaultCode.BACKEND_UNSUPPORTED,'simulation','Real hardware writes are disabled in simulation mode'));return
        draft_keys=self.submitting_drafts
        def write():
            results=[]
            for command in commands:
                result=perform(plan_for(command));self.log.operation(result);results.append(result)
                if not result.accepted:break
            return results
        def completed(results):
            for result in results:self.show_operation(result)
            if len(results)==len(commands) and all(r.accepted for r in results):
                for key in draft_keys:self.draft_store.submitted(key,"confirmed" if all(r.state==State.CONFIRMED for r in results) else "sent_unverified")
                if after:after(results)
        self.job(write,completed)
    def backup_controls(self,group,kind,target):
        row=self.row(group,_('Резервная копия'),_('Источник данных указан в файле; локальные настройки не являются аппаратной копией.'))
        self.button(row,_('Сохранить настройки устройства'),lambda *unused:self.export_backup(kind,target))
        self.button(row,_('Восстановить настройки'),lambda *unused:self.choose_backup(kind,target))
    def export_backup(self,kind,target):
        dialog=Gtk.FileDialog(title=_('Сохранить настройки устройства'),initial_name=kind+'-backup.json')
        def chosen(dialog,result):
            try:path=dialog.save_finish(result).get_path()
            except GLib.Error:return
            if not path:return
            def export():
                document=snapshot(kind,target);write_backup(document,path);return document['source']
            self.job(export,lambda source:self.toast.add_toast(Adw.Toast(title=_('Копия сохранена. Источник: ')+source)))
        dialog.save(self.win,None,chosen)
    def choose_backup(self,kind,target):
        dialog=Gtk.FileDialog(title=_('Восстановить настройки'))
        def chosen(dialog,result):
            try:path=dialog.open_finish(result).get_path()
            except GLib.Error:return
            if not path:return
            def inspect():
                document=read_backup(path)
                if document['device']['kind']!=kind:raise ValueError('Backup is for a different device type')
                return backup_preview(document,snapshot(kind,target),target)
            self.job(inspect,lambda value:self.restore_dialog(value,target))
        dialog.open(self.win,None,chosen)
    def restore_dialog(self,preview,target):
        dialog=Adw.Dialog(title=_('Предпросмотр восстановления'),content_width=760,content_height=600)
        content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,margin_start=20,margin_end=20,margin_top=20,margin_bottom=20)
        content.append(Gtk.Label(label=_('Источник копии: ')+preview.backup['source'],wrap=True))
        content.append(Gtk.Label(label=_('Перед изменениями будет сохранена защитная копия. При ошибке восстановление остановится; автоматический откат не гарантируется.'),wrap=True))
        choices={}
        grid=Gtk.Grid(column_spacing=14,row_spacing=10,margin_top=8)
        for column,label in enumerate([_('Параметр'),_('Сейчас'),_('Из копии'),_('Ожидаемое действие')]):
            title=Gtk.Label(label=label,xalign=0);title.add_css_class('heading');grid.attach(title,column,0,1,1)
        for index,change in enumerate(preview.changes,1):
            check=Gtk.CheckButton(label=change.label.split(' → ')[0],active=True);choices[change.id]=check;grid.attach(check,0,index,1,1)
            for column,value in [(1,change.current),(2,change.desired)]:
                label=Gtk.Label(label=json.dumps(value,ensure_ascii=False),wrap=True,max_width_chars=22,xalign=0,selectable=True);grid.attach(label,column,index,1,1)
            grid.attach(Gtk.Label(label=change.category,xalign=0),3,index,1,1)
        if not preview.changes:grid.attach(Gtk.Label(label=_('Изменений нет')),0,1,4,1)
        for index,message in enumerate(preview.skipped,len(preview.changes)+1):
            grid.attach(Gtk.Label(label=_('Пропущено: ')+message,wrap=True,xalign=0),0,index,4,1)
        scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.AUTOMATIC);scroll.set_child(grid);content.append(scroll)
        buttons=Gtk.Box(spacing=12,halign=Gtk.Align.END)
        cancel=Gtk.Button(label=_('Отмена'));cancel.connect('clicked',lambda *unused:dialog.close());buttons.append(cancel)
        apply=Gtk.Button(label=_('Восстановить выбранное'),sensitive=bool(preview.changes));buttons.append(apply);content.append(buttons)
        def start(*unused):
            selected={k for k,c in choices.items() if c.get_active()}
            if not selected:return
            dialog.close()
            def completed(report):
                lines=[_('Защитная копия: ')+report.safety_copy]
                for label,result in report.results:lines.append(label+'\n'+self.operation_text(result))
                lines.extend(report.skipped)
                if report.stopped:lines.append(_('Восстановление остановлено после ошибки. Проверь частично применённые настройки.'))
                self.operation_result.set_text('\n'.join(lines))
                self.refresh()
            self.job(lambda:restore_backup(preview,selected,target,on_result=self.log.operation),completed)
        apply.connect('clicked',start);dialog.set_child(content);dialog.present(self.win)
    def group(self,page,title,description=None):
        g=Adw.PreferencesGroup(title=title,description=description);self.pages[page].append(g);return g
    def row(self,g,title,subtitle=''):
        r=Adw.ActionRow(title=GLib.markup_escape_text(title),subtitle=GLib.markup_escape_text(subtitle));r.set_subtitle_lines(3);g.add(r);return r
    def button(self,row,label,callback):
        b=Gtk.Button(label=label,valign=Gtk.Align.CENTER);b.connect('clicked',callback);row.add_suffix(b);return b
    def submit_drafts(self,keys,callback,*args):
        old=self.submitting_drafts;self.submitting_drafts=tuple(keys)
        try:callback(*args)
        finally:self.submitting_drafts=old
    def bind_draft(self,widget,key,observed,getter,setter,signal):
        desired,conflict=self.draft_store.get(key,observed)
        try:setter(desired)
        except (ValueError,TypeError):
            conflict=True
            try:setter(observed)
            except (ValueError,TypeError):pass
        def changed(*unused):
            try:self.draft_store.edit(key,observed,getter())
            except (OSError,ValueError) as error:self.present_fault(error)
        widget.connect(signal,changed)
        if conflict:
            widget.add_css_class('error');widget.set_tooltip_text(_('Черновик сохранён, но состояние устройства изменилось. Проверь значения или загрузи текущее.'))
            self.operation_result.set_text(_('Черновик сохранён, но состояние устройства изменилось. Проверь значения или загрузи текущее.'))
        return conflict
    def choice(self,g,title,items,current,callback,subtitle=''):
        if not items:return
        row=self.row(g,title,subtitle);values=[str(x) for x in items]
        combo=Gtk.DropDown.new_from_strings(values);combo.set_valign(Gtk.Align.CENTER)
        observed=str(current) if str(current) in values else values[0]
        key=self.draft_scope+'/'+canonical_text(title)
        canonical=[canonical_text(value) for value in values]
        self.bind_draft(combo,key,canonical_text(observed),lambda:canonical[combo.get_selected()],lambda value:combo.set_selected(canonical.index(str(value))),'notify::selected')
        row.add_suffix(combo)
        self.button(row,_('Загрузить текущее'),lambda *unused:(self.draft_store.discard(key),combo.set_selected(values.index(observed))))
        self.button(row,_('Применить'),lambda *unused:self.submit_drafts([key],callback,values[combo.get_selected()]))
    def launch(self,command):
        try:subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except OSError as e:self.toast.add_toast(Adw.Toast(title=str(e)))
    def choose_preset(self,*unused):
        dialog=Gtk.FileDialog(title=_('Импортировать готовый эффект'))
        filter=Gtk.FileFilter();filter.set_name(_('Пресеты EasyEffects (*.json)'));filter.add_pattern('*.json');filter.add_pattern('*.JSON')
        filters=Gio.ListStore.new(Gtk.FileFilter);filters.append(filter);dialog.set_filters(filters)
        def selected(dialog,result):
            try:
                file=dialog.open_finish(result)
                path=file.get_path()
                if not path:
                    self.toast.add_toast(Adw.Toast(title=_('Сначала скачай файл на компьютер.')));return
            except GLib.Error:return
            def install():
                try:return import_preset(path),None
                except (ValueError,OSError) as error:return None,str(error)
            def completed(outcome):
                value,error=outcome
                if error:
                    self.toast.add_toast(Adw.Toast(title=_('Не удалось импортировать: ')+_(error)[:180]));return
                name,kinds=value
                self.preferences['preset']=name
                for kind in kinds:self.preferences.setdefault('presets',{})[kind]=name
                save_preferences(self.preferences)
                self.refresh()
                self.toast.add_toast(Adw.Toast(title=_('Эффект добавлен: ')+name+_('. Выбери его и нажми «Применить».')))
            self.job(install,completed)
        dialog.open(self.win,None,selected)
    def poll_keyboard(self):
        if self.keyboard_polling:return True
        self.keyboard_polling=True
        token=self.epoch.token()
        future=self.pool.submit(keyboard_online)
        def finish(f):
            try:connected=f.result()
            except Exception:connected=None
            def deliver():
                self.keyboard_polling=False
                if self.closed or token.is_set():return False
                self.keyboard_connected=connected
                if hasattr(self,'keyboard_group'):self.keyboard_group.set_sensitive(connected is True)
                self.update_batteries()
                return False
            GLib.idle_add(deliver)
        future.add_done_callback(finish)
        return True
    def update_batteries(self):
        if self.simulation:return True
        entries=[]
        if self.mouse_presence.name:
            state=self.mouse_presence.connected
            status=_('Подключена по USB') if state is True and 'G502' in self.mouse_presence.name else _('Подключена') if state is True else _('Не в сети') if state is False else _('Связь не подтверждена')
            entries.append(('mouse',self.mouse_presence.name+' · '+status,'input-mouse-symbolic' if state is True else 'network-offline-symbolic'))
        for index,battery in enumerate(wireless_batteries()):
            text,icon=battery_label(battery)
            entries.append((battery.get('id',str(index)),battery['model']+' · '+_(text),icon))
        keys=tuple(item[0] for item in entries)
        if keys!=self.battery_keys:
            while self.battery_box.get_first_child():self.battery_box.remove(self.battery_box.get_first_child())
            self.battery_widgets={};self.battery_keys=keys
            for key,text,icon_name in entries:
                box=Gtk.Box(spacing=6);icon=Gtk.Image(icon_name=icon_name)
                label=Gtk.Label(wrap=True,max_width_chars=28);box.append(icon);box.append(label);self.battery_box.insert(box,-1)
                self.battery_widgets[key]=(label,icon)
        for key,text,icon_name in entries:
            label,icon=self.battery_widgets[key];label.set_text(text);icon.set_from_icon_name(icon_name)
        return True
    def hardware_event(self,reason):
        if self.closed:return False
        if reason=='battery':
            self.update_batteries()
            if not self.keyboard_polling:self.poll_keyboard()
            return False
        self.epoch.invalidate()
        self.mouse_presence.invalidate();self.update_batteries()
        for box in self.pages.values():box.set_sensitive(False)
        if hasattr(self,'audio_session'):self.audio_session.stop()
        if self.hotplug_timer:GLib.source_remove(self.hotplug_timer)
        def update():
            self.hotplug_timer=None
            self.refresh(force=False)
            return False
        self.hotplug_timer=GLib.timeout_add(400,update)
        return False
    def shutdown_resources(self,*unused):
        self.closed=True;self.epoch.invalidate()
        if getattr(self,'battery_timer',0):GLib.source_remove(self.battery_timer)
        if self.hotplug_timer:GLib.source_remove(self.hotplug_timer)
        if hasattr(self,'audio_session'):self.audio_session.close()
        # Monitor shutdown runs outside GTK; its observer may be waiting for netlink.
        self.pool.shutdown(wait=False,cancel_futures=True)
        self.log.close()
        __import__('threading').Thread(target=self.monitor.stop,daemon=True).start()
    def restore_scroll(self):
        if self.closed:return False
        for page,value in self.scroll_positions.items():
            scroll=self.stack.get_child_by_name(page)
            if scroll:scroll.get_vadjustment().set_value(value)
        return False
    def refresh(self,force=True):
        if self.closed:return
        self.audio_session.stop()
        self.refresh_revision+=1;revision=self.refresh_revision
        self.mouse_request+=1;self.mouse_presence.invalidate()
        for page in self.pages:
            scroll=self.stack.get_child_by_name(page)
            if scroll:self.scroll_positions[page]=scroll.get_vadjustment().get_value()

        self.update_batteries()
        def collect():
            if self.simulation:
                self.device_manager=DeviceManager([self.simulation_adapter]);self.device_manager.discover()
                return {'manager':self.device_manager}
            data={}
            for key,args in [('mice',['ratbagctl','list']),('headset',['headsetcontrol','-o','json']),('sinks',['pactl','-f','json','list','sinks']),('sources',['pactl','-f','json','list','sources'])]:
                try:data[key]=run(args,40)
                except Exception as e:data[key+'_error']=e
            data['keyboard_online']=keyboard_online()
            cached={tuple(args):data[key] for key,args in [('mice',['ratbagctl','list']),('headset',['headsetcontrol','-o','json']),('sinks',['pactl','-f','json','list','sinks']),('sources',['pactl','-f','json','list','sources'])] if key in data}
            def inventory_run(args,**kwargs):
                return cached[tuple(args)] if tuple(args) in cached else run(args,**kwargs)
            manager=DeviceManager([InputAdapter(),RatbagAdapter(inventory_run),PulseAdapter(inventory_run),HeadsetAdapter(inventory_run),SavedSolaarAdapter()])
            manager.discover();data['manager']=manager
            return data
        self.job(collect,lambda data:self.populate(data,force) if revision==self.refresh_revision else None)
    def clear(self,key):
        b=self.pages[key]
        while b.get_first_child():b.remove(b.get_first_child())
    def populate(self,data,force=True):
        manager=data.get('manager',DeviceManager())
        # Preserve detailed observations when discovery intentionally did not query them.
        for device in manager.devices:
            if device.backend=='ratbagctl' and not device.capabilities and not device.faults:
                old=next((d for d in self.device_manager.devices if device.target in d.targets.get('ratbagctl',[]) and device.name==d.name and not d.faults),None)
                if old:
                    device.capabilities=[c for c in old.capabilities if c.backend=='ratbagctl'];device.vid=old.vid;device.pid=old.pid
        self.device_manager=manager
        inventory=mouse_list(data.get('mice',''))
        self.ambiguous_mouse_targets={target for target,name in inventory if sum(item[0]==target for item in inventory)>1}
        def signature(devices):
            return repr([(d.id,d.physical,d.name,d.connected,[(c.name,c.backend,c.supported,c.writable,c.verifiable,c.value,c.source,c.choices,c.minimum,c.maximum) for c in d.capabilities]) for d in devices])
        fingerprints={
            'devices':signature(manager.devices)+str(manager.faults),
            'mouse':str(data.get('mice',data.get('mice_error')))+signature([d for d in manager.devices if d.kind=='mouse']),
            'keyboard':str(data.get('keyboard_online'))+signature([d for d in manager.devices if d.kind in ['keyboard','input']]),
            'audio':str([data.get(k,data.get(k+'_error')) for k in ['sinks','sources','headset']])}
        for box in self.pages.values():box.set_sensitive(True)
        changed={page for page,value in fingerprints.items() if force or self.page_fingerprints.get(page)!=value}
        if 'devices' in changed:populate_inventory(self,manager.devices,manager.faults)
        if self.simulation:
            self.operation_result.set_text(_('СИМУЛЯЦИЯ: реальные устройства и аудиозапись отключены.'))
            self.clear('mouse');self.clear('keyboard');self.clear('audio')
            for device in manager.devices:
                if device.kind=='keyboard':
                    group=self.group('keyboard',_('СИМУЛЯЦИЯ · ')+device.name);group.add(KeyboardDiagram())
                elif device.kind=='mouse':
                    group=self.group('mouse',_('СИМУЛЯЦИЯ · ')+device.name)
                    count=next((c.value for c in device.capabilities if c.name=='buttons'),6)
                    count=count if isinstance(count,int) else 6
                    buttons=[{'index':i,'action':'button '+str(i+1),'macro':False} for i in range(count)]
                    actions={_('Левый щелчок'):['button','1'],_('Правый щелчок'):['button','2'],_('Отключить кнопку'):['disabled']}
                    macro=any(c.name=='macros' for c in device.capabilities)
                    types={i:[0,1,3]+([4] if macro else []) for i in range(count)}
                    def apply(index,action,d=device):
                        self.job(lambda:self.simulation_adapter.apply(d.target,'button:'+str(index),action),self.show_operation)
                    group.add(MouseEditor(device.name,buttons,actions,types,apply))
            self.group('audio',_('СИМУЛЯЦИЯ: реальные устройства и аудиозапись отключены.'))
            self.page_fingerprints=fingerprints;return
        for key,value in data.items():
            if key.endswith('_error'):self.present_fault(value)
        self.mouse_presence.update(list(dict.fromkeys(mouse_list(data.get('mice','')))),error='mice_error' in data)
        self.update_batteries()
        for page,builder in [('mouse',self.populate_mouse),('keyboard',self.keyboard_controls),('audio',self.populate_audio)]:
            if page in changed:self.clear(page);builder(data)
        self.page_fingerprints=fingerprints
    def populate_mouse(self,data):
        mice=list(dict.fromkeys(mouse_list(data.get('mice',''))))
        selected=self.mouse_presence.update(mice,error='mice_error' in data)
        g=self.group('mouse',_('Мыши через libratbag'),_('Настрой скорость движения указателя, плавность и действия кнопок.'))
        if mice:
            for device,name in mice:
                row=self.row(g,name,_('Неоднозначный идентификатор backend') if device in self.ambiguous_mouse_targets else _('Подключена'))
                button=self.button(row,_('Прочитать настройки'),lambda *unused,d=device,n=name:self.load_mouse(d,n));button.set_sensitive(device not in self.ambiguous_mouse_targets)
            selected=next((item for item in mice if item[0] not in self.ambiguous_mouse_targets and item==selected),next((item for item in mice if item[0] not in self.ambiguous_mouse_targets),None))
            if selected:self.load_mouse(selected[0],selected[1])
        else:self.row(g,_('Мышь недоступна'),_('Включи мышь и подключи USB-приёмник.'))
        row=self.row(g,_('Расширенный редактор'),_('Полный интерфейс Piper: профили и макросы.'));self.button(row,_('Открыть Piper'),lambda *unused:self.launch(['piper']))
    def populate_audio(self,data):
        ag=self.group('audio',_('Звук и микрофон'),_('Аудиоустройства Linux. Уровни применяются только по кнопке; выше 100% усиление не задаётся.'))
        self.draft_scope='audio'
        self.backup_controls(ag,'audio','all')
        found=False
        audio_sections={}
        for kind,title,cmd in [('sinks',_('Выход'),'sink'),('sources',_('Микрофон'),'source')]:
            audio_group=self.group('audio',_('Наушники и динамики') if kind=='sinks' else _('Микрофон'))
            audio_sections[kind]=audio_group
            try:devices=json.loads(data.get(kind,'[]'))
            except ValueError:devices=[]
            if not isinstance(devices,list):devices=[]
            for d in devices:
                if not isinstance(d,dict) or not isinstance(d.get('name'),str):continue
                name=d['name']
                if name.endswith('.monitor') or name.startswith('easyeffects_'):continue
                if any(x in (name+' '+d.get('description','')).lower() for x in ['logitech','pro_x','pro x']):found=True
                description=d.get('description',_('Аудиоустройство'))
                if not isinstance(d.get('volume'),dict) or not d['volume'] or type(d.get('mute')) is not bool:
                    self.row(audio_group,description,_('Данные аудиоустройства неполные; управление недоступно.'));continue
                r=self.row(audio_group,title+': '+description,_('Уровень громкости, %'))
                spin=Gtk.SpinButton.new_with_range(0,100,1);spin.set_value(min(100,volume(d)));spin.set_valign(Gtk.Align.CENTER);r.add_suffix(spin)
                draft_key='audio:'+name+':volume'
                self.bind_draft(spin,draft_key,min(100,volume(d)),spin.get_value_as_int,spin.set_value,'value-changed')
                self.button(r,_('Громкость'),lambda *unused,s=spin,n=name,c=cmd,k=draft_key:self.submit_drafts([k],lambda:self.apply(['pactl','set-'+c+'-volume',n,str(s.get_value_as_int())+'%'])))
                r=self.row(audio_group,_('Управление устройством'))
                self.button(r,_('По умолчанию'),lambda *unused,n=name,c=cmd:self.apply(['pactl','set-default-'+c,n]))
                self.button(r,_('Вкл. микр.') if d.get('mute') and cmd=='source' else (_('Включить') if d.get('mute') else _('Заглушить')),lambda *unused,n=name,c=cmd,m=d.get('mute'):self.apply(['pactl','set-'+c+'-mute',n,'0' if m else '1']))
        if not any(d.kind=='audio' for d in self.device_manager.devices):self.row(ag,_('Аудиоустройства не обнаружены'),_('Проверь подключение и открой диагностику компонентов.'))
        effects=self.group('audio',_('Обработка звука'),_('Собственные пресеты EasyEffects можно включать отсюда. Редактирование цепочки эффектов открывается в его редакторе.'))
        r=self.row(effects,_('Готовые эффекты сообщества'),_('Настройки для микрофона и наушников. Откроются в браузере.'))
        self.button(r,_('Найти готовые эффекты'),lambda *unused:self.launch(['xdg-open','https://github.com/wwmm/easyeffects/wiki/Community-Presets']))
        r=self.row(effects,_('Добавить скачанный эффект'),_('Выбери файл .json для микрофона или наушников. Затем выбери его в списке ниже.'))
        self.button(r,_('Импортировать эффект'),self.choose_preset)
        available=preset_lists()
        for kind,title in [('input',_('Пресеты микрофона')),('output',_('Пресеты наушников'))]:
            group=self.group('audio',title,_('Настройки входа и выхода сохраняются раздельно.'))
            presets=available[kind]
            if presets:
                def select(name,k=kind):
                    def completed(result):
                        self.show_operation(result)
                        if result.accepted:
                            self.preferences.setdefault('presets',{})[k]=name;save_preferences(self.preferences)
                    def load():
                        result=load_preset(k,name);self.log.operation(result);return result
                    self.job(load,completed)
                self.choice(group,_('Пресет'),presets,self.preferences.get('presets',{}).get(kind,presets[0]),select)
            else:self.row(group,_('Пресетов пока нет'),_('Импортируй файл для нужного направления или открой редактор эффектов.'))
        test_group=self.group('audio',_('Проверка микрофона'))
        try:source_devices=json.loads(data.get('sources','[]'))
        except ValueError:source_devices=[]
        test_group.add(MicrophonePanel(source_devices,self.audio_session,self.job,self.present_fault))
        r=self.row(effects,_('Эквалайзер и обработка микрофона'));self.button(r,_('Редактор эффектов'),lambda *unused:self.launch(['easyeffects']))
        r=self.row(effects,_('Звуковые эффекты'),_('Общий обход обработки влияет и на микрофон, и на наушники.'));self.button(r,_('С эффектами'),lambda *unused:self.apply(['easyeffects','-b','2']));self.button(r,_('Без эффектов'),lambda *unused:self.apply(['easyeffects','-b','1']))
        GLib.timeout_add(80,self.restore_scroll)
    def keyboard_controls(self,data):
        keyboards=[d for d in self.device_manager.devices if d.kind=='keyboard' and d.backend!='solaar-local']
        for device in keyboards:
            group=self.group('keyboard',device.name,_('Стандартный ввод Linux; дополнительные функции показаны во вкладке устройств.'))
            group.add(KeyboardDiagram())
        if not saved_keyboard() and data.get('keyboard_online') is not True:
            if not keyboards:self.group('keyboard',_('Клавиатуры не обнаружены'),_('Дополнительные аппаратные функции требуют совместимого backend.'))
            return
        kg=self.group('keyboard','Logitech G515 Lightspeed TKL',_('Выбери яркость, цвет и поведение подсветки.'))
        self.keyboard_connected=data.get('keyboard_online')
        self.update_batteries()
        self.keyboard_group=kg
        settings=keyboard_saved_settings()
        if self.keyboard_connected is not True:
            self.row(kg,_('Клавиатура не в сети') if self.keyboard_connected is False else _('Не удалось проверить связь'),_('Сохранённые настройки доступны для просмотра. Включи клавиатуру и обнови список.'))
        saved=saved_keyboard()
        for setting in settings:
            previous=saved.get(setting['key'])
            if isinstance(previous,str) and setting['key'] not in ['rgb_idle_timeout','rgb_sleep_timeout']:setting['value']=previous.capitalize() if previous.lower() in ['true','false'] else previous
        if not settings:self.row(kg,_('Настройки недоступны'),_('Подключи клавиатуру и нажми кнопку обновления вверху окна.'))
        self.draft_scope='keyboard:G515'
        labels={'rgb_control':_('Управление подсветкой из приложения'),
                'rgb_idle_timeout':_('Приглушать подсветку при бездействии'),
                'rgb_sleep_timeout':_('Выключать подсветку при бездействии')}
        translations={'true':_('Включено'),'false':_('Выключено'),'Disabled':_('Никогда'),
                      '15 Seconds':_('Через 15 секунд'),'30 Seconds':_('Через 30 секунд'),
                      '1 Minute':_('Через минуту'),'2 Minutes':_('Через 2 минуты'),
                      '5 Minutes':_('Через 5 минут'),'10 Minutes':_('Через 10 минут'),
                      '15 Minutes':_('Через 15 минут'),'30 Minutes':_('Через 30 минут')}
        for setting in settings:
            key=setting['key']
            if setting['choices'] and key in labels:
                values=setting['choices'];display=[translations.get(v,v) for v in values]
                current=setting['value'].lower() if values==['true','false'] else setting['value']
                current=translations.get(current,current)
                mapping=dict(zip(display,values))
                self.choice(kg,labels[key],display,current,
                    lambda value,k=key,m=mapping:self.apply(['solaar','config','G515',k,m[value]]))
            elif key=='brightness_control':
                values=[_('Выключена'),'12%','25%','50%','100%']
                mapping=dict(zip(values,['0','12','25','50','100']))
                current=next((k for k,v in mapping.items() if v==setting['value']),'100%')
                self.choice(kg,_('Яркость подсветки'),values,current,
                    lambda value,m=mapping:self.apply(['solaar','config','G515','brightness_control',m[value]]))
        if any(x['key']=='rgb_zone_1' for x in settings):
            r=self.row(kg,_('Режим подсветки'),_('Выбери эффект и цвет, затем нажми «Применить».'))
            modes=Gtk.DropDown.new_from_strings([_('Статичный цвет'),_('Дыхание'),_('Цикл цветов'),_('Выключено')]);modes.set_valign(Gtk.Align.CENTER);r.add_suffix(modes)
            dialog=Gtk.ColorDialog(title=_('Выбери цвет подсветки'));dialog.set_with_alpha(False)
            color=Gtk.ColorDialogButton(dialog=dialog,valign=Gtk.Align.CENTER,tooltip_text=_('Выбрать любой цвет'))
            previous=saved.get('rgb_zone_1',{})
            if not isinstance(previous,dict):previous={}
            try:
                last_mode=int(previous.get('ID',self.preferences.get('light_effect',1)))
                last_color=int(str(previous.get('color',self.preferences.get('light_color','0x44aaff'))),0)
            except (ValueError,TypeError):last_mode=1;last_color=0x44aaff
            if last_mode in [1,10,21,0]:modes.set_selected([1,10,21,0].index(last_mode))
            initial=Gdk.RGBA();initial.parse(f'#{last_color:06x}');color.set_rgba(initial);r.add_suffix(color)
            self.bind_draft(modes,'keyboard:G515/effect',last_mode,lambda:[1,10,21,0][modes.get_selected()],lambda value:modes.set_selected([1,10,21,0].index(value)),'notify::selected')
            def set_keyboard_color(value):
                rgba=Gdk.RGBA()
                if not rgba.parse(value):raise ValueError('Invalid draft color')
                color.set_rgba(rgba)
            self.bind_draft(color,'keyboard:G515/color',color.get_rgba().to_string(),lambda:color.get_rgba().to_string(),set_keyboard_color,'notify::rgba')
            palette=Gtk.Box(spacing=8,halign=Gtk.Align.CENTER,margin_top=8,margin_bottom=8)
            palette.set_accessible_role(Gtk.AccessibleRole.GROUP)
            for label,code in [(_('Белый'),'#ffffff'),(_('Красный'),'#ff3030'),(_('Оранжевый'),'#ff9500'),(_('Жёлтый'),'#ffdc00'),(_('Зелёный'),'#30d158'),(_('Голубой'),'#44aaff'),(_('Синий'),'#304ffe'),(_('Фиолетовый'),'#bf5af2'),(_('Розовый'),'#ff4f9a')]:
                rgba=Gdk.RGBA();rgba.parse(code)
                swatch=Gtk.DrawingArea(content_width=30,content_height=30)
                def paint(area,ctx,w,h,c=rgba):
                    ctx.set_source_rgba(c.red,c.green,c.blue,1);ctx.arc(w/2,h/2,min(w,h)/2-2,0,6.2832);ctx.fill()
                swatch.set_draw_func(paint)
                b=Gtk.Button(child=swatch,tooltip_text=label)
                b.update_property([Gtk.AccessibleProperty.LABEL],[label])
                b.connect('clicked',lambda *unused,c=rgba:color.set_rgba(c));palette.append(b)
            kg.add(palette)
            def color_sensitivity(*unused):color.set_sensitive(modes.get_selected() in [0,1]);palette.set_sensitive(modes.get_selected() in [0,1])
            modes.connect('notify::selected',color_sensitivity)
            color_sensitivity()
            def light(*unused):
                rgba=color.get_rgba()
                hexcolor=''.join(f'{round(c*255):02x}' for c in [rgba.red,rgba.green,rgba.blue])
                effect=[1,10,21,0][modes.get_selected()]
                value='!LEDEffectSetting {ID: '+str(effect)+', color: 0x'+hexcolor+', period: 3000, intensity: 100}'
                def saved(results):
                    self.preferences.update(light_effect=effect,light_color='0x'+hexcolor)
                    save_preferences(self.preferences)
                self.submit_drafts(['keyboard:G515/effect','keyboard:G515/color'],lambda:self.apply_batch([['solaar','config','G515','rgb_control','true'],['solaar','config','G515','rgb_zone_1',value]],after=saved))
            self.button(r,_('Применить'),light)
        self.backup_controls(kg,'keyboard','G515')
        kg.set_sensitive(self.keyboard_connected is True)
        row=self.row(kg,_('Все настройки клавиатуры'),_('Другие доступные настройки можно проверить в Solaar.'));self.button(row,_('Открыть Solaar'),lambda *unused:self.launch(['solaar','--window=show']))
    def load_mouse(self,device,name=None):
        if device in self.ambiguous_mouse_targets:
            self.present_fault(Fault(FaultCode.CONFIG,'ratbagctl','Ambiguous backend selector'));return
        self.mouse_request+=1;request=self.mouse_request
        selected_name=name or self.current_mouse_name
        def loaded(data):
            if request!=self.mouse_request:return
            self.current_mouse_name=selected_name
            self.mouse_presence.name=selected_name;self.mouse_presence.connected=True
            self.update_batteries()
            record=next((d for d in self.device_manager.devices if d.backend=='ratbagctl' and d.target==device),None)
            if record:
                record.capabilities=mouse_capabilities(data,device)
                match=re.search(r'Model:\s*[^:]+:([0-9a-fA-F]{4}):([0-9a-fA-F]{4})',data.get('text',''))
                if match:record.vid,record.pid=match.groups()
                DeviceManager.link_physical(self.device_manager.devices)
                self.device_manager.devices=DeviceManager.merge(self.device_manager.devices)
                populate_inventory(self,self.device_manager.devices,self.device_manager.faults)
            self.mouse_controls(device,data)
            GLib.timeout_add(80,self.restore_scroll)
        self.job(lambda:read_mouse(device),loaded)
    def mouse_controls(self,device,data):
        if hasattr(self,'mouse_extra') and self.mouse_extra.get_parent():self.mouse_extra.get_parent().remove(self.mouse_extra)
        g=self.group('mouse',self.current_mouse_name or _('Настройки мыши'));self.mouse_extra=g
        self.draft_scope='mouse:'+device
        self.backup_controls(g,'mouse',device)
        profiles=data['profiles']
        active=next((p for p in profiles if p['index']==data['active']),None)
        if active is None:
            self.row(g,_('Активный профиль не определён'),_('Обнови настройки мыши перед изменениями.'));return
        self.row(g,_('Мышь подключена'),_('Изменения применяются только к выбранному профилю.'))
        if len(profiles)>1:
            choices={_('Профиль ')+str(p['index']+1):str(p['index']) for p in profiles}
            def switch_profile(value):
                self.apply(['ratbagctl',device,'profile','active','set',choices[value]],after=lambda result:self.load_mouse(device))
            self.choice(g,_('Встроенный профиль'),list(choices),_('Профиль ')+str(active['index']+1),switch_profile)
        prefix=['ratbagctl',device,'profile',str(active['index'])]
        self.draft_scope='mouse:'+device+':profile:'+str(active['index'])
        resolutions=active['resolutions']
        resolution=next((r for r in resolutions if r['active']),None)
        if resolution and data['dpis']:
            values=sorted(set(data['dpis']+[resolution['dpi']]))
            self.choice(g,_('Чувствительность DPI'),values,resolution['dpi'],lambda v:self.apply([*prefix,'resolution',str(resolution['index']),'dpi','set',v]))
        if data['rates'] and active['rate']:
            self.choice(g,_('Частота опроса, Гц'),data['rates'],active['rate'],lambda v:self.apply([*prefix,'rate','set',v]))
        enabled={_('Уровень ')+str(r['index']+1)+' · '+str(r['dpi'])+' DPI':str(r['index']) for r in resolutions if not r['disabled']}
        if len(enabled)>1 and resolution:
            current=next((k for k,v in enabled.items() if v==str(resolution['index'])),next(iter(enabled)))
            def switch_dpi(value):
                self.apply([*prefix,'resolution','active','set',enabled[value]],after=lambda result:self.load_mouse(device))
            self.choice(g,_('Активный уровень чувствительности'),list(enabled),current,switch_dpi)
        names={0:_('Левая кнопка'),1:_('Правая кнопка'),2:_('Нажатие колёсика'),3:_('Боковая кнопка «Назад»'),4:_('Боковая кнопка «Вперёд»'),5:_('Кнопка переключения чувствительности')}
        if 'G502' in self.current_mouse_name:
            names.update({5:_('Кнопка снижения DPI при удержании'),6:_('Уменьшить DPI'),7:_('Увеличить DPI'),8:_('Кнопка переключения профиля'),9:_('Наклон колёсика вправо'),10:_('Наклон колёсика влево')})
        actions={_('Левый щелчок'):['button','1'],_('Правый щелчок'):['button','2'],_('Нажатие колёсика'):['button','3'],_('Назад'):['button','4'],_('Вперёд'):['button','5'],
                 _('Переключать чувствительность'):['special','resolution-cycle-up'],_('Уменьшить DPI'):['special','resolution-down'],_('Увеличить DPI'):['special','resolution-up'],
                 _('Снижение DPI при удержании'):['special','resolution-alternate'],_('Следующий профиль'):['special','profile-cycle-up'],_('G-Shift'):['special','second-mode'],
                 _('Наклон колёсика вправо'):['special','wheel-right'],_('Наклон колёсика влево'):['special','wheel-left'],
                 _('Копировать'):['macro','+KEY_LEFTCTRL','KEY_C','-KEY_LEFTCTRL'],_('Вставить'):['macro','+KEY_LEFTCTRL','KEY_V','-KEY_LEFTCTRL'],_('Вырезать'):['macro','+KEY_LEFTCTRL','KEY_X','-KEY_LEFTCTRL'],
                 _('Отменить'):['macro','+KEY_LEFTCTRL','KEY_Z','-KEY_LEFTCTRL'],_('Выделить всё'):['macro','+KEY_LEFTCTRL','KEY_A','-KEY_LEFTCTRL'],
                 **{(_('Клавиша F')+str(i)):['key',f'KEY_F{i}'] for i in range(1,13)},_('Отключить кнопку'):['disabled']}
        visual=Adw.ExpanderRow(title=_('Визуальный редактор кнопок'))
        editor_key=self.draft_scope+'/visual-editor'
        baseline=[{'index':b['index'],'action':b['action'],'macro':b['macro']} for b in active['buttons']]
        state,conflict=self.draft_store.get(editor_key,baseline)
        editor=MouseEditor(self.current_mouse_name,active['buttons'],actions,data.get('button_types',{}),
            lambda index,action:self.apply([*prefix,'button',str(index),'action','set',*action]),
            state=state if isinstance(state,dict) else None,on_draft=lambda value:self.draft_store.edit(editor_key,baseline,value) if value.get('dirty') else self.draft_store.discard(editor_key))
        if conflict:
            banner=Gtk.Label(label=_('Черновик сохранён, но состояние устройства изменилось. Проверь значения или загрузи текущее.'),wrap=True)
            banner.add_css_class('warning');editor.prepend(banner)
        visual.add_row(editor);g.add(visual)
        for button in active['buttons']:
            current=assignment_label(button,actions) or ''
            supported_actions={label:value for label,value in actions.items() if action_allowed(value,data.get('button_types',{}).get(button['index'],[]))}
            if not supported_actions:
                self.row(g,names.get(button['index'],_('Дополнительная кнопка')+' '+str(button['index']+1)),_('Сейчас: ')+(current or _('Собственное назначение')));continue
            options=list(supported_actions) if current in supported_actions else [_('Не изменять')]+list(supported_actions)
            def set_action(value,i=button['index']):
                if value==_('Не изменять'):return
                self.apply([*prefix,'button',str(i),'action','set',*actions[value]])
            self.choice(g,names.get(button['index'],_('Дополнительная кнопка')+' '+str(button['index']+1)),options,current if current in supported_actions else _('Не изменять'),set_action,_('Сейчас: ')+(current or _('Собственное назначение')))
        for led in active['leds']:
            supported=data['led_modes'].get(led['index'],[])
            if not supported:continue
            r=self.row(g,_('Зона подсветки ')+str(led['index']+1),_('Показаны данные профиля; фактический цвет может отличаться.'))
            labels={'on':_('Статичный цвет'),'breathing':_('Дыхание'),'cycle':_('Цикл цветов'),'off':_('Выключено')}
            modes=Gtk.DropDown.new_from_strings([labels[m] for m in supported]);modes.set_valign(Gtk.Align.CENTER)
            if led['mode'] in supported:modes.set_selected(supported.index(led['mode']))
            mode_key=self.draft_scope+'/led:'+str(led['index'])+':mode'
            self.bind_draft(modes,mode_key,led['mode'],lambda m=modes,s=supported:s[m.get_selected()],lambda value,m=modes,s=supported:m.set_selected(s.index(value)),'notify::selected')
            r.add_suffix(modes)
            dialog=Gtk.ColorDialog(title=_('Выбери цвет подсветки'));dialog.set_with_alpha(False)
            color=Gtk.ColorDialogButton(dialog=dialog,valign=Gtk.Align.CENTER,tooltip_text=_('Выбрать любой цвет'))
            rgba=Gdk.RGBA();rgba.parse('#'+(led['color'] or 'ffffff'));color.set_rgba(rgba);r.add_suffix(color)
            color_key=self.draft_scope+'/led:'+str(led['index'])+':color'
            def set_color(value,c=color):
                rgba=Gdk.RGBA()
                if not rgba.parse(value):raise ValueError('Invalid draft color')
                c.set_rgba(rgba)
            self.bind_draft(color,color_key,color.get_rgba().to_string(),lambda c=color:c.get_rgba().to_string(),set_color,'notify::rgba')
            color.set_sensitive(led.get('depth')=='rgb')
            def write_light(*unused,l=led,m=modes,c=color,available=supported,keys=(mode_key,color_key)):
                rgba=c.get_rgba();rgb=''.join(f'{round(v*255):02x}' for v in [rgba.red,rgba.green,rgba.blue]);mode=available[m.get_selected()]
                command=[*prefix,'led',str(l['index']),'set']
                commands=[]
                if mode in ['on','breathing'] and l.get('depth')=='rgb':commands.append([*command,'color',rgb])
                commands.append([*command,'mode',mode])
                self.submit_drafts(keys,lambda:self.apply_batch(commands,after=lambda results:self.load_mouse(device)))
            self.button(r,_('Применить'),write_light)

if __name__=='__main__':Center().run([sys.argv[0]])
