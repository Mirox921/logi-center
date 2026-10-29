"""Model layouts and editable keyboard event drafts, independent of GTK."""
from dataclasses import dataclass,field
from logi_center.core.services.backups import action as validate_action
import re

# Native evdev codes: XKB scan codes in both Qt Wayland and X11 are code+8.
# This physical mapping remains stable when the active layout is Cyrillic.
SCAN_KEYS={**dict(zip(range(2,12),list('1234567890'))),**dict(zip(range(16,26),list('QWERTYUIOP'))),
           **dict(zip(range(30,39),list('ASDFGHJKL'))),**dict(zip(range(44,51),list('ZXCVBNM'))),
           **{59+i:'F'+str(i+1) for i in range(10)},87:'F11',88:'F12',
           **{183+i:'F'+str(i+13) for i in range(12)},
           1:'ESC',12:'MINUS',13:'EQUAL',14:'BACKSPACE',15:'TAB',26:'LEFTBRACE',27:'RIGHTBRACE',28:'ENTER',
           29:'LEFTCTRL',39:'SEMICOLON',40:'APOSTROPHE',41:'GRAVE',42:'LEFTSHIFT',43:'BACKSLASH',51:'COMMA',
           52:'DOT',53:'SLASH',54:'RIGHTSHIFT',55:'KPASTERISK',56:'LEFTALT',57:'SPACE',58:'CAPSLOCK',
           69:'NUMLOCK',70:'SCROLLLOCK',96:'KPENTER',97:'RIGHTCTRL',98:'KPSLASH',99:'SYSRQ',100:'RIGHTALT',
           102:'HOME',103:'UP',104:'PAGEUP',105:'LEFT',106:'RIGHT',107:'END',108:'DOWN',109:'PAGEDOWN',
           110:'INSERT',111:'DELETE',113:'MUTE',114:'VOLUMEDOWN',115:'VOLUMEUP',119:'PAUSE',125:'LEFTMETA',126:'RIGHTMETA'}
SCAN_KEYS.update(dict(zip(range(71,84),['KP7','KP8','KP9','KPMINUS','KP4','KP5','KP6','KPPLUS','KP1','KP2','KP3','KP0','KPDOT'])))


def scan_key(code,platform):
    if platform not in ('wayland','xcb') or type(code) is not int:return None
    name=SCAN_KEYS.get(code-8)
    return 'KEY_'+name if name else None


def validate_macro(tokens,allow_empty=False):
    if not isinstance(tokens,list) or len(tokens)>512 or not tokens and not allow_empty:raise ValueError('Invalid macro length')
    down=set()
    for token in tokens:
        if not isinstance(token,str) or not re.fullmatch(r'[+-]?(?:KEY_[A-Z0-9_]+|BTN_(?:LEFT|RIGHT|MIDDLE|SIDE|EXTRA))|t\d{1,5}',token):raise ValueError('Unsupported macro event')
        if token.startswith('t'):
            if not 1<=int(token[1:])<=99999:raise ValueError('Invalid macro pause')
        elif token.startswith('+'):
            if token[1:] in down:raise ValueError('Duplicate macro press')
            down.add(token[1:])
        elif token.startswith('-'):
            if token[1:] not in down:raise ValueError('Release without press')
            down.remove(token[1:])
    if down:raise ValueError('Unreleased macro key')

G502={0:(.445,.24),1:(.61,.24),2:(.532,.26),3:(.356,.51),4:(.357,.425),5:(.332,.60),6:(.39,.275),7:(.40,.195),8:(.532,.425),9:(.565,.265),10:(.495,.265)}
G305={0:(.45,.24),1:(.61,.24),2:(.532,.26),3:(.375,.55),4:(.375,.46),5:(.53,.425)}
def layout(name,count):
    known=G502 if 'G502' in name else G305 if 'G305' in name else {}
    rows=max(1,(count+3)//4)
    return {i:known.get(i, (.17+(i%4)*.22,.18+(i//4)*.64/max(1,rows-1))) for i in range(count)}

def action_allowed(action,types):
    return {'disabled':0,'button':1,'special':2,'key':3,'macro':4}.get(action[0]) in types

def assignment_label(button,actions):
    """Compare typed assignments, retaining the button/key/special discriminator."""
    from logi_center.core.services.operations import read_action,same
    actual=read_action(('macro ' if button.get('macro') else '')+button['action'])
    return next((label for label,value in actions.items() if same(value,actual)),None)

def linux_key(name):
    if re.fullmatch(r'KEY_[A-Z0-9_]+',name or ''):return name
    special={'Control_L':'LEFTCTRL','Control_R':'RIGHTCTRL','Shift_L':'LEFTSHIFT','Shift_R':'RIGHTSHIFT','Alt_L':'LEFTALT','Alt_R':'RIGHTALT','Super_L':'LEFTMETA','Super_R':'RIGHTMETA','Return':'ENTER','Escape':'ESC','space':'SPACE','BackSpace':'BACKSPACE','Tab':'TAB','Delete':'DELETE','Insert':'INSERT','Home':'HOME','End':'END','Page_Up':'PAGEUP','Page_Down':'PAGEDOWN','Left':'LEFT','Right':'RIGHT','Up':'UP','Down':'DOWN','minus':'MINUS','equal':'EQUAL','comma':'COMMA','period':'DOT','slash':'SLASH','semicolon':'SEMICOLON','apostrophe':'APOSTROPHE','bracketleft':'LEFTBRACE','bracketright':'RIGHTBRACE','backslash':'BACKSLASH','grave':'GRAVE'}
    if name in special:return 'KEY_'+special[name]
    if len(name)==1 and name.isascii() and name.isalnum():return 'KEY_'+name.upper()
    if name.startswith('F') and name[1:].isdigit() and 1<=int(name[1:])<=24:return 'KEY_'+name
    return None

def friendly(token):
    if token.startswith('t'):return 'Wait '+token[1:]+' ms'
    prefix={'+' : 'Press ', '-':'Release '}.get(token[0],'Tap ')
    key=token.lstrip('+-').removeprefix('KEY_')
    for source,target in [('LEFTCTRL','Ctrl'),('RIGHTCTRL','Right Ctrl'),('LEFTSHIFT','Shift'),('RIGHTSHIFT','Right Shift'),('LEFTALT','Alt'),('RIGHTALT','Right Alt'),('LEFTMETA','Super'),('RIGHTMETA','Right Super')]:
        if key==source:key=target;break
    return prefix+key

def conflicts(tokens):
    text=' '.join(tokens)
    return any(all(key in text for key in combination) for combination in [('KEY_LEFTALT','KEY_F4'),('KEY_LEFTCTRL','KEY_LEFTALT'),('KEY_LEFTMETA',),('KEY_RIGHTMETA',)])

@dataclass
class MacroDraft:
    tokens:list=field(default_factory=list)
    held:set=field(default_factory=set)
    def press(self,key):
        if key and key not in self.held:self.held.add(key);self.tokens.append('+'+key)
    def release(self,key):
        if key in self.held:self.held.remove(key);self.tokens.append('-'+key)
    def validate(self):validate_macro(self.tokens)


G502_ART={
    'top':{'file':'g502-top-wired-qt.svg','wireless_file':'g502-top-wireless-qt.svg',
           'width':1103,'height':2048,
           'anchors':{0:(140/366,155/680),1:(285/366,150/680),2:(209/366,190/680),
                      6:(67/366,240/680),7:(78/366,173/680),8:(216/366,337/680),
                      9:(236/366,190/680),10:(184/366,190/680)}},
    'side':{'file':'g502_hero_side_wired_fixed.svg','wireless_file':'g502_hero_side_wireless.svg',
            'width':999,'height':359,
            'anchors':{4:(346/680,109/244),3:(448/680,94/244),5:(300/680,171/244)}}}


def g502_wireless(device):
    """Transport evidence selects artwork; a USB receiver is not a cable."""
    return str(getattr(device,'connection','')).lower() in ('wireless','bluetooth','2.4g')



def editor_callouts(count):
    """Canonical 480×440 diagram coordinates; hit targets stay outside the shell."""
    if count>12:
        return {i:((50+(i%8)*54)/480,(50+(i//8)*48)/440) for i in range(count)}
    result={}
    for side in (0,1):
        indices=list(range(side,count,2))
        for row,index in enumerate(indices):
            result[index]=((426 if side else 54)/480,(74+row*min(56,290/max(1,len(indices)-1)))/440)
    return result


def button_caption(name,index):
    # Physical controls, independent of the user's current assignment.
    common=['Левая кнопка','Правая кнопка','Нажатие колеса','Назад','Вперёд']
    extra=['DPI Shift','DPI −','DPI +','Смена профиля','Колесо вправо','Колесо влево'] if 'G502' in name else ['DPI'] if 'G305' in name else []
    captions=common+extra
    return captions[index] if index<len(captions) else 'Кнопка'
