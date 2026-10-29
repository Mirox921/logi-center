"""Ace68-II native three-byte key actions, independent of mouse protocols.

Source: official CZ channel getKeyMatrix/setUserKeyMatrix and its HID catalog.
Unknown advanced actions remain intact. No reset/boot/calibration actions.
"""
from ace68_protocol import KEY_INDICES


def read_colors(wire,profile):
    raw=list(wire.read(10,profile*512,384))
    if len(raw)!=384:raise ValueError('Incomplete native color bank')
    return {'raw_colors':raw,'key_lighting':{str(k):raw[k*3:k*3+3] for k in KEY_INDICES}}


def prepare_colors(profile,observed,changes):
    if not isinstance(changes,dict) or not changes or len(changes)>68:raise ValueError('Expected selected-key RGB colors')
    frames=[]
    for key,color in changes.items():
        if key not in observed['key_lighting']:raise ValueError('Unknown physical color index')
        if not isinstance(color,list) or len(color)!=3 or any(type(v) is not int or not 0<=v<=255 for v in color):raise ValueError('Expected RGB channels')
        frames.append((11,profile*512+int(key)*3,bytes(color)))
    return frames

LAYERS=('Windows','Windows Fn','Mac','Mac Fn')


def keyboard_usages():
    return {**{chr(65+i):4+i for i in range(26)},**{str(i):29+i for i in range(1,10)},'0':39,
            **{'F'+str(i):57+i for i in range(1,13)},'Enter':40,'Esc':41,'Backspace':42,'Tab':43,
            'Space':44,'-':45,'=':46,'[':47,']':48,'\\':49,';':51,"'":52,'`':53,',':54,'.':55,'/':56,
            'Print':70,'Scroll':71,'Pause':72,'Insert':73,'Home':74,'Page Up':75,'Delete':76,
            'End':77,'Page Down':78,'→':79,'←':80,'↓':81,'↑':82}


def actions():
    rows=[{'group':'basic','label':key,'value':[16,0,usage]} for key,usage in keyboard_usages().items()]
    rows += [{'group':'basic','label':name,'value':[16,1<<i,0]} for i,name in enumerate(('Ctrl','Shift','Alt','Super','R Ctrl','R Shift','R Alt','R Super'))]
    rows += [{'group':'mouse','label':name,'value':value} for name,value in
             [('Левая кнопка мыши',[32,1,0]),('Правая кнопка мыши',[32,2,0]),
              ('Средняя кнопка мыши',[32,4,0]),('Вперёд',[32,16,0]),('Назад',[32,8,0]),
              ('Колесо вверх',[33,0,1]),('Колесо вниз',[33,0,255])]]
    rows += [{'group':'media','label':name,'value':[48,code,0]} for name,code in
             [('Громче',233),('Тише',234),('Без звука',226),('Воспроизведение / пауза',205),('Остановить воспроизведение',183),('Предыдущий трек',182),('Следующий трек',181)]]
    rows += [{'group':'lighting','label':name,'value':[240,code,0]} for name,code in
             [('Следующий эффект',47),('Предыдущий эффект',46),('Ярче',50),('Темнее',51),('Выключить подсветку',53),
              ('Ускорить эффект',54),('Замедлить эффект',55),('Следующий цвет',61)]]
    rows += [{'group':'shortcuts','label':name,'value':[16,1,code]} for name,code in
             [('Копировать',6),('Вставить',25),('Вырезать',27),('Отменить',29),('Выделить всё',4),('Сохранить',22)]]
    rows += [{'group':'basic','label':'Fn (Windows)','value':[240,255,1]},
             {'group':'basic','label':'Fn (Mac)','value':[240,255,3]}]
    return rows


def validate_action(value):
    if not isinstance(value,list) or len(value)!=3 or any(type(v) is not int or not 0<=v<=255 for v in value):
        raise ValueError('Expected a native Ace68 action')
    kind,first,second=value
    if kind==16 and (second in keyboard_usages().values() or second==0 and first):return value
    if value in [a['value'] for a in actions()]:return value
    raise ValueError('Unverified Ace68 action; original binding is preserved')


def label(value):
    known=next((a['label'] for a in actions() if a['value']==value),None)
    if known:return known
    if value[0]==16:
        key=next((k for k,v in keyboard_usages().items() if v==value[2]),None)
        if key:
            modifiers=[n for i,n in enumerate(('Ctrl','Shift','Alt','Super','R Ctrl','R Shift','R Alt','R Super')) if value[1]&(1<<i)]
            return '+'.join([*modifiers,key])
    return {112:'Макрос на устройстве',144:'DKS',145:'TGL',146:'MT',147:'RS',148:'SOCD'}.get(value[0],'Назначение не распознано')


def read(wire,profile):
    current=[];defaults=[]
    for layer in range(4):
        offset=(profile*4+layer)*512
        user=wire.read(8,offset,384);default=wire.read(7,offset,384)
        if len(user)!=384 or len(default)!=384:raise ValueError('Incomplete Ace68 layer')
        current.append(list(user));defaults.append(list(default))
    effective={str(layer)+':'+str(index):list((defaults[layer] if current[layer][index*3]==255 else current[layer])[index*3:index*3+3])
               for layer in range(4) for index in KEY_INDICES}
    return {'key_remap':effective,'raw_bindings':current,'default_bindings':defaults}


def prepare(profile,original,changes):
    if not isinstance(changes,dict) or not changes or len(changes)>272:raise ValueError('Invalid Ace68 binding batch')
    for key,value in changes.items():
        if key not in original['key_remap']:raise ValueError('Key is outside the Ace68 layout')
        validate_action(value)
    def fn(value):return value in ([240,255,1],[240,255,3])
    for layer in (0,2):
        before={k:v for k,v in original['key_remap'].items() if k.startswith(str(layer)+':')};after={**before,**{k:v for k,v in changes.items() if k in before}}
        if any(fn(v) for v in before.values()) and not any(fn(v) for v in after.values()):raise ValueError('Preserve at least one Fn key')
    ordered=sorted(changes,key=lambda key:not fn(changes[key]))
    return [(9,(profile*4+int(key.split(':')[0]))*512+int(key.split(':')[1])*3,bytes(changes[key])) for key in ordered]
