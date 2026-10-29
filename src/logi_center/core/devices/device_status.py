"""Pure, provenance-aware device status formatting; no GTK or hardware calls."""
from datetime import datetime,timezone
from logi_center.i18n import tr as _

def battery_text(device):
    if device.connected is False:return _('Не в сети')
    if any(f.code.value=='permission_denied' for f in device.faults):return _('Нет доступа к заряду')
    cap=next((c for c in device.capabilities if c.name=='battery_status'),None)
    if cap is None:return ''
    if cap.value is None:
        if cap.supported is not True:return ''
        return _('Заряд: нет данных')
    else:
        value=cap.value
        text=str(value)+'%' if type(value) in [int,float] and 0<=value<=100 else str(value)
    stale=False
    if cap.source not in ['device','kernel']:
        text=_('Сохранённое значение: ')+text
    elif cap and cap.observed_at:
        try:
            stale=(datetime.now(timezone.utc)-datetime.fromisoformat(cap.observed_at)).total_seconds()>90
            if stale:text=_('Последнее значение: ')+text+' · '+_('Устарело')
        except ValueError:text+=' · '+_('Свежесть неизвестна')
    if any(f.component==cap.backend for f in device.faults):text+=' · '+_('Последнее чтение не удалось')
    charging=next((c for c in device.capabilities if c.name=='charging'),None)
    if charging and charging.value is True and not stale:
        fresh=True
        if charging.observed_at:
            try:fresh=(datetime.now(timezone.utc)-datetime.fromisoformat(charging.observed_at)).total_seconds()<=90
            except ValueError:fresh=False
        if fresh:text+=_(' · заряжается')
    return text


def battery_icon(device):
    if device.connected is False:return 'network-offline-symbolic'
    if any(f.code.value=='permission_denied' for f in device.faults):return 'battery-missing-symbolic'
    cap=next((c for c in device.capabilities if c.name=='battery_status'),None)
    charging=next((c for c in device.capabilities if c.name=='charging'),None)
    if charging and charging.value is True and charging.source in ['device','kernel']:
        try:
            if not charging.observed_at or (datetime.now(timezone.utc)-datetime.fromisoformat(charging.observed_at)).total_seconds()<=90:return 'battery-good-charging-symbolic'
        except ValueError:pass
    if cap is None or cap.value is None:return 'battery-missing-symbolic'
    if cap.observed_at:
        try:
            if (datetime.now(timezone.utc)-datetime.fromisoformat(cap.observed_at)).total_seconds()>90:return 'battery-missing-symbolic'
        except ValueError:return 'battery-missing-symbolic'
    return 'battery-good-symbolic'


def status_text(device):
    status=_('Подключено') if device.connected is True else _('Подключение не подтверждено')
    transport={'usb':'USB','bluetooth':'Bluetooth','wireless':_('Беспроводное подключение'),
               '2.4g':_('Беспроводное 2,4 ГГц'),'internal':_('Встроенное устройство')}.get(device.connection,_('Тип соединения неизвестен'))
    return status+' · '+transport


def user_fault_summary(fault):
    """Short localized status for primary pages; backend detail stays in diagnostics."""
    summaries={
        'missing':_('Требуется дополнительный компонент'),
        'unavailable':_('Компонент сейчас недоступен'),
        'permission_denied':_('Нет доступа к устройству'),
        'unsupported':_('Функция недоступна'),
        'device_unsupported':_('Функция не поддерживается этим устройством'),
        'backend_unsupported':_('Backend не поддерживает операцию'),
        'disconnected':_('Не удалось связаться с устройством'),
        'timeout':_('Устройство не ответило вовремя'),
        'cancelled':_('Операция отменена'),
        'connection':_('Ошибка связи с устройством'),
        'config':_('Не удалось прочитать настройки устройства'),
        'internal':_('Не удалось прочитать настройки устройства'),
    }
    return summaries.get(getattr(fault.code,'value',''),_('Не удалось прочитать настройки устройства'))


