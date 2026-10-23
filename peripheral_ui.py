"""Shared physical-device selectors, status and capability-driven control pages."""
from datetime import datetime,timezone
import gi
gi.require_version('Gtk','4.0');gi.require_version('Adw','1')
from gi.repository import Gtk,Adw
from i18n import tr as _
from device_ui import add_control,add_backup_controls,NAMES


from device_status import battery_text,status_text


def populate(center,kind,data):
    page='mouse' if kind=='mouse' else 'keyboard'
    center.clear(page)
    devices=center.device_manager.active(kind,simulation=center.simulation)
    if not hasattr(center,'selected_peripherals'):center.selected_peripherals={}
    if not devices:
        center.group(page,_('Мыши не обнаружены') if kind=='mouse' else _('Клавиатуры не обнаружены'),_('Подключи устройство. Сохранённые черновики останутся доступны после подключения.'))
        return
    selected=next((d for d in devices if d.id==center.selected_peripherals.get(kind)),devices[0])
    center.selected_peripherals[kind]=selected.id
    if len(devices)>1:
        chooser=Gtk.DropDown.new_from_strings([d.name for d in devices]);chooser.set_selected(devices.index(selected));chooser.set_hexpand(True)
        chooser.set_tooltip_text(_('Выбрать устройство'))
        def choose(widget,*unused):
            center.mouse_request+=1
            center.selected_peripherals[kind]=devices[widget.get_selected()].id
            populate(center,kind,data)
        chooser.connect('notify::selected',choose);center.pages[page].append(chooser)
    header=Adw.PreferencesGroup(title=selected.name,description=status_text(selected));center.pages[page].append(header)
    vendor={'3837':'MCHOSE','41e4':'MCHOSE','046d':'Logitech','1532':'Razer','1b1c':'Corsair','1038':'SteelSeries'}.get(selected.vid,selected.vid.upper() if selected.vid else '')
    profile=next((c.value for c in selected.capabilities if c.name=='profiles' and c.readable),None)
    description=(vendor+' · ' if vendor else '')+status_text(selected)
    if profile is not None:description+=' · '+_('Встроенный профиль')+' '+str(profile)
    header.set_description(description)
    if not hasattr(center,'peripheral_battery_rows'):center.peripheral_battery_rows={}
    center.peripheral_battery_rows.pop(kind,None)
    if any(c.name=='battery_status' for c in selected.capabilities) or selected.connection=='bluetooth' or any(f.code.value=='permission_denied' for f in selected.faults):
        battery_row=center.row(header,_('Аккумулятор'),battery_text(selected))
        center.peripheral_battery_rows[kind]=(selected.id,battery_row)
    for fault in selected.faults:center.row(header,_('Ошибка чтения'),str(fault))
    # Detailed libratbag editor remains intact; provider controls augment it below.
    if kind=='mouse' and 'ratbagctl' in selected.backends:
        targets=selected.targets.get('ratbagctl',[])
        if len(targets)==1 and targets[0] not in center.ambiguous_mouse_targets:center.load_mouse(targets[0],selected.name)
    body=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=20);center.pages[page].append(body)
    tabs=Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
    if kind=='keyboard':
        navigation=Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,min_children_per_line=1,max_children_per_line=5,homogeneous=True,column_spacing=6,row_spacing=6);body.append(navigation);body.append(tabs)
    sections={}
    def section(key,title):
        if key in sections:return sections[key]
        group=Adw.PreferencesGroup(title=title)
        if kind=='keyboard':
            wrap=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);wrap.append(group);tabs.add_titled(wrap,key,title)
            button=Gtk.Button(label=title);button.connect('clicked',lambda *unused,k=key:tabs.set_visible_child_name(k));navigation.insert(button,-1)
            def update(*unused,b=button,k=key):
                if tabs.get_visible_child_name()==k:b.add_css_class('suggested-action')
                else:b.remove_css_class('suggested-action')
            tabs.connect('notify::visible-child-name',update);update()
        else:body.append(group)
        sections[key]=group;return group
    overview=section('overview',_('Обзор'))
    center.row(overview,_('Возможности устройства'),_('Доступны только настройки, предоставленные обнаруженными backend.'))
    if any(c.readable and c.backend in ['mchose','mchose-ace68','openrazer','openrgb'] for c in selected.capabilities):add_backup_controls(center,overview,selected)
    if kind=='keyboard' and 'mchose-ace68' in selected.backends:
        from keyboard_ui import MagneticKeyboardEditor
        section('keys',_('Клавиши')).add(MagneticKeyboardEditor(center,selected))
    for cap in selected.capabilities:
        if kind=='mouse' and cap.readable and not cap.writable and cap.name in ['dpi_stages','motion_sync','ripple','angle_snap']:
            value=', '.join(map(str,cap.value)) if isinstance(cap.value,list) else str(cap.value)
            center.row(section('advanced',_('Дополнительно')),_(NAMES.get(cap.name,cap.name)),value+' · '+_('Только чтение'))
        if cap.backend=='ratbagctl' or not cap.writable or cap.plan is None:continue
        if isinstance(cap.value,dict):continue
        if cap.name in ['lighting','lighting_mode','brightness','lighting_speed','lighting_palette'] or cap.name.startswith('lighting_zone_'):key,title='lighting',_('Подсветка')
        elif cap.name=='profiles':key,title='profiles',_('Профили')
        elif cap.name in ['dpi','stage','polling_rate','dpi_x','dpi_y'] and kind=='mouse':key,title='pointer',_('Чувствительность и скорость')
        else:key,title='advanced',_('Дополнительно')
        row=center.row(section(key,title),_(NAMES.get(cap.name,cap.name.replace('_',' '))))
        add_control(center,row,selected,cap)
    if kind=='keyboard' and 'G515' in selected.name and data.get('keyboard_online') is True:center.legacy_keyboard_controls(data)
    row=center.row(overview,_('Диагностика возможностей'),_('Почему некоторые настройки недоступны'))
    center.button(row,_('Открыть'),lambda *unused:center.stack.set_visible_child_name('devices'))
    if kind=='keyboard':
        if not hasattr(center,'keyboard_sections'):center.keyboard_sections={}
        previous=center.keyboard_sections.get(selected.id,'overview');tabs.set_visible_child_name(previous if previous in sections else 'overview')
        tabs.connect('notify::visible-child-name',lambda *unused:center.keyboard_sections.update({selected.id:tabs.get_visible_child_name()}))
    center.peripheral_devices=devices
