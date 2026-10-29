"""Screen-space top-left key / bottom-right fill, with sub-LSB Bayer dither."""
from functools import lru_cache
import math
import sys
import cairo

# Ordered, deterministic +/-0.5 LSB. No time, RNG, stipple or texture noise.
BAYER = ((0, 32, 8, 40, 2, 34, 10, 42), (48, 16, 56, 24, 50, 18, 58, 26),
         (12, 44, 4, 36, 14, 46, 6, 38), (60, 28, 52, 20, 62, 30, 54, 22),
         (3, 35, 11, 43, 1, 33, 9, 41), (51, 19, 59, 27, 49, 17, 57, 25),
         (15, 47, 7, 39, 13, 45, 5, 37), (63, 31, 55, 23, 61, 29, 53, 21))


def multiply(colour, value):
    return tuple(min(1., max(0., channel * value)) for channel in colour)


@lru_cache(maxsize=128)
def gradient_surface(width, height, start, end, curved=False):
    width, height = max(2, width), max(2, height)
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_RGB24, width)
    data = bytearray(stride * height)
    little = sys.byteorder == 'little'
    for y in range(height):
        for x in range(width):
            t = .56 * x / (width - 1) + .44 * y / (height - 1)
            crown = 1 + .12 * max(0, 1 - math.hypot((x / width - .33) / .62,
                                                    (y / height - .66) / .60)) if curved else 1
            dither = (BAYER[y % 8][x % 8] + .5) / 64 - .5
            rgb = [max(0, min(255, round(255 * (a * (1 - t) + b * t) * crown + dither)))
                   for a, b in zip(start, end)]
            i = y * stride + x * 4
            data[i:i + 4] = bytes((*reversed(rgb), 255) if little else (255, *rgb))
    return cairo.ImageSurface.create_for_data(data, cairo.FORMAT_RGB24, width, height, stride)


def set_gradient(ctx, bounds, start, end, pixel_scale, curved=False):
    x, y, w, h = bounds
    surface = gradient_surface(max(2, math.ceil(w * pixel_scale)), max(2, math.ceil(h * pixel_scale)),
                               tuple(start), tuple(end), curved)
    pattern = cairo.SurfacePattern(surface)
    pattern.set_extend(cairo.EXTEND_PAD)
    pattern.set_filter(cairo.FILTER_BILINEAR)
    pattern.set_matrix(cairo.Matrix(xx=surface.get_width() / w, yy=surface.get_height() / h,
                                    x0=-x * surface.get_width() / w, y0=-y * surface.get_height() / h))
    ctx.set_source(pattern)
