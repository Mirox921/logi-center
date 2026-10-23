"""Capability-driven inventory presentation shared by real and simulated devices."""
import json
import gi
gi.require_version('Gtk','4.0');gi.require_version('Adw','1')
from gi.repository import Gtk,Adw,GLib
from i18n import tr as _

NAMES={'dpi':'DPI','polling_rate':'Polling rate','profiles':'Hardware profiles','buttons':'Buttons','macros':'Macros','lighting':'Lighting','standard_input':'Standard input','sidetone':'Sidetone','battery_status':'Battery'}

def capability_text(cap):
    support=_('Обнаружено') if cap.supported is True else _('Не поддерживается устройством') if cap.supported is False else _('Поддержка не проверена')
    access=_('Чтение и изменение') if cap.writable and cap.readable else _('Изменение без чтения') if cap.writable else _('Только чтение') if cap.readable else _('Только информация backend')
    verify=_('Возможно повторное чтение') if cap.verifiable else _('Аппаратное подтверждение недоступно')
    return support+' · '+access+' · '+verify+'\n'+_('Источник: ')+cap.source+' · '+cap.backend+('\n'+cap.limitation if cap.limitation else '')

def populate_inventory(center,devices,faults=()):
    center.clear('devices')
    if not devices:
        center.group('devices',_('Устройства не обнаружены'),_('Проверь подключение и открой диагностику компонентов.'))
    for device in devices:
        title=(_('СИМУЛЯЦИЯ · ') if device.simulated else '')+device.name
        group=center.group('devices',title,device.kind+' · '+', '.join(device.backends)+' · '+(_('Подключена') if device.connected is True else _('Не в сети') if device.connected is False else _('Связь не подтверждена')))
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
        if not device.capabilities:center.row(group,_('Возможности не прочитаны'),_('Наличие устройства не означает поддержку настройки через backend.'))
        for cap in device.capabilities:
            name=NAMES.get(cap.name,cap.name.rsplit(':',1)[-1] if ':' in cap.name else cap.name.replace('_',' '))
            value_text='\n'+_('Текущее значение: ')+str(cap.value) if cap.readable and type(cap.value) in [int,float,bool] else ''
            row=center.row(group,cap.label or name,capability_text(cap)+value_text);row.set_subtitle_lines(0)
            # Only implemented operations receive a control. Unsupported capabilities
            # remain diagnostic; they never become an enabled placebo editor.
            if device.simulated and cap.writable:
                entry=Gtk.Entry(text=json.dumps(cap.value),width_chars=12);row.add_suffix(entry)
                def simulate(*unused,d=device,c=cap,e=entry):
                    try:value=json.loads(e.get_text())
                    except ValueError as error:center.present_fault(error);return
                    center.job(lambda:center.simulation_adapter.apply(d.target,c.name,value),center.show_operation)
                center.button(row,_('Применить'),simulate)
            if cap.writable and cap.plan is not None and not device.simulated:
                add_control(center,row,device,cap)
        for fault in device.faults:center.row(group,_('Ошибка чтения'),str(fault))
    for fault in faults:center.row(center.group('devices',_('Диагностика backend')),fault.component,str(fault))

def add_control(center,row,device,cap):
    """Render common scalar editors from provider metadata and provider-owned plans."""
    key='device:'+device.id+':'+cap.name
    if cap.choices:
        values=cap.choices;widget=Gtk.DropDown.new_from_strings([str(v) for v in values])
        observed=cap.value if cap.value in values else values[0]
        getter=lambda:values[widget.get_selected()]
        setter=lambda value:widget.set_selected(values.index(value))
        signal='notify::selected'
    elif cap.minimum is not None and cap.maximum is not None:
        widget=Gtk.SpinButton.new_with_range(cap.minimum,cap.maximum,1)
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
            if current.minimum is not None and not current.minimum<=value<=current.maximum:raise ValueError('Value is outside capability range')
            if current.plan is None:raise ValueError('Capability plan is no longer available')
            plan=current.plan(value)
            center.submit_drafts([key],lambda:center.apply(plan.command,verified_plan=plan))
        except Exception as error:center.present_fault(error)
    center.button(row,_('Загрузить текущее'),lambda *unused:(center.draft_store.discard(key),setter(observed)))
    center.button(row,_('Применить'),apply)
