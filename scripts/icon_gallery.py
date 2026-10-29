#!/usr/bin/env python3
"""Cairo-only artwork contact sheets, 1x/2x on dark/light backgrounds."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import cairo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from illustrations.models import ARTWORK_KEYS
from illustrations.palette import TOKENS, rgb
from illustrations.units import WIDTH, HEIGHT


def contact_sheet(source, output, density, background, foreground, suffix, keys=ARTWORK_KEYS):
    columns, tile_w, tile_h = min(4,len(keys)), 320, 240
    rows = (len(keys) + columns - 1) // columns
    sheet = cairo.ImageSurface(cairo.FORMAT_ARGB32, columns * tile_w * density, rows * tile_h * density)
    ctx = cairo.Context(sheet)
    ctx.scale(density, density)
    ctx.set_source_rgb(*rgb(background))
    ctx.paint()
    for index, key in enumerate(keys):
        x, y = (index % columns) * tile_w, (index // columns) * tile_h
        path = source / f'{key.replace("_", "-")}@{density}x.png'
        if not path.is_file():
            raise SystemExit(f'FAIL: missing asset {path}')
        image = cairo.ImageSurface.create_from_png(str(path))
        if (image.get_width(), image.get_height()) != (WIDTH * density, HEIGHT * density):
            raise SystemExit(f'FAIL: malformed asset {path}')
        ctx.set_source_rgba(*rgb(foreground), .15)
        ctx.set_line_width(1)
        ctx.rectangle(x + 8.5, y + 8.5, tile_w - 17, tile_h - 17)
        ctx.stroke()
        ctx.save()
        ctx.translate(x + 8, y + 15)
        ctx.scale(304 / image.get_width(), 190 / image.get_height())
        ctx.set_source_surface(image)
        ctx.paint()
        ctx.restore()
        ctx.set_source_rgb(*rgb(foreground))
        ctx.select_font_face('monospace')
        ctx.set_font_size(11)
        ctx.move_to(x + 16, y + 208)
        ctx.show_text(key.upper())
        ctx.set_font_size(9)
        ctx.set_source_rgba(*rgb(foreground), .65)
        ctx.move_to(x + 16, y + 223)
        ctx.show_text(f'generated / MIT / {density}x / '+hashlib.sha256(path.read_bytes()).hexdigest()[:10])
    target = output / (f'contact-{suffix}' + ('@2x' if density == 2 else '') + '.png')
    sheet.write_to_png(str(target))
    print(f'PASS: {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target} ({len(keys)} classes, {density}x)')


def miniature_sheet(source,output):
    keys=('bluetooth_audio','builtin_audio','audio_unknown','unknown','touchpad')
    image=cairo.ImageSurface(cairo.FORMAT_ARGB32,600,160)
    p=cairo.Context(image);p.set_source_rgb(*rgb(TOKENS['background']));p.paint()
    for index,key in enumerate(keys):
        asset=cairo.ImageSurface.create_from_png(str(source/f'{key.replace("_","-")}@2x.png'))
        p.save();p.translate(index*120+28,12);p.scale(64/asset.get_width(),40/asset.get_height())
        p.set_source_surface(asset);p.paint();p.restore()
        p.set_source_rgb(*rgb(TOKENS['text']));p.select_font_face('monospace');p.set_font_size(9)
        p.move_to(index*120+4,80);p.show_text(key)
    image.write_to_png(str(output/'neutral-64px.png'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'qml_ui/assets/devices/generated')
    parser.add_argument('--keys',nargs='+',choices=ARTWORK_KEYS)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/screenshots/redesign/icons')
    args = parser.parse_args()
    keys=args.keys or ARTWORK_KEYS
    args.output.mkdir(parents=True, exist_ok=True)
    for density in (1, 2):
        for bg, fg, suffix in ((TOKENS['background'], TOKENS['text'], 'dark'), ('#eeeeee', '#222222', 'light')):
            contact_sheet(args.source, args.output, density, bg, fg, suffix,keys)
    lines=['# Actual artwork sources and content hashes','','| Class / variant | Actual file | SHA-256 | Source |','|---|---|---|---|']
    manifest=[]
    for key in keys:
        for density in (1,2):
            path=args.source/f'{key.replace("_","-")}@{density}x.png'
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            shown=path.resolve().relative_to(ROOT).as_posix() if path.resolve().is_relative_to(ROOT) else path.name
            lines.append(f'| `{key}` | `{shown}` | `{digest}` | generated · project / MIT |')
            manifest.append({'class':key,'file':shown,'sha256':digest,'source':'generated'})
    lines+=['','No exact-model product images are bundled. All models including K7 Ultra, Ace68-II, G502 HERO and G PRO X use generic class illustrations unless a local user image is chosen. Unknown Bluetooth class is neutral, never asserted to be a speaker.']
    (args.output/'sources.md').write_text('\n'.join(lines)+'\n')
    (args.output/'sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if not args.keys:
        for name,subset in (('series',('mouse_gaming','keyboard_65','headset','touchpad','speakers')),
                            ('neutral',('bluetooth_audio','builtin_audio','audio_unknown','unknown','touchpad'))):
            for density in (1,2):
                for bg,fg,suffix in ((TOKENS['background'],TOKENS['text'],'dark'),('#eeeeee','#222222','light')):
                    contact_sheet(args.source,args.output,density,bg,fg,name+'-'+suffix,subset)
        miniature_sheet(args.source,args.output)
    print('PASS: source table written; renderer/gallery requires only pycairo.')


if __name__ == '__main__':
    main()
