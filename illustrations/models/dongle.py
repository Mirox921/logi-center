"""USB receiver, top view, with distinct metal plug and dark shell."""
from ..render import Model
from ..shapes import rounded_rect


def build():
    plug = rounded_rect(-6, -22, 12, 15, .6)
    case = rounded_rect(-9.5, -10, 19, 32, 2.4)
    def draw(p):
        p.object(plug, 'metal_dark', bevel=.5)
        for x in (-3.5, 1.5):
            p.object(rounded_rect(x, -19, 2, 4.2, .2), 'rubber_dark', bevel=.12, panel=False)
        p.line([(-5, -11.5), (5, -11.5)], (.1, .1, .1), .35)
        p.object(case, bevel=.65, rim=True)
        p.glow(rounded_rect(-1.5, 11, 3, .8, .3), .22)
    return Model('receiver', 19, 44, (plug, case), draw,
                 checks={'family': 'receiver', 'gradient': (0, 0, 1, 1),
                         'gradient_line': ((-5, -5), (-5, 18))})
