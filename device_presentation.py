"""Toolkit-free presentation helpers shared by GTK and Qt frontends."""
import re
from datetime import datetime, timezone

from device_status import battery_text, battery_icon
from device_artwork import DeviceArtworkProvider, artwork_key, audio_subtype, is_builtin, local_identity, confirmed_touchpad
from battery_presentation import battery_display
from i18n import tr as _

MODEL_IDS = {
    ('3837', '1001'): 'MCHOSE K7 Ultra',
    ('41e4', '2116'): 'MCHOSE Ace68-II',
}
SIMULATION_NAMES = {
    'simple-mouse': 'Простая мышь · симуляция',
    'gaming-mouse': 'Игровая мышь · симуляция',
    'rgb-keyboard': 'RGB-клавиатура · симуляция',
    'plain-keyboard': 'Обычная клавиатура · симуляция',
    'usb-headset': 'USB-гарнитура · симуляция',
    'wireless-headset': 'Беспроводная гарнитура · симуляция',
    'partial': 'Частично доступное устройство · симуляция',
    'disconnect': 'Отключение во время операции · симуляция',
    'logitech': 'Тестовая мышь Logitech · симуляция',
    'mchose': 'Тестовая мышь MCHOSE · симуляция',
    'razer': 'Тестовая мышь Razer · симуляция',
    'corsair': 'Тестовая клавиатура Corsair · симуляция',
    'steelseries': 'Тестовая мышь SteelSeries · симуляция',
    'wireless-charging-mouse': 'Беспроводная мышь · зарядка · симуляция',
    'unsupported': 'Устройство без настройки · симуляция',
}

_SENSITIVE_TEXT = re.compile(
    r'(?i)(?:/dev/[^\s]+|/sys/[^\s]+|\b[0-9a-f]{4}:[0-9a-f]{4}\b|'
    r'\b(?:serial|sn)[=: ]+[a-z0-9-]+|\b(?:MSNB|ELAN|SYNA|PNP)\w*:\d{2}\b)'
)
_SPACE = re.compile(r'\s+')


def _normal(value):
    return _SPACE.sub(' ', str(value or '').strip())


def model_name(device, user_name=''):
    """Return a readable name; device transport, never its raw name, marks built-ins."""
    preferred = _normal(user_name)
    if preferred:
        return preferred[:48]
    if device.simulated:
        return _(SIMULATION_NAMES.get(str(device.target), 'Симулированное устройство'))
    vid, pid = str(device.vid or '').lower(), str(device.pid or '').lower()
    if (vid, pid) in MODEL_IDS:
        return MODEL_IDS[(vid, pid)]
    name = _normal(device.name)
    lower = name.casefold()
    for model in ('Logitech G502 HERO', 'Logitech G305', 'Logitech G515 LIGHTSPEED TKL',
                  'Logitech G PRO X', 'MCHOSE K7 Ultra', 'MCHOSE Ace68-II'):
        if model.casefold() in lower:
            return model
    if is_builtin(device):
        if device.kind == 'keyboard':
            return _('Встроенная клавиатура')
        if device.kind in ('mouse','touchpad'):
            return _('Встроенная сенсорная панель') if artwork_key(device) == 'touchpad' else _('Встроенный указатель')
    if device.kind == 'audio':
        subtype = audio_subtype(device)
        route = re.search(r'\b(?:hdmi|displayport|display port)\s*(\d+)\b', name, re.I)
        if subtype in ('display_audio','display_hdmi','display_dp'):
            ordinal = f" {route.group(1)}" if route else ''
            direction = _('Выход') if 'output' in lower else ''
            return f"HDMI / DisplayPort{ordinal} {direction}".strip()
        if subtype == 'microphone':
            return _('Микрофон')
        if subtype == 'headset':
            return _('Гарнитура')
        if subtype == 'headphones':
            return _('Наушники')
        if subtype == 'speakers':
            return _('Динамики')
        if subtype == 'usb_audio':
            return _('USB-аудиоустройство')
        if subtype == 'bluetooth_audio':
            return _('Bluetooth-аудиоустройство')
        if subtype == 'builtin_audio':
            return _('Встроенное аудиоустройство')
    safe = _normal(_SENSITIVE_TEXT.sub('', name)).strip(' -_:')
    if len(safe) > 64 or any(token in safe.casefold() for token in ('/dev/', '/sys/', 'hidraw', 'event')):
        safe = ''
    if safe and safe.casefold() not in {'mouse', 'keyboard', 'input', 'audio output', 'audio source'}:
        return safe
    return {
        'mouse': _('Неизвестная мышь'), 'touchpad': _('Сенсорная панель'), 'keyboard': _('Неизвестная клавиатура'),
        'audio': _('Неизвестное аудиоустройство'),
    }.get(device.kind, _('Неизвестное устройство'))


def device_category(device):
    if device.kind == 'audio':
        return 'audio'
    if device.kind in ('mouse', 'touchpad', 'keyboard'):
        if is_builtin(device):
            return 'builtin'
        if device.connection in ('usb', 'bluetooth', '2.4g', 'wireless'):
            return 'external'
    return 'unknown'


def category_label(category):
    return {'external': _('Внешнее устройство'), 'builtin': _('Встроенное устройство'),
            'audio': _('Аудиоустройство'), 'unknown': _('Тип не определён')}.get(category, _('Тип не определён'))


def connection_label(device):
    if is_builtin(device):
        return _('Встроенное устройство')
    if (device.connection == 'wireless' and 'mchose' in device.backends
            and (device.vid,device.pid) == ('3837','1001')):
        return _('Беспроводное через USB-приёмник')
    if device.kind == 'audio':
        subtype = audio_subtype(device)
        return {
            'display_hdmi': 'HDMI / DisplayPort', 'display_dp': 'HDMI / DisplayPort', 'display_audio': _('HDMI / DisplayPort'), 'usb_audio': _('USB-аудио'),
            'bluetooth_audio': _('Bluetooth-аудио'), 'headset': _('Аудио'),
            'headphones': _('Аудио'), 'speakers': _('Аудиосистема'),
            'microphone': _('Аудио'), 'audio_unknown': _('Аудиоустройство'),
        }.get(subtype, _('Аудиоустройство'))
    return {'usb': _('USB'), 'bluetooth': _('Bluetooth'), '2.4g': _('Беспроводное 2,4 ГГц'),
            'wireless': _('Беспроводное подключение'), 'internal': _('Встроенное устройство'),
            'audio': _('Аудиосистема')}.get(device.connection, _('Подключение не определено'))


def connection_status(device):
    if device.connected is True:
        return _('Подключено')
    if device.connected is False:
        return _('Отключено')
    return _('Подключение не подтверждено')


def dashboard_devices(devices, simulation=False, show_builtin=True):
    kinds = {'mouse', 'touchpad', 'keyboard', 'audio', 'input'}
    return [d for d in devices if d.kind in kinds and d.kind != 'interface'
            and d.connected is True and d.simulated is simulation
            and (show_builtin or device_category(d) != 'builtin')]


def available_settings(device):
    informational = {'standard_input','battery_status','battery_present','charging','firmware_version','identity','raw','key_details'}
    return sum(1 for c in device.capabilities if c.name not in informational
               and c.supported is True and (c.readable or c.writable))


def image_key(device):
    return artwork_key(device)


def image_source(device, assets_dir, provider=None):
    provider = provider or DeviceArtworkProvider(assets_dir, allow_user_artwork=False)
    return provider.resolve(device).path.resolve().as_uri()


def presentation(device, assets_dir, artwork_provider=None):
    provider = artwork_provider or DeviceArtworkProvider(assets_dir, allow_user_artwork=False)
    artwork = provider.resolve(device)
    has_battery = any(c.name == 'battery_status' for c in device.capabilities)
    has_charging = any(c.name == 'charging' for c in device.capabilities)
    setting_count = available_settings(device)
    display_battery = battery_display(device)
    description = provider.describe(artwork)
    key = artwork_key(device)
    uncertain = (key in ('mouse_builtin','pointer_generic','bluetooth_audio','audio_unknown','unknown') or device.kind=='input')
    type_label = {
        'mouse':'Мышь','mouse_gaming':'Игровая мышь','mouse_wireless':'Беспроводная мышь',
        'mouse_compact':'Компактная мышь','touchpad':'Тачпад','keyboard':'Клавиатура',
        'keyboard_60':'Клавиатура 60%','keyboard_65':'Клавиатура 65%','keyboard_tkl':'Клавиатура TKL',
        'keyboard_full':'Полноразмерная клавиатура','keyboard_builtin':'Клавиатура ноутбука',
        'headset':'Гарнитура','headphones':'Наушники','speakers':'Динамики',
        'microphone':'Микрофон','display_hdmi': 'HDMI / DisplayPort', 'display_dp': 'HDMI / DisplayPort', 'display_audio':'HDMI / DisplayPort','usb_audio':'Аудиоинтерфейс',
        'builtin_audio':'Встроенные динамики',
    }.get(key,'Тип не определён')
    sources = {'ratbagctl':'libratbag','solaar':'Solaar','solaar-local':'Solaar',
        'linux-input':'Linux Input','mchose':'MCHOSE','mchose-ace68':'MCHOSE',
        'openrgb':'OpenRGB','openrazer':'OpenRazer','headsetcontrol':'HeadsetControl',
        'pactl':'PipeWire / PulseAudio','simulation':_('Симуляция')}
    providers = list(dict.fromkeys(sources.get(name,name) for name in device.backends if name != 'kernel-battery'))
    plural = '%1 настройка' if setting_count%10==1 and setting_count%100!=11 else ('%1 настройки' if 2<=setting_count%10<=4 and not 12<=setting_count%100<=14 else '%1 настроек')
    transport = str(device.connection or '').casefold()
    if transport in ('usb', 'bluetooth', '2.4g', 'wireless'):
        connection_tag = {'2.4g': '2.4G', 'wireless': _('Беспроводное')}.get(transport, transport.upper())
    elif is_builtin(device):
        physical = str(device.physical or '').casefold()
        connection_tag = 'I²C' if 'i2c' in physical else 'PS/2' if 'serio' in physical else '—'
    else:
        connection_tag = '—'
    return {
        'deviceId': device.id,
        'name': model_name(device, provider.user_name(device)),
        'category': device_category(device),
        'categoryLabel': category_label(device_category(device)),
        'kind': device.kind,
        'connection': connection_label(device),
        'connectionTag': connection_tag,
        'status': connection_status(device),
        'connected': device.connected is True,
        **display_battery,
        'showBattery': battery_block_visible(device),
        'batteryIcon': ('network-offline-symbolic' if device.connected is False else 'battery-good-charging-symbolic' if display_battery['charging'] else 'battery-good-symbolic' if display_battery['batteryState']=='current' else 'battery-missing-symbolic') if has_battery or has_charging else '',
        'typeLabel': _(type_label),
        'generalizedArtwork': artwork.source in ('generated','fallback') and key!='touchpad',
        'artworkNote': _('Пользовательское изображение') if artwork.source=='user' else (_('Обобщённая графика') if artwork.source=='generated' and key!='touchpad' else (_('Изображение недоступно') if artwork.source=='fallback' else '')),
        'sourceLabel': ' · '.join(providers),
        'showSource': False,
        'readOnly': not any(c.supported is True and c.writable for c in device.capabilities),
        'settingsLabel': _(plural).replace('%1',str(setting_count)) if setting_count else _('Нет настроек'),
        'artGeometry': description,
        'artworkHash': description['sha256'],
        'artworkFile': description['file'],
        'availableSettings': setting_count,
        'settingsText': (_('Нет доступных настроек') if setting_count == 0 else
                         f"{setting_count} {(_('параметр') if setting_count == 1 else _('параметров'))}"),
        'imageSource': artwork.path.resolve().as_uri() + ('?v='+description['sha256'] if description['sha256'] else ''),
        'artworkSource': artwork.source,
        'artworkSourceLabel': _({'user':'Пользовательское изображение','exact-model':'Точная модель','system':'Системное изображение','generated':'Обобщённая графика','fallback':'Изображение недоступно'}.get(artwork.source,'Обобщённая графика')),
        'artworkKey': artwork.key,
        'artworkSlug': local_identity(device),
        'audioSubtype': audio_subtype(device) if device.kind == 'audio' else '',
        'simulated': device.simulated,
    }


def group_presentations(rows):
    """Split active presentation rows for indexed dashboard sections."""
    rows = list(rows)
    external = [row for row in rows if row['category'] == 'external' or
                (row['category'] == 'unknown' and row['kind'] in ('mouse', 'touchpad', 'keyboard'))]
    builtin = [row for row in rows if row['category'] == 'builtin']
    audio = [row for row in rows if row['kind'] == 'audio']
    consumed = {row['deviceId'] for row in (*external, *builtin, *audio)}
    other = [row for row in rows if row['deviceId'] not in consumed]
    return {'external': external, 'builtin': builtin, 'audio': audio, 'other': other}


def dashboard_inventory(rows, search='', show_builtin=True, category='all'):
    """One presentation universe for filters, sections, tabs and header counts.

    Tabs count available choices before the selected category. Header/section
    counts describe visible records; the built-in toggle counts available records
    before hiding them. Identity and backend discovery are not altered.
    """
    query=' '.join(str(search).casefold().split())
    searched=[r for r in rows if not query or query in ' '.join(r['name'].casefold().split())]
    def matches(row):
        return category=='all' or (row['kind'] in ('mouse','touchpad') if category=='mouse' else row['kind']==category)
    builtin_count=sum(r['category']=='builtin' and matches(r) for r in searched)
    eligible=[r for r in searched if show_builtin or r['category']!='builtin']
    visible=[r for r in eligible if matches(r)]
    groups=group_presentations(visible)
    return {'rows':visible,'groups':groups,'sections':{k:len(v) for k,v in groups.items()},
            'tabs':{'all':len(eligible),**{k:sum((r['kind'] in ('mouse','touchpad') if k=='mouse' else r['kind']==k) for r in eligible) for k in ('mouse','keyboard','audio')}},
            'builtin_available':builtin_count}


def battery_block_visible(device):
    caps=getattr(device,'capabilities',())
    if any(c.name=='battery_status' and c.supported is True and c.source in ('device','kernel')
           and type(c.value) in (int,float) and 0<=c.value<=100 for c in caps):return True
    if any(c.name=='battery_present' and c.value is False and c.supported is True
           and c.source in ('device','kernel','model_spec','simulation') for c in caps):return False
    if any(c.name in ('battery_status','charging') and c.supported is True for c in caps):return True
    if any(c.name=='battery_status' and c.supported is False for c in caps):return False
    return str(device.connection).lower() in ('wireless','2.4g','bluetooth')


def battery_segments(percent,segments=12):
    import math
    return math.floor(percent*segments/100) if type(percent) in (int,float) and math.isfinite(percent) and 0<=percent<=100 else 0
