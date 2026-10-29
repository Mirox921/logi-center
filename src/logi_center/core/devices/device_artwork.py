"""Safe, provenance-aware device artwork selection shared by UI frontends.

This module never queries hardware. Physical identity is only hashed locally for
user artwork preferences; raw selectors are never written into file names or
preference keys.
"""
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET


MAX_ARTWORK_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 48_000_000
_SVG_NS = '{http://www.w3.org/2000/svg}'
_SAFE_SVG_TAGS = {
    'svg', 'title', 'desc', 'defs', 'linearGradient', 'radialGradient', 'stop',
    'clipPath', 'mask', 'g', 'rect', 'path', 'circle', 'ellipse', 'line',
    'polyline', 'polygon',
}
_SAFE_URL = re.compile(r'url\(\s*#[A-Za-z_][\w.-]*\s*\)', re.I)
_URL_TOKEN = re.compile(r'url\s*\(', re.I)


@dataclass(frozen=True)
class Artwork:
    path: Path
    source: str
    key: str


def _text(value):
    return ' '.join(str(value or '').strip().split()).casefold()


def is_builtin(device):
    physical = str(getattr(device, 'physical', '') or '').split('|', 1)[0].casefold()
    pieces = [part for part in physical.split('/') if part]
    return (getattr(device, 'connection', '') == 'internal' or
            any(part.startswith(('i2c-', 'serio', 'serial')) for part in pieces))


def audio_subtype(device):
    """Use typed metadata, backend routes and capabilities, never display names."""
    explicit = _metadata(device, 'audio_subtype')
    allowed = {'headset', 'headphones', 'speakers', 'display_audio', 'microphone',
               'usb_audio', 'bluetooth_audio', 'builtin_audio', 'audio_unknown','display_hdmi','display_dp'}
    if explicit in allowed:
        return explicit
    connection = _text(getattr(device, 'connection', ''))
    identifier = _text(getattr(device, 'id', ''))
    route = _text(getattr(device, 'target', ''))
    if re.search(r'(?:^|[._:-])(?:hdmi|displayport)(?:[._:-]|$)', route):
        return 'display_hdmi' if re.search(r'(?:^|[._:-])hdmi(?:[._:-]|$)',route) else 'display_dp'
    if identifier.startswith('pulse:microphone:'):
        return 'microphone'
    if 'headsetcontrol' in getattr(device, 'backends', ()):
        return 'headset'
    if any(c.name == 'sidetone' and c.supported is True for c in getattr(device, 'capabilities', ())):
        return 'headset'
    if connection == 'bluetooth':
        return 'bluetooth_audio'
    if is_builtin(device):
        return 'builtin_audio'
    return 'audio_unknown'


def _metadata(device, field):
    value = getattr(device, field, None)
    if isinstance(value, str):
        return value.casefold()
    for cap in getattr(device, 'capabilities', ()):
        if cap.name == field and cap.supported is True and isinstance(cap.value, str):
            return cap.value.casefold()
    return ''


def confirmed_touchpad(device):
    if getattr(device,'kind','') == 'touchpad' or _metadata(device,'input_subtype') in ('touchpad','trackpad'):
        return True
    if getattr(device,'ID_INPUT_TOUCHPAD',None) in ('1',1,True):return True
    if any(c.name=='ID_INPUT_TOUCHPAD' and c.supported is True and c.value in ('1',1,True)
           for c in getattr(device,'capabilities',())):return True
    for field in ('udev_properties','properties','udev'):
        values=getattr(device,field,None)
        if isinstance(values,dict) and values.get('ID_INPUT_TOUCHPAD') in ('1',1,True):return True
    return False


def artwork_key(device):
    kind = getattr(device, 'kind', 'unknown')
    connection = _text(getattr(device, 'connection', ''))
    if kind == 'mouse':
        if confirmed_touchpad(device): return 'touchpad'
        if is_builtin(device):
            if confirmed_touchpad(device):
                return 'touchpad'
            return 'pointer_generic'
        if _metadata(device, 'mouse_variant') == 'compact':
            return 'mouse_compact'
        if any((c.name in ('dpi', 'dpi_x', 'polling_rate', 'macros') or
                c.name == 'buttons' and type(c.value) is int and c.value > 3) and c.supported is True
               for c in getattr(device, 'capabilities', [])):
            return 'mouse_gaming'
        if connection in ('bluetooth', 'wireless', '2.4g'):
            return 'mouse_wireless'
        return 'mouse'
    if kind == 'keyboard':
        if is_builtin(device):
            return 'keyboard_builtin'
        if (str(getattr(device, 'vid', '')).lower(), str(getattr(device, 'pid', '')).lower()) == ('41e4', '2116'):
            return 'keyboard_65'
        layout = _metadata(device, 'keyboard_layout')
        if layout in ('60', '65', 'tkl', 'full'):
            return 'keyboard_' + layout
        return 'keyboard'
    if kind == 'audio':
        return audio_subtype(device)
    if kind == 'touchpad':
        return 'touchpad'
    if kind in ('receiver', 'usb-receiver', 'dongle'):
        return 'receiver'
    return 'unknown'


def local_identity(device):
    physical = str(getattr(device, 'physical', '') or '').split('|', 1)[0].strip()
    selector = physical or str(getattr(device, 'id', '') or '').strip()
    if not selector:
        return ''
    kind = str(getattr(device, 'kind', 'unknown'))
    return hashlib.sha256((kind + '\0' + selector).encode('utf-8', 'replace')).hexdigest()


def validate_artwork_file(path):
    """Validate safe SVG or bounded PNG/WebP headers without decoding on GUI thread."""
    path = Path(path)
    try:
        size = path.stat().st_size
        if size <= 0 or size > MAX_ARTWORK_BYTES:
            return False, 'Artwork must be between 1 byte and 8 MiB.'
        suffix = path.suffix.casefold()
        raw = path.read_bytes()
    except OSError:
        return False, 'Artwork file cannot be read.'
    if suffix == '.png':
        if len(raw) < 24 or raw[:8] != b'\x89PNG\r\n\x1a\n' or raw[12:16] != b'IHDR':
            return False, 'Invalid PNG image.'
        width, height = int.from_bytes(raw[16:20], 'big'), int.from_bytes(raw[20:24], 'big')
        if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
            return False, 'Image dimensions are too large.'
        return True, ''
    if suffix == '.webp':
        if len(raw) < 30 or raw[:4] != b'RIFF' or raw[8:12] != b'WEBP':
            return False, 'Invalid WebP image.'
        if int.from_bytes(raw[4:8], 'little') + 8 > len(raw):
            return False, 'Truncated WebP image.'
        position = 12
        limit = int.from_bytes(raw[4:8], 'little') + 8
        while position + 8 <= limit:
            kind = raw[position:position + 4]
            count = int.from_bytes(raw[position + 4:position + 8], 'little')
            payload = position + 8
            if payload + count > limit:
                return False, 'Truncated WebP image.'
            width = height = 0
            if kind == b'VP8X' and count >= 10:
                width = int.from_bytes(raw[payload + 4:payload + 7], 'little') + 1
                height = int.from_bytes(raw[payload + 7:payload + 10], 'little') + 1
            elif kind == b'VP8L' and count >= 5 and raw[payload] == 0x2f:
                bits = int.from_bytes(raw[payload + 1:payload + 5], 'little')
                width, height = (bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1
            elif kind == b'VP8 ' and count >= 10 and raw[payload + 3:payload + 6] == b'\x9d\x01\x2a':
                width = int.from_bytes(raw[payload + 6:payload + 8], 'little') & 0x3fff
                height = int.from_bytes(raw[payload + 8:payload + 10], 'little') & 0x3fff
            if width and height:
                return (True, '') if width * height <= MAX_IMAGE_PIXELS else (False, 'Image dimensions are too large.')
            position = payload + count + (count & 1)
        return False, 'Invalid WebP dimensions.'
    if suffix != '.svg':
        return False, 'Choose a PNG, WebP or safe SVG image.'
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        return False, 'SVG document types and entities are not allowed.'
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return False, 'Invalid SVG image.'
    if root.tag not in (_SVG_NS + 'svg', 'svg'):
        return False, 'The file is not an SVG document.'
    nodes = list(root.iter())
    # Bound parser/rendering work for hand-crafted SVGs. The byte cap alone
    # does not protect against thousands of tiny nodes or huge path data.
    if len(nodes) > 5000:
        return False, 'SVG contains too many drawing elements.'
    for node in nodes:
        tag = node.tag.rsplit('}', 1)[-1]
        if tag not in _SAFE_SVG_TAGS:
            return False, 'SVG contains unsupported or active content.'
        if len(node.text or '') > 128_000 or any(len(str(value)) > 128_000 for value in node.attrib.values()):
            return False, 'SVG drawing data is too large.'
        for key, value in node.attrib.items():
            local = key.rsplit('}', 1)[-1].casefold()
            value = str(value).strip()
            if local.startswith('on') or local in ('style', 'src', 'base'):
                return False, 'SVG contains active content.'
            if local == 'href' and not value.startswith('#'):
                return False, 'External SVG references are not allowed.'
            if _URL_TOKEN.search(_SAFE_URL.sub('', value)):
                return False, 'External SVG resources are not allowed.'
            if re.search(r'javascript:|data:|file:', value, re.I):
                return False, 'SVG contains an unsafe reference.'
    return True, ''


class DeviceArtworkProvider:
    """Select local, exact-model, system, generated and generic artwork in order."""
    def __init__(self, assets_dir, *, data_dir=None, exact_models=None, system_models=None,
                 allow_user_artwork=True, preferences_file=None):
        self.assets_dir = Path(assets_dir)
        self.generated_dir = self.assets_dir / 'generated'
        if data_dir is None:
            base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
            data_dir = base / 'logi-center' / 'device-images'
            self._legacy_dir = base / 'logi-center' / 'device-artwork'
        else:
            self._legacy_dir = None
        self.data_dir = Path(data_dir)
        config_base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
        self.preferences_file = Path(preferences_file) if preferences_file else config_base / 'logi-center' / 'device-artwork.json'
        self.allow_user_artwork = allow_user_artwork
        self.exact_models = dict(exact_models or {})
        self.system_models = dict(system_models or {})
        self.product_models = self._product_models()
        self._validation_cache = {}
        self._decode_failures = {}

    def _product_models(self):
        """Project-authored model art; product IDs never imply a revision."""
        try:
            manifest=self.assets_dir.parent/'mice'/'models.json'
            if manifest.stat().st_size>32768:return {}
            data=json.loads(manifest.read_text(encoding='utf-8'))
            if data.get('version')!=1:return {}
            result={}
            for row in data.get('models',[]):
                vid,pid=row['vid'],row['pid'];filename=row['file']
                canvas=row['canvas'];bounds=row['bounds']
                if not (re.fullmatch('[0-9a-f]{4}',vid) and re.fullmatch('[0-9a-f]{4}',pid)
                        and Path(filename).name==filename and filename.endswith('.svg')
                        and len(canvas)==2 and all(type(v) is int and v>0 for v in canvas)
                        and len(bounds)==4 and all(type(v) is int for v in bounds)
                        and 0<=bounds[0]<bounds[2]<=canvas[0]
                        and 0<=bounds[1]<bounds[3]<=canvas[1]):continue
                path=self.assets_dir.parent/'mice'/filename
                editor=row.get('editor_diagram')
                if editor is not None and (Path(editor).name!=editor or not (self.assets_dir.parent/'mice'/editor).is_file()):continue
                variants={}
                for connection,variant in row.get('variants',{}).items():
                    if connection=='wireless' and Path(variant).name==variant and variant.endswith('.svg') and (self.assets_dir.parent/'mice'/variant).is_file():
                        variants[connection]=self.assets_dir.parent/'mice'/variant
                if path.is_file():result[(vid,pid)]={'path':path,'canvas':canvas,'bounds':bounds,
                    'family':row.get('family','unknown'),'editor_diagram':editor,'anchors':row.get('anchors',''),'variants':variants,
                    'model_ids':row.get('model_ids',[])}
            return result
        except (OSError,ValueError,TypeError,KeyError,AttributeError):return {}

    @staticmethod
    def _signature(path):
        try:
            stat=Path(path).stat()
            return (str(Path(path).resolve()),stat.st_size,stat.st_mtime_ns,stat.st_ino)
        except OSError:return None

    def reject_decoding(self,path):
        signature=self._signature(path)
        if signature:
            self._decode_failures[signature]=True
            if len(self._decode_failures)>128:self._decode_failures.pop(next(iter(self._decode_failures)))

    def _usable(self,path):
        return Path(path).is_file() and self._signature(path) not in self._decode_failures

    def _preference(self, key):
        if not self.allow_user_artwork or not key:
            return None
        filename = self._read_preferences()['devices'].get(key)
        candidates = []
        if isinstance(filename, str) and Path(filename).name == filename:
            candidates.append(self.data_dir / filename)
            if self._legacy_dir is not None:
                candidates.append(self._legacy_dir / filename)
        # Manual drop-in files use the same private stable slug as GUI choices.
        candidates.extend(self.data_dir / (key + suffix) for suffix in ('.png', '.webp', '.svg'))
        for candidate in candidates:
            if not self._usable(candidate):continue
            try:
                stat = candidate.stat()
            except OSError:
                continue
            cache_key = (str(candidate), stat.st_size, stat.st_mtime_ns, stat.st_ino)
            valid = self._validation_cache.get(cache_key)
            if valid is None:
                valid, _ = validate_artwork_file(candidate)
                self._validation_cache = {cache_key: valid, **dict(list(self._validation_cache.items())[-31:])}
            if valid:
                return candidate
        return None

    def resolve(self, device):
        key = artwork_key(device)
        identity = local_identity(device)
        preferred = self._preference(identity)
        if preferred:
            return Artwork(preferred, 'user', key)
        exact_key = (str(getattr(device, 'vid', '')).lower(),
                     str(getattr(device, 'pid', '')).lower(),
                     str(getattr(device, 'revision', '') or '').lower())
        confirmed_revision = exact_key[2] not in ('', 'unknown', 'unconfirmed')
        exact = self.exact_models.get(exact_key) if confirmed_revision else None
        if exact and self._usable(exact):
            return Artwork(Path(exact), 'exact-model', key)
        system = self.system_models.get(exact_key) if confirmed_revision else None
        if system and self._usable(system):
            return Artwork(Path(system), 'system', key)
        product=self.product_models.get(exact_key[:2]) if getattr(device,'kind','')=='mouse' else None
        if product and product.get('model_ids'):
            model=next((c.value for c in getattr(device,'capabilities',[]) if c.name=='model_id' and c.source=='device'),None)
            if model not in product['model_ids']:product=None
        if product:
            connection='wireless' if getattr(device,'connection','') in ('wireless','bluetooth','2.4g') else ''
            path=product.get('variants',{}).get(connection,product['path'])
            if self._usable(path):return Artwork(path, 'exact-model', key)
        for density in (2, 1):
            for stem in dict.fromkeys((key.replace('_', '-'), key)):
                generated = self.generated_dir / f'{stem}@{density}x.png'
                if self._usable(generated):
                    return Artwork(generated, 'generated', key)
        # Keep a read-only compatibility fallback for installations upgrading
        # from the previous SVG pack; newly rendered assets always take priority.
        generated = self.generated_dir / (key + '.svg')
        if self._usable(generated):return Artwork(generated, 'generated', key)
        choices=[self.generated_dir/'unknown@2x.png',self.generated_dir/'unknown@1x.png',
                 self.assets_dir/'fallback@2x.png',self.assets_dir/'fallback.png',
                 self.generated_dir/'unknown.svg',self.assets_dir/'unknown.svg']
        fallback=next((path for path in choices if self._usable(path)),choices[-1])
        return Artwork(fallback, 'fallback', 'unknown')

    def describe(self, artwork):
        """Cached provenance and precomputed bounds; no decoder/runtime renderer."""
        path=artwork.path.resolve()
        cache=getattr(self,'_file_descriptions',{})
        try:
            stat=path.stat();key=(str(path),stat.st_size,stat.st_mtime_ns,stat.st_ino)
            digest=cache.get(key)
            if digest is None:
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                cache[key]=digest
                if len(cache)>128:cache.pop(next(iter(cache)))
                self._file_descriptions=cache
        except OSError:digest=''
        data={'file':path.name,'path':str(path),'sha256':digest,'source':artwork.source,
              'bounds':[.1,.1,.9,.9],'shadow_bounds':[.1,.1,.9,.9],'family':artwork.key,'family_width':.8,'family_height':.8,'aspect':1.6,'valid':False}
        for product in self.product_models.values():
            if path in [product['path'].resolve(),*(p.resolve() for p in product.get('variants',{}).values())]:
                width,height=product['canvas'];x1,y1,x2,y2=product['bounds']
                bounds=[x1/width,y1/height,x2/width,y2/height]
                data.update({'bounds':bounds,'shadow_bounds':bounds,'family':product['family'],
                             'family_width':(x2-x1)/width,'family_height':(y2-y1)/height,
                             'aspect':width/height,'valid':True})
                return data
        if artwork.source not in ('generated','fallback') or path.suffix.casefold()!='.png':return data
        manifest=self.generated_dir/'geometry.json'
        try:
            stat=manifest.stat()
            signature=(stat.st_size,stat.st_mtime_ns)
            cached=getattr(self,'_geometry_description',None)
            if cached is None or cached[0]!=signature:
                if stat.st_size>131072:raise ValueError('Artwork geometry too large')
                doc=json.loads(manifest.read_text())
                if doc.get('version')!=1:raise ValueError('Unknown geometry version')
                self._geometry_description=(signature,doc.get('classes',{}))
            row=self._geometry_description[1].get(artwork.key,{})
            bounds=row.get('bounds',[])
            if len(bounds)!=4 or not all(type(v) in (int,float) and math.isfinite(v) and 0<=v<=1 for v in bounds):return data
            if not (bounds[0]<bounds[2] and bounds[1]<bounds[3]):return data
            if not all(type(row.get(k)) in (int,float) and 0<row[k]<=1 for k in ('family_width','family_height')):return data
            if not isinstance(row.get('family'),str) or len(row['family'])>64:return data
            if row['family_width']<bounds[2]-bounds[0] or row['family_height']<bounds[3]-bounds[1]:return data
            data.update({k:row[k] for k in ('bounds','family','family_width','family_height')})
            shadow=row.get('shadow_bounds',bounds)
            if len(shadow)==4 and all(type(v) in (int,float) and math.isfinite(v) and 0<=v<=1 for v in shadow) and shadow[0]<=bounds[0] and shadow[1]<=bounds[1] and shadow[2]>=bounds[2] and shadow[3]>=bounds[3]:data['shadow_bounds']=shadow
            data['valid']=True
        except (OSError,ValueError,TypeError,KeyError,AttributeError):pass
        return data

    def set_user_artwork(self, device, source, *, decoder=None):
        if not self.allow_user_artwork:
            raise ValueError('User artwork storage is disabled.')
        source = Path(source)
        valid, reason = validate_artwork_file(source)
        if not valid:
            raise ValueError(reason)
        if decoder is not None and not decoder(source):
            raise ValueError('The image could not be decoded.')
        identity = local_identity(device)
        if not identity:
            raise ValueError('This device has no stable local identity for an image preference.')
        extension = source.suffix.casefold()
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        filename = identity + extension
        target = self.data_dir / filename
        previous = self._read_preferences()['devices'].get(identity)
        fd, temporary = tempfile.mkstemp(prefix='.artwork-', dir=self.data_dir)
        try:
            with os.fdopen(fd, 'wb') as output, source.open('rb') as incoming:
                shutil.copyfileobj(incoming, output, length=128 * 1024)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, target)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
        self._write_preferences(identity, filename)
        if isinstance(previous, str) and previous != filename and Path(previous).name == previous:
            try:
                (self.data_dir / previous).unlink()
            except OSError:
                pass
        return target

    def clear_user_artwork(self, device):
        identity = local_identity(device)
        if not identity:
            return False
        doc = self._read_preferences()
        filename = doc['devices'].pop(identity, None)
        self._write_document(doc)
        removed = False
        for suffix in ('.png', '.webp', '.svg'):
            candidate = self.data_dir / (identity + suffix)
            try:
                candidate.unlink()
                removed = True
            except FileNotFoundError:
                pass
        if isinstance(filename, str) and Path(filename).name == filename:
            try:
                (self.data_dir / filename).unlink()
            except OSError:
                pass
        return bool(filename) or removed

    def user_name(self, device):
        if not self.allow_user_artwork:return ''
        identity = local_identity(device)
        if not identity:
            return ''
        value = self._read_preferences()['names'].get(identity, '')
        return value if isinstance(value, str) else ''

    def set_user_name(self, device, name):
        identity = local_identity(device)
        name = ' '.join(str(name or '').split())
        if not identity:
            raise ValueError('This device has no stable local identity.')
        if len(name) > 48 or any(ord(char) < 32 for char in name):
            raise ValueError('Device name must be 1–48 printable characters.')
        doc = self._read_preferences()
        if name:
            doc['names'][identity] = name
        else:
            doc['names'].pop(identity, None)
        self._write_document(doc)

    def _read_preferences(self):
        try:
            doc = json.loads(self.preferences_file.read_text(encoding='utf-8'))
            devices = doc.get('devices', {})
            names = doc.get('names', {})
            return {'version': 1,
                    'devices': devices if isinstance(devices, dict) else {},
                    'names': names if isinstance(names, dict) else {}}
        except (OSError, ValueError, TypeError):
            return {'version': 1, 'devices': {}, 'names': {}}

    def _write_preferences(self, identity, filename):
        doc = self._read_preferences()
        doc['devices'][identity] = filename
        self._write_document(doc)

    def _write_document(self, doc):
        self.preferences_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temporary = tempfile.mkstemp(prefix='.device-artwork-', dir=self.preferences_file.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(doc, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.preferences_file)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
