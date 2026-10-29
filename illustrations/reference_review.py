"""Private local contour overlays. Reference pixels never enter generated assets.

Default output is /tmp; the source pack intentionally excludes user-provided
reference photos. Filenames describe references, not verified hardware revisions.
"""
import argparse
from pathlib import Path
import cairo
from .checks import Pixels
from .models import build_model

REFERENCES = (
    ('k7-ultra-top.png', 'mouse_gaming', (0, .12, .47, .91), 'height'),
    ('ace68-ii-top.png', 'keyboard_65', (.115, .32, .98, .75), 'width'),
    ('g-pro-x-front.png', 'headset', (.13, 0, .84, .98), 'height'),
    ('g502-hero-top.png', 'mouse_gaming', (.26, .09, .76, .94), 'height'),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--references', type=Path, default=Path(__file__).resolve().parents[1] / 'docs')
    parser.add_argument('--output', type=Path, default=Path('/tmp/logi-2d-reference-overlays'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for filename, key, roi, anchor in REFERENCES:
        path = args.references / filename
        if not path.is_file():
            print('SKIP: local reference absent:', filename)
            continue
        photo = cairo.ImageSurface.create_from_png(str(path))
        pixels = Pixels(photo)
        points = []
        for y in range(int(roi[1] * pixels.height), int(roi[3] * pixels.height)):
            for x in range(int(roi[0] * pixels.width), int(roi[2] * pixels.width)):
                r, g, b, a = pixels.rgba(x, y)
                if a > 200 and min(r, g, b) < 220:
                    points.append((x, y))
        if not points:
            print('SKIP: no reference silhouette detected:', filename)
            continue
        xs, ys = zip(*points)
        left, top, w, h = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
        sheet = cairo.ImageSurface(cairo.FORMAT_ARGB32, 720, 520)
        ctx = cairo.Context(sheet)
        ctx.set_source_rgb(.93, .93, .93)
        ctx.paint()
        scale = min(620 / w, 420 / h)
        ctx.save()
        ctx.translate(360, 270)
        ctx.scale(scale, scale)
        ctx.translate(-left - w / 2, -top - h / 2)
        ctx.rectangle(left, top, w, h)
        ctx.clip()
        ctx.set_source_surface(photo)
        ctx.paint()
        ctx.restore()
        model = build_model(key)
        factor = scale * (w / model.width_mm if anchor == 'width' else h / model.height_mm)
        ctx.save()
        ctx.translate(360, 270)
        ctx.scale(factor, factor)
        cx, cy = model.centre
        ctx.translate(-cx, -cy)
        ctx.set_source_rgba(1, .54, .06, .85)
        ctx.set_line_width(1.5 / factor)
        for outline in model.outlines:
            outline.path(ctx)
            ctx.stroke()
        ctx.restore()
        ctx.set_source_rgb(.15, .15, .15)
        ctx.select_font_face('monospace')
        ctx.set_font_size(12)
        ctx.move_to(16, 22)
        ctx.show_text(f'{filename} / {key}: generic contour, {anchor}-aligned')
        ctx.move_to(16, 43)
        ctx.show_text('Shape comparison only; revision and redistribution rights not verified.')
        target = args.output / filename
        sheet.write_to_png(str(target))
        print(target)


if __name__ == '__main__':
    main()
