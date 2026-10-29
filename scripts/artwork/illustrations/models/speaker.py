"""Matched front-facing speaker pair, concentric driver layers."""
import cairo
from ..render import Model
from ..shapes import rounded_rect, circle


def build():
    cases = tuple(rounded_rect(x, -58, 57, 116, 4) for x in (-66, 9))
    def draw(p):
        for case in cases:
            p.object(case, bevel=1.8, rim=True)
            x, _, w, _ = case.bounds
            cx = x + w / 2
            p.object(rounded_rect(x + 3, -55, w - 6, 109, 2.4), 'panel', bevel=.6)
            for cy, radius in ((18, 21), (-31, 10)):
                p.object(circle(cx, cy, radius + 1), 'metal_dark', bevel=.8)
                p.object(circle(cx, cy, radius - 1), 'rubber_dark', bevel=1.8)
                p.object(circle(cx, cy, radius - 4), 'speaker_cone', bevel=.8)
                cone = cairo.RadialGradient(cx - 3, cy - 4, 1, cx, cy, radius - 4)
                cone.add_color_stop_rgba(0, 1, 1, 1, .12)
                cone.add_color_stop_rgba(1, 0, 0, 0, .4)
                circle(cx, cy, radius - 4).path(p.ctx)
                p.ctx.set_source(cone)
                p.ctx.fill()
                p.object(circle(cx, cy, max(2.2, radius * .25)), 'rubber_dark', bevel=.65)
            p.glow(circle(cx, 46, .75), .2)
    return Model('speakers', 132, 116, cases, draw,
                 checks={'family': 'speakers', 'gradient': (0, 0, 1, 1),
                         'gradient_line': ((-64.5, -50), (-64.5, 50))}, symmetry_outlines=cases)
