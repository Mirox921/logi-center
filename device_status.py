"""Pure, provenance-aware device status formatting; no GTK or hardware calls."""
from datetime import datetime,timezone
from i18n import tr as _

def battery_text(device):
    if device.connected is False:return _('Не в сети')
    if any(f.code.value=='permission_denied' for f in device.faults):return _('Нет доступа к заряду')
    cap=next((c for c in device.capabilities if c.name=='battery_status'),None)
    if cap is None or cap.value is None:
        if any(f.code.value=='permission_denied' for f in device.faults):return _('Нет доступа к заряду')
        return _('Заряд недоступен')
    value=cap.value
    text=str(value)+'%' if type(value) in [int,float] and 0<=value<=100 else str(value)
    if cap.source not in ['device','kernel']:text+=' · '+_('Сохранённое значение')
    elif cap.observed_at:
        try:
            if (datetime.now(timezone.utc)-datetime.fromisoformat(cap.observed_at)).total_seconds()>90:text+=' · '+_('Устаревшее значение')
        except ValueError:text+=' · '+_('Свежесть неизвестна')
    if any(f.component==cap.backend for f in device.faults):text+=' · '+_('Последнее чтение не удалось')
    charging=next((c.value for c in device.capabilities if c.name=='charging'),False)
    if charging is True:text+=_(' · заряжается')
    return text


def status_text(device):
    status=_('Подключена') if device.connected is True else _('Связь не подтверждена')
    transport={'usb':'USB','bluetooth':'Bluetooth','internal':_('Встроенное устройство')}.get(device.connection,_('Тип соединения неизвестен'))
    return status+' · '+transport+' · '+', '.join(device.backends)


