"""Pure battery display evidence; no hardware access or toolkit imports."""
from datetime import datetime,timezone
from i18n import tr as _


def _age(cap):
    try:return (datetime.now(timezone.utc)-datetime.fromisoformat(cap.observed_at)).total_seconds()
    except (ValueError,TypeError,AttributeError):return float('inf')


def _faults(device,cap):
    return [fault for fault in device.faults if fault.component==cap.backend]


def _fresh(device,cap):
    return ((cap.source in ('device','kernel') or device.simulated and cap.source=='simulation')
            and -5<=_age(cap)<=90 and not _faults(device,cap))


def _number(value):
    return type(value) in (int,float) and 0<=value<=100


def _value(value):
    return str(int(value) if type(value) is float and value.is_integer() else value)+'%'


def battery_display(device):
    caps=[cap for cap in device.capabilities if cap.name=='battery_status']
    levels={'full':'Высокий заряд','high':'Высокий заряд','normal':'Средний заряд',
            'low':'Низкий заряд','critical':'Критический заряд'}
    current=[cap for cap in caps if _fresh(device,cap) and (_number(cap.value) or str(cap.value).lower() in levels)]
    current.sort(key=_age)
    cap=current[0] if current else next(iter(sorted([c for c in caps if _number(c.value)],key=_age)),None)
    charging_caps=sorted([c for c in device.capabilities if c.name=='charging' and type(c.value) is bool and _fresh(device,c)],key=_age)
    charging=bool(charging_caps and charging_caps[0].value is True and device.connected is True)
    state='unknown';percent=-1;label=_('Нет данных');text=_('Заряд: нет данных');detail=text
    denied=any(getattr(f.code,'value','')=='permission_denied' for c in caps for f in _faults(device,c))
    if device.connected is False:
        state='disconnected';label=_('Не в сети');text=detail=label;charging=False
    elif current:
        state='current'
        if _number(cap.value):percent=cap.value;label=text=_value(cap.value)
        else:label=text=_(levels[str(cap.value).lower()])
        detail=text
    elif denied:
        state='denied';label=_('Нет доступа');text=detail=_('Нет доступа к заряду')
    elif cap:
        state='cached' if cap.source not in ('device','kernel','simulation') else 'stale'
        label=_('Последний заряд: %1').replace('%1',_value(cap.value))
        text=_('Сохранённое значение: ')+_value(cap.value)
        detail=text+' · '+_('Актуальность не подтверждена')
    if charging:
        detail+=' · '+_('Заряжается')
    return {'batteryPercent':percent,'batteryLabel':label,'batteryText':text,'batteryDetail':detail,
            'batteryState':state,'batteryAvailable':bool(caps),'charging':charging,
            'chargingKnown':bool(charging_caps),'batterySource':cap.source if cap else 'unavailable',
            'batteryObservedAt':cap.observed_at if cap else ''}
