"""G515 ANSI/TKL presentation, using existing project geometry.

LED zone numbers are the factual HID++ 0x8081/OpenRGB keyboard numbering
used by Solaar. They are NOT HID keycodes or remapping IDs. Only zones
present in saved per-key settings are made writable; the CLI validates them
again against the connected device. No Qt/GTK imports or device discovery.
"""
from keyboard_layouts import LAYOUTS

ZONES={c:i+1 for i,c in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}
ZONES.update({c:i+27 for i,c in enumerate('1234567890')})
ZONES.update({f'F{i}':54+i for i in range(1,13)})
ZONES.update(dict(zip(['Enter','Esc','Backspace','Tab','Space','-','=','[',']','\\'],range(37,47))))
ZONES.update(dict(zip([';',"'",'`',',','.','/','Caps'],range(48,55))))
ZONES.update(dict(zip(['Print','Scroll','Pause','Insert','Home','PgUp','Del','End','PgDn','Right','Left','Down','Up'],range(67,80))))
ZONES.update({'Menu':98,'LCtrl':104,'LShift':105,'LAlt':106,'Super':107,
              'RCtrl':108,'RShift':109,'RAlt':110,'Fn':111})


def keys():
    return [dict(id=str(ZONES[k.label]),label=k.label,x=k.x,y=k.y,w=k.width,h=k.height)
            for k in LAYOUTS['tkl'].keys]


def group_ids(name):
    labels={'wasd':list('WASD'),'numbers':list('1234567890'),
            'function':[f'F{i}' for i in range(1,13)],
            'modifiers':['LCtrl','RCtrl','LShift','RShift','LAlt','RAlt','Super','Fn'],
            'arrows':['Left','Right','Up','Down'],'all':list(ZONES)}.get(name,[])
    return {str(ZONES[label]) for label in labels}


def saved_colors(saved):
    """Ignore sentinels/unknown zones rather than turning them into black."""
    colors={}
    mapping=saved.get('per-key-lighting')
    if not isinstance(mapping,dict):return colors
    valid={k['id'] for k in keys()}
    for key,raw in mapping.items():
        if str(key) not in valid or isinstance(raw,bool):continue
        try:value=int(str(raw),0) if isinstance(raw,str) else raw
        except (ValueError,TypeError):continue
        if type(value) is int and 0<=value<=0xffffff:
            colors[str(key)]=[(value>>s)&255 for s in (16,8,0)]
    return colors
