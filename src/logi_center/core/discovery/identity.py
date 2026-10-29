"""Private physical identity helpers; never merge devices by model alone."""
from pathlib import Path
import hashlib,re

def identity(path):return hashlib.sha256(str(path).encode()).hexdigest()[:24]


def usb_identity(path):
    """Return exact USB interface parent, shared by input/HID/ALSA siblings."""
    path=Path(path).resolve()
    for parent in [path,*path.parents]:
        try:
            vid=(parent/'idVendor').read_text().strip();pid=(parent/'idProduct').read_text().strip()
            return str(parent),vid,pid
        except OSError:pass
    return '', '', ''


def serial_usb_identity(serial,root='/sys/bus/usb/devices'):
    """Private exact serial + unique physical USB parent, never public report data."""
    if not serial or len(serial)<4 or len(set(serial))==1:return '', '', ''
    matches=[]
    for node in Path(root).glob('*'):
        try:
            if (node/'serial').read_text().strip()==serial:
                item=usb_identity(node)
                if item[0] and item not in matches:matches.append(item)
        except OSError:continue
    return matches[0] if len(matches)==1 else ('','','')


def usb_id(value):
    if type(value) is int:return f'{value:04x}' if 0<=value<=65535 else ''
    value=str(value or '').lower().removeprefix('0x')
    return value.zfill(4) if re.fullmatch('[0-9a-f]{1,4}',value) else ''
