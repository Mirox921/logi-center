"""Front-view capsule, grille, yoke and desktop stand."""
from ..render import Model
from ..shapes import rounded_rect, circle


def build():
    capsule = rounded_rect(-23, -77, 46, 101, (20, 20, 12, 12))
    base = rounded_rect(-48, 67, 96, 13, 5)
    stem = rounded_rect(-4.5, 25, 9, 43, 2)
    left, right = rounded_rect(-29, -15, 5, 55, 2), rounded_rect(24, -15, 5, 55, 2)
    bottom = rounded_rect(-26, 35, 52, 6, 2)
    def draw(p):
        for part in (base, stem, left, right, bottom):
            p.object(part, 'metal_dark', bevel=.9)
        p.object(capsule, bevel=1.4, shadow=True)
        grille = rounded_rect(-19, -73, 38, 61, (17, 17, 4, 4))
        p.object(grille, 'metal_dark', bevel=.75)
        p.ctx.save()
        grille.path(p.ctx)
        p.ctx.clip()
        for y in range(-68, -14, 3):
            for x in range(-17, 18, 3):
                p.fill(circle(x + (1.5 if y % 2 else 0), y, .52), (.045, .045, .045), .75)
        p.ctx.restore()
        p.object(circle(0, 4, 5), 'rubber_dark', bevel=.7)
        p.glow(rounded_rect(-2, 15, 4, 1, .4), .2)
    return Model('microphone', 96, 157, (capsule, base, stem, left, right, bottom), draw,
                 checks={'family': 'microphone', 'gradient': (-17, -7, 34, .1)})
