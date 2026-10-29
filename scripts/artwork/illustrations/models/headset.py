"""Front-facing headset with a single continuous padded headband."""
import math
from ..render import Model
from ..shapes import Outline, rounded_rect, bezier, ribbon, circle


def arc_band(rx, ry, thickness, cy):
    outer = [(rx * math.cos(t), cy - ry * math.sin(t)) for t in (math.pi * i / 100 for i in range(101))]
    inner = [((rx - thickness) * math.cos(t), cy - (ry - thickness) * math.sin(t))
             for t in (math.pi * i / 100 for i in range(100, -1, -1))]
    return Outline(tuple(outer + inner))


def build(variant='headset'):
    band = arc_band(79, 81, 9, -3)
    cushion = arc_band(69.5, 69.5, 5, -2.5)
    cups = tuple(rounded_rect(x, -5, 44, 74, (16, 16, 18, 18)) for x in (-95, 51))
    yokes = tuple(rounded_rect(x, -18, 8, 58, 3) for x in (-82, 74))
    boom_line = bezier((75, 54), (77, 89), (53, 101), (17, 99))
    boom = ribbon(boom_line, 1.6)
    mic = rounded_rect(4, 92, 25, 13, 5)
    has_mic = variant == 'headset'
    outlines = (band, cushion, *yokes, *cups) + ((boom, mic) if has_mic else ())
    def draw(p):
        p.object(band, bevel=1.6, rim=True)
        p.object(cushion, 'rubber_dark', bevel=.9, panel=False)
        for yoke in yokes:
            p.object(yoke, 'metal_dark', bevel=.8)
        for x in (-78, 78):
            p.object(circle(x, -10, 2), 'metal_dark', bevel=.35)
            p.line([(x - .75, -10), (x + .75, -10)], (.08, .08, .08), .3)
        for side, cup in zip((-1, 1), cups):
            p.object(cup, bevel=1.35, shadow=True, rim=True)
            x = -90 if side < 0 else 56
            p.object(rounded_rect(x, 0, 34, 64, 13), 'rubber_dark', bevel=2.5, shadow=True)
            p.object(rounded_rect(x + 4, 5, 26, 53, 10), 'panel', bevel=.7)
        if has_mic:
            p.object(boom, 'metal_dark', bevel=.55)
            p.object(circle(75, 54, 3.2), 'rubber_dark', bevel=.5)
            p.object(mic, 'rubber_dark', bevel=1.1)
            for x in range(9, 26, 3):
                p.line([(x, 96), (x, 101)], (.35, .35, .35), .6, .35)
        if variant == 'bluetooth':
            p.glow(rounded_rect(85, 47, 1.1, 5, .4), .18)
    return Model(variant, 190, 193 if has_mic else 165, outlines, draw,
                 checks={'family': 'headset', 'gradient': (0, 0, 1, 1),
                         'gradient_line': ((-93, 12), (-93, 50)), 'gradient_min_levels': 3},
                 symmetry_outlines=(band, cushion, *yokes, *cups))
