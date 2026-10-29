"""Native 1x/2x review pairs on both backgrounds, without Qt or image libraries."""
import argparse
from pathlib import Path
import cairo
from .palette import TOKENS, rgb


def review_pair(key, source, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    width, height = 1568, 1380
    sheet = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(sheet)
    for row, (background, foreground) in enumerate(((TOKENS['background'], TOKENS['text']), ('#eeeeee', '#222222'))):
        y = row * 690
        ctx.set_source_rgb(*rgb(background))
        ctx.rectangle(0, y, width, 690)
        ctx.fill()
        for density, x in ((1, 0), (2, 528)):
            path = Path(source) / f'{key.replace("_", "-")}@{density}x.png'
            if not path.is_file():
                path = Path(source) / f'{key}@{density}x.png'
            image = cairo.ImageSurface.create_from_png(str(path))
            image_y = y + 35 + (640 - image.get_height()) / 2
            ctx.set_source_surface(image, x + 8, image_y)
            ctx.paint()
            ctx.set_source_rgb(*rgb(foreground))
            ctx.select_font_face('monospace')
            ctx.set_font_size(12)
            ctx.move_to(x + 12, y + 22)
            ctx.show_text(f'{key} / {density}x native / {image.get_width()}x{image.get_height()}')
    target = output / f'{key}-review.png'
    sheet.write_to_png(str(target))
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--only', nargs='+', default=['mouse_gaming', 'keyboard_65', 'headset'])
    args = parser.parse_args()
    for key in args.only:
        print(review_pair(key, args.input, args.output))


if __name__ == '__main__':
    main()
