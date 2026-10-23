"""Model layouts and editable keyboard event drafts, independent of GTK."""
from dataclasses import dataclass,field
from backups import action as validate_action

G502={0:(.445,.24),1:(.61,.24),2:(.532,.26),3:(.356,.51),4:(.357,.425),5:(.332,.60),6:(.39,.275),7:(.40,.195),8:(.532,.425),9:(.565,.265),10:(.495,.265)}
G305={0:(.45,.24),1:(.61,.24),2:(.532,.26),3:(.375,.55),4:(.375,.46),5:(.53,.425)}
def layout(name,count):
    known=G502 if 'G502' in name else G305 if 'G305' in name else {}
    return {i:known.get(i, (.15+(i%4)*.22,.18+(i//4)*.2)) for i in range(count)}

def linux_key(name):
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
    def validate(self):validate_action(['macro',*self.tokens])
