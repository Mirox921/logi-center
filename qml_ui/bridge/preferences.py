"""Bounded, private GUI preferences, separate from device/profile settings."""
import json
import os
from pathlib import Path

UI_SCALES=(75,90,100,110,125,150,175,200)
DEFAULTS = {'language':'ru', 'show_builtin':True, 'reduced_motion':False,'ui_scale':100}


def qt_scale(environment,percent):
    """Application-local scale composed with an explicit Qt environment factor."""
    import math
    try:factor=float(environment.get('QT_SCALE_FACTOR','1'))
    except (TypeError,ValueError):factor=1.
    if not math.isfinite(factor) or factor<=0:factor=1.
    return str(factor*percent/100)


def preferences_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))/'logi-center/qml-ui.json'


def _read(path):
    if not path.exists(): return {}
    if path.stat().st_size > 16384: raise ValueError('GUI preferences too large')
    value=json.loads(path.read_text())
    if not isinstance(value,dict): raise ValueError('Invalid GUI preferences')
    return value


def load_preferences(path=None):
    try: value=_read(Path(path) if path else preferences_path())
    except (OSError,ValueError): value={}
    result=dict(DEFAULTS)
    if value.get('language') in ('ru','en'):result['language']=value['language']
    for key in ('show_builtin','reduced_motion'):
        if type(value.get(key)) is bool:result[key]=value[key]
    if type(value.get('ui_scale')) is int and value['ui_scale'] in UI_SCALES:result['ui_scale']=value['ui_scale']
    return result


def save_preferences(values,path=None):
    from drafts import atomic_json
    target=Path(path) if path else preferences_path()
    # Do not discard future keys or overwrite an unreadable/corrupt document.
    current=_read(target)
    for key in DEFAULTS:
        if key in values:current[key]=values[key]
    atomic_json(target,current)


def system_reduced_motion(runner=None):
    """Read the GTK desktop preference once from a worker; never change it."""
    from execution import command,Fault
    if os.environ.get('LOGI_CENTER_REDUCED_MOTION') == '1':return True
    runner=runner or command
    try:
        return runner(['gsettings','get','org.gnome.desktop.interface','enable-animations'],timeout=1).strip()=='false'
    except (Fault,OSError,ValueError):return False
