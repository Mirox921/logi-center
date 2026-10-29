"""Pure K7 Ultra settings codec from the official M HUB K7 panels.

No transport or discovery here. Frames are executed by mchose_adapter under
its identity, snapshot, serialization and readback guards. See docs/k7-controls.md.
"""
import struct


FIELDS=('dpi_config','button_bindings','sensor_config')
# Original anchors widened about x=.5 by 1.45, matching the SVG group.
BUTTONS=((0,'Левый щелчок',.355,.24),(2,'Правый щелчок',.6885,.24),
         (1,'Нажатие колёсика',.50,.27),(3,'Вперёд',.1665,.39),(4,'Назад',.1665,.51))


def integer(value,low,high):
    if type(value) is not int or not low<=value<=high:raise ValueError('K7 value outside documented range')
    return value


def values(raw,mode=1):
    """Read all stages, five assignable buttons, and native sensor parameters."""
    if len(raw)!=63:raise ValueError('Short K7 configuration')
    x=list(struct.unpack_from('<6H',bytes(raw),4))
    y=list(struct.unpack_from('<6H',bytes(raw),51)) if raw[50] else x[:]
    dpi={'count':raw[16],'active':raw[1 if mode==0 else 2]&15,'axes_available':bool(raw[50])}
    dpi.update({axis+str(i):v for axis,rows in (('x',x),('y',y)) for i,v in enumerate(rows)})
    buttons={str(i):[raw[20+4*i]&15,int.from_bytes(bytes(raw[21+4*i:24+4*i]),'big')] for i in range(5)}
    sensor={'lod':raw[17]&3,'ripple':bool(raw[17]&4),'angle_snap':bool(raw[17]&8),
            'motion_sync':bool(raw[17]&16),'performance_mode':{0:0,128:1,192:2}.get(raw[17]&192),
            'rotation':raw[49] if raw[49]<128 else raw[49]-256}
    return {'dpi_config':dpi,'button_bindings':buttons,'sensor_config':sensor}


def prepare(raw,field,changes,mode):
    """Return (native frames, permitted per-byte bitmasks).

    0x42 uses zero as *unchanged* for boolean fields, one for on and two
    for off. It is not a replacement sensor byte. The current LOD is always
    supplied, as in the exact K7 official panel, preserving unknown bits.
    """
    if field not in FIELDS or not isinstance(changes,dict) or not changes:
        raise ValueError('Invalid K7 settings batch')
    state=values(raw,mode)[field]
    if set(changes)-set(state) or 'axes_available' in changes:raise ValueError('Unknown or read-only K7 setting')
    target={**state,**changes};allowed={3:255};frames=[]
    if field=='dpi_config':
        count=integer(target['count'],1,6);active=integer(target['active'],0,count-1)
        axes=[]
        for axis in ('x','y'):
            rows=[integer(target[axis+str(i)],50,42000) for i in range(6)]
            if any(v%50 for v in rows):raise ValueError('K7 DPI step is 50')
            if any(axis+str(i) in changes and v<200 for i,v in enumerate(rows)):
                raise ValueError('The official K7 DPI range is 200..42000')
            axes+=rows
        if not state['axes_available'] and axes[:6]!=axes[6:]:
            raise ValueError('This K7 firmware does not expose separate DPI axes')
        # A single packet changes stage count, active index and both axes.
        frames=[(0x12,0x40,bytes([active,active,0])+struct.pack('<6H',*axes[:6])+bytes([count,255])+struct.pack('<6H',*axes[6:]))]
        allowed.update({1:15,2:15,16:255})
        for i in range(6):
            for axis,offset in (('x',4),('y',51)):
                # Old firmware may initialize previously unavailable Y values.
                if axis+str(i) in changes or axis=='y' and not raw[50]:
                    allowed[offset+2*i]=allowed[offset+2*i+1]=255
    elif field=='button_bindings':
        for key,action in changes.items():
            if not isinstance(action,list) or len(action)!=2:raise ValueError('Invalid K7 button action')
            kind,value=action
            validate_action(action)
        if not any(action==[1,0x010000] or key=='0' and action==[0,0] for key,action in target.items()):
            raise ValueError('Keep at least one left-click button')
        # Establish a replacement left click before changing the old one.
        for key in sorted(changes,key=lambda k:changes[k]!=[1,0x010000]):
            index=integer(int(key),0,4);kind,value=changes[key]
            frames.append((0x12,0x52,bytes([index,0,kind])+value.to_bytes(3,'big')))
            allowed.update({20+4*index:15,21+4*index:255,22+4*index:255,23+4*index:255})
    else:
        args=bytearray(9);args[0]=integer(target['lod'],0,2)
        if 'lod' in changes:allowed[17]=3
        for key,position,mask in (('ripple',1,4),('angle_snap',2,8),('motion_sync',3,16)):
            if key not in changes:continue
            if type(changes[key]) is not bool:raise ValueError('Expected a K7 sensor switch')
            args[position]=1 if changes[key] else 2
            allowed[17]=allowed.get(17,0)|mask
        if 'performance_mode' in changes:
            args[6]=integer(changes['performance_mode'],0,2)+1;allowed[17]=allowed.get(17,0)|192
        if 'rotation' in changes:
            args[7]=1;args[8]=integer(changes['rotation'],-30,30)&255;allowed[49]=255
        frames=[(0x11,0x42,bytes(args))]
    return frames,allowed


def unchanged(before,after,allowed):
    return len(before)==len(after)==63 and all(not ((a^b)&(~allowed.get(i,0)&255)) for i,(a,b) in enumerate(zip(before,after)))


def keyboard_usages():
    return {**{chr(65+i):4+i for i in range(26)},**{str(i):0x1d+i for i in range(1,10)},'0':0x27,
            **{'F'+str(i):0x39+i for i in range(1,13)},'Enter':0x28,'Esc':0x29,'Backspace':0x2a,
            'Tab':0x2b,'Space':0x2c,'Insert':0x49,'Home':0x4a,'Page Up':0x4b,'Delete':0x4c,
            'End':0x4d,'Page Down':0x4e,'→':0x4f,'←':0x50,'↓':0x51,'↑':0x52}


def validate_action(action):
    if not isinstance(action,list) or len(action)!=2:raise ValueError('Invalid K7 button action')
    kind,value=action;integer(kind,0,15);integer(value,0,0xffffff)
    if kind==2 and value&255==0 and ((value>>8)&255 in keyboard_usages().values() or (value>>8)&255==0 and value>>16):return action
    if action not in [a['value'] for a in actions()]:raise ValueError('Unsupported K7 button action')
    return action


def action_label(action):
    known=next((a['label'] for a in actions() if a['value']==action),None)
    if known:return known
    if isinstance(action,list) and len(action)==2:
        if action[0]==4:return 'Макрос на устройстве'
        if action[0]==2:
            value=action[1];key=next((key for key,usage in keyboard_usages().items() if usage==((value>>8)&255)),None)
            if (key or value>>16 and not value&65535) and not value&255:
                modifiers=[name for bit,name in enumerate(('Ctrl','Shift','Alt','Super','R Ctrl','R Shift','R Alt','R Super')) if value&(1<<(16+bit))]
                return '+'.join([*modifiers,*([key] if key else [])])
    return 'Назначение не распознано'


def actions():
    """Allowlisted M HUB action encodings, never arbitrary reports/macros."""
    rows=[]
    def add(group,label,kind,value):rows.append({'group':group,'label':label,'value':[kind,value]})
    add('system','Исходное назначение',0,0)
    for label,value in (('Левый щелчок',0x010000),('Правый щелчок',0x020000),('Нажатие колёсика',0x040000),
                        ('Вперёд',0x100000),('Назад',0x080000),('Прокрутить вверх',0x000200),('Прокрутить вниз',0x00fe00)):
        add('system',label,1,value)
    for label,value in (('Переключать чувствительность',1),('Увеличить DPI',2),('Уменьшить DPI',3)):add('system',label,5,value<<16)
    for i in range(3):add('system','Профиль '+str(i+1),10,(i+1)<<16)
    add('system','Следующий профиль',10,0x040000);add('system','Отключить кнопку',9,0xffffff)
    for label,usage in keyboard_usages().items():add('keyboard',label,2,usage<<8)
    for label,usage in (('Копировать',6),('Вставить',25),('Вырезать',27),('Отменить',29),('Выделить всё',4),('Сохранить',22)):
        add('hotkey',label,2,0x010000|(usage<<8))
    for label,value in (('Громче',0xe90000),('Тише',0xea0000),('Без звука',0xe20000),
                        ('Воспроизведение / пауза',0xcd0000),('Предыдущий трек',0xb60000),('Следующий трек',0xb50000)):
        add('media',label,3,value)
    return rows
