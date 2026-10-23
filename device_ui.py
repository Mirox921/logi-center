"""Capability-driven inventory presentation shared by real and simulated devices."""
import json
import gi
gi.require_version('Gtk','4.0');gi.require_version('Adw','1')
from gi.repository import Gtk,Adw,GLib,Gdk
from i18n import tr as _
from devices import matches_name

NAMES={'dpi_x':'DPI по горизонтали','dpi_y':'DPI по вертикали','backend_features':'Возможности, сообщённые backend','dpi':'Чувствительность DPI','polling_rate':'Частота опроса, Гц','profiles':'Встроенный профиль','buttons':'Кнопки','macros':'Макросы','lighting':'Подсветка','standard_input':'Стандартный ввод','sidetone':'Слышимость своего голоса','battery_status':'Заряд аккумулятора','volume':'Громкость','mute':'Без звука','lighting_mode':'Эффект подсветки','brightness':'Яркость','zones':'Зоны подсветки','stage':'Ступень DPI','dpi_stages':'Ступени DPI','debounce':'Задержка устранения дребезга, мс','sleep':'Таймер сна (единицы протокола)','motion_sync':'Синхронизация сенсора','ripple':'Подавление дрожания','angle_snap':'Выпрямление линий'}

NAMES.update({'firmware_version':'Версия прошивки','usb_release':'Версия USB-устройства','keyboard_layout':'Раскладка клавиатуры','actuation':'Точка срабатывания','rapid_trigger':'Rapid Trigger','rt_press':'RT при нажатии','rt_release':'RT при отпускании','press_dead_zone':'Верхняя мёртвая зона','release_dead_zone':'Нижняя мёртвая зона','key_details':'Параметры магнитных переключателей','lighting_palette':'Палитра подсветки','lighting_speed':'Скорость эффекта','socd':'SOCD / Snap Tap','dks':'Динамическое нажатие (DKS)','mod_tap':'Mod Tap','toggle_key':'Toggle Key','key_remap':'Переназначение клавиш','layers':'Слои клавиатуры'})

def capability_text(cap):
    support=_('Обнаружено') if cap.supported is True else _('Не поддерживается устройством') if cap.supported is False else _('Поддержка не проверена')
    access=_('Чтение и изменение') if cap.writable and cap.readable else _('Изменение без чтения') if cap.writable else _('Только чтение') if cap.readable else _('Только информация backend')
    verify=_('Возможно повторное чтение') if cap.verifiable else _('Аппаратное подтверждение недоступно')
    return support+' · '+access+' · '+verify+'\n'+_('Источник: ')+cap.source+' · '+cap.backend+('\n'+cap.limitation if cap.limitation else '')

def populate_inventory(center,devices,faults=()):
    center.clear('devices')
    search=Gtk.SearchEntry(placeholder_text=_('Поиск устройств по названию'),hexpand=True)
    search.set_text(getattr(center,'inventory_query',''))
    center.pages['devices'].append(search)
    center.inventory_search=search
    device_groups=[]
    empty=Gtk.Label(label=_('Устройства с таким названием не найдены'),wrap=True,visible=False,margin_top=16)
    empty.add_css_class('dim-label')
    def filter_devices(*unused):
        if center.inventory_search is not search:return
        center.inventory_query=search.get_text()
        found=False
        for name,group in device_groups:
            visible=matches_name(name,center.inventory_query);group.set_visible(visible);found=found or visible
        empty.set_visible(bool(devices) and not found)
    search.connect('search-changed',filter_devices)
    if not devices:
        center.group('devices',_('Устройства не обнаружены'),_('Проверь подключение и открой диагностику компонентов.'))
    for device in devices:
        title=(_('СИМУЛЯЦИЯ · ') if device.simulated else '')+device.name
        group=center.group('devices',title,device.kind+' · '+', '.join(device.backends)+' · '+(_('Подключена') if device.connected is True else _('Не в сети') if device.connected is False else _('Связь не подтверждена')))
        device_groups.append((device.name,group))
        if device.backend=='solaar-local' and not device.simulated:
            from backend import saved_solaar_devices
            from solaar_adapter import probe,choice_plan
            # Find a single local record; model names alone are never a write selector.
            records=[r for r in saved_solaar_devices() if r.get('_NAME')==device.name]
            if len(records)==1:
                row=center.row(group,_('Проверить отдельные настройки Solaar'),_('Явный запрос чтения. Только сообщённые backend варианты станут доступны для изменения.'))
                def inspect(*unused,d=device,r=records[0]):
                    def loaded(outcome):
                        target,caps,errors=outcome;d.target=target;d.backend='solaar';d.backends=['solaar'];d.targets={'solaar':[target]};d.capabilities=caps;d.faults=errors;d.connected=True if caps else None
                        populate_inventory(center,center.device_manager.devices,center.device_manager.faults)
                    center.job(lambda:probe(r),loaded)
                center.button(row,_('Проверить'),inspect)
        if device.kind in ['mouse','keyboard']:
            destination='mouse' if device.kind=='mouse' else 'keyboard'
            center.button(center.row(group,_('Настройки устройства')),_('Открыть'),lambda *unused,p=destination:center.stack.set_visible_child_name(p))
        elif any(c.backend in ['mchose','openrgb','openrazer','mchose-ace68'] and c.readable for c in device.capabilities):add_backup_controls(center,group,device)
        if not device.capabilities:center.row(group,_('Возможности не прочитаны'),_('Наличие устройства не означает поддержку настройки через backend.'))
        for cap in device.capabilities:
            setting=cap.name.rsplit(':',1)[-1]
            name=_(NAMES.get(setting,setting.replace('_',' ')))
            if cap.label:name=cap.label+' · '+name
            value_text='\n'+_('Текущее значение: ')+str(cap.value) if cap.readable and type(cap.value) in [int,float,bool] else ''
            if cap.readable and isinstance(cap.value,str):value_text='\n'+_('Текущее значение: ')+cap.value
            if cap.backend=='mchose-ace68' and isinstance(cap.value,dict):value_text='\n'+_('Настройка отдельных клавиш доступна во вкладке «Клавиатура».')
            if setting in ['dpi_stages','backend_features'] and isinstance(cap.value,list):value_text='\n'+_('Текущее значение: ')+', '.join(str(v) for v in cap.value)
            if setting=='zones' and isinstance(cap.value,list):value_text='\n'+', '.join(z['name']+' ('+str(z['leds'])+')' for z in cap.value)
            row=center.row(group,name,capability_text(cap)+value_text);row.set_subtitle_lines(0)
            # Only implemented operations receive a control. Unsupported capabilities
            # remain diagnostic; they never become an enabled placebo editor.
            if device.simulated and cap.writable:
                entry=Gtk.Entry(text=json.dumps(cap.value),width_chars=12);row.add_suffix(entry)
                def simulate(*unused,d=device,c=cap,e=entry):
                    try:value=json.loads(e.get_text())
                    except ValueError as error:center.present_fault(error);return
                    center.job(lambda:center.simulation_adapter.apply(d.target,c.name,value),center.show_operation)
                center.button(row,_('Применить'),simulate)
            if cap.writable and cap.plan is not None and not device.simulated and device.kind not in ['mouse','keyboard']:
                add_control(center,row,device,cap)
        for fault in device.faults:center.row(group,_('Ошибка чтения'),str(fault))
    center.pages['devices'].append(empty)
    center.inventory_groups=device_groups;center.inventory_empty=empty
    filter_devices()
    components=center.group('devices',_('Backend и компоненты'),_('Наличие устройства не означает поддержку настройки через backend.'))
    center.button(center.row(components,_('Диагностика компонентов')),_('Проверить'),lambda *unused:center.job(__import__('diagnostics').collect,center.show_diagnostics))
    for fault in faults:center.row(components,fault.component,str(fault))

def add_control(center,row,device,cap):
    """Render common scalar editors from provider metadata and provider-owned plans."""
    key='device:'+device.id+':'+cap.name
    if cap.choices:
        values=cap.choices;widget=Gtk.DropDown.new_from_strings([str(v) for v in values])
        observed=cap.value if cap.value in values else values[0]
        getter=lambda:values[widget.get_selected()]
        setter=lambda value:widget.set_selected(values.index(value))
        signal='notify::selected'
    elif cap.name=='lighting' or cap.name.startswith('lighting_zone_'):
        dialog=Gtk.ColorDialog(title=_('Выбери цвет подсветки'));dialog.set_with_alpha(False)
        widget=Gtk.ColorDialogButton(dialog=dialog)
        observed=cap.value if isinstance(cap.value,list) and len(cap.value)==3 else [255,255,255]
        def setter(value):
            color=Gdk.RGBA();color.parse('#'+''.join(f'{v:02x}' for v in value));widget.set_rgba(color)
        getter=lambda:[round(getattr(widget.get_rgba(),channel)*255) for channel in ['red','green','blue']]
        signal='notify::rgba'
    elif cap.minimum is not None and cap.maximum is not None:
        widget=Gtk.SpinButton.new_with_range(cap.minimum,cap.maximum,cap.step)
        observed=cap.value if isinstance(cap.value,(int,float)) else cap.minimum
        getter=widget.get_value_as_int;setter=widget.set_value;signal='value-changed'
    else:return
    center.bind_draft(widget,key,observed,getter,setter,signal);row.add_suffix(widget)
    def apply(*unused):
        try:
            # Re-resolve before submission; stale or conflicting controls cannot route a write.
            current=center.device_manager.route(device.id,cap.name,cap.backend)
            value=getter()
            if current.choices and value not in current.choices:raise ValueError('Value is outside capability choices')
            if current.minimum is not None and (not current.minimum<=value<=current.maximum or (value-current.minimum)%current.step):raise ValueError('Value is outside capability range/step')
            if current.plan is None:raise ValueError('Capability plan is no longer available')
            plan=current.plan(value)
            center.submit_drafts([key],lambda:center.apply(plan.command,verified_plan=plan,after=(lambda result:center.refresh(force=False)) if cap.name in ['profiles','lighting_mode'] else None))
        except Exception as error:center.present_fault(error)
    reset=center.button(row,_('Загрузить текущее'),lambda *unused:(center.draft_store.discard(key),setter(observed)))
    reset.set_child(Gtk.Image(icon_name='edit-undo-symbolic'));reset.set_tooltip_text(_('Загрузить текущее'))
    submit=center.button(row,_('Применить'),apply);submit.set_child(Gtk.Image(icon_name='object-select-symbolic'));submit.set_tooltip_text(_('Применить'))


def add_backup_controls(center,group,device):
    import capability_backup as backup
    row=center.row(group,_('Резервная копия'),_('Источник данных указан в файле; локальные настройки не являются аппаратной копией.'))
    def save(*unused):
        dialog=Gtk.FileDialog(title=_('Сохранить настройки устройства'),initial_name='device-capabilities.json')
        def chosen(dialog,result):
            try:path=dialog.save_finish(result).get_path()
            except GLib.Error:return
            if path:center.job(lambda:backup.write(backup.capture(device),path),lambda unused:center.toast.add_toast(Adw.Toast(title=_('Копия сохранена. Источник: ')+device.backend)))
        dialog.save(center.win,None,chosen)
    def load(*unused):
        dialog=Gtk.FileDialog(title=_('Восстановить настройки'))
        def chosen(dialog,result):
            try:path=dialog.open_finish(result).get_path()
            except GLib.Error:return
            if path:center.job(lambda:backup.preview(backup.read(path),backup.capture(device),device),lambda preview:center.restore_dialog(preview,device,restorer=backup.restore))
        dialog.open(center.win,None,chosen)
    save_button=center.button(row,_('Сохранить настройки устройства'),save);save_button.set_child(Gtk.Image(icon_name='document-save-symbolic'));save_button.set_tooltip_text(_('Сохранить настройки устройства'))
    load_button=center.button(row,_('Восстановить настройки'),load);load_button.set_child(Gtk.Image(icon_name='document-open-symbolic'));load_button.set_tooltip_text(_('Восстановить настройки'))
