"""Inset touch surface with faint wrist-rest corner traces, no fading rectangle."""
import cairo
from ..render import Model
from ..shapes import rounded_rect,circle


def build(variant='touchpad'):
    confirmed=variant=='touchpad'
    sw,sh=(115,74) if confirmed else (105,75)
    width,height=sw+15,sh+18
    rim=rounded_rect(-sw/2-.9,-sh/2-.9,sw+1.8,sh+1.8,sw*.03+.5)
    surface=rounded_rect(-sw/2,-sh/2,sw,sh,sw*.03)
    def draw(p):
        # Only faint physical panel corner traces. No luminous panel mask/halo.
        for sign in (-1,1):
            x=sign*(sw/2+5)
            p.line([(x,sh/2-10),(x,sh/2+5),(x-sign*17,sh/2+5)],(.065,.065,.065),.35,.14)
        p.object(rim,'graphite_matte',bevel=.35,panel=False)
        surface.path(p.ctx);p.ctx.set_source_rgba(0,0,0,.65);p.ctx.set_line_width(1.0);p.ctx.stroke()
        p.line([(-sw/2+5,-sh/2-.5),(sw/2-5,-sh/2-.5)],(.6,.6,.6),.2,.14)
        p.object(surface,'touch_surface',bevel=.4,panel=True)
        p.ctx.save();surface.path(p.ctx);p.ctx.clip()
        sheen=cairo.LinearGradient(-sw/2,-sh/2,sw/2,sh/2)
        for stop,alpha in ((0,.025),(.35,.06),(.75,0),(1,0)):sheen.add_color_stop_rgba(stop,1,1,1,alpha)
        p.ctx.set_source(sheen);p.ctx.paint()
        if confirmed:
            for yi in range(96):
                for xi in range(148):
                    x=-55+xi*.75;y=-35+yi*.75
                    if y<35:p.fill(circle(x+(yi%2)*.19,y,.055),(.65,.65,.65),.045)
            line_y=-sh/2+sh*.835
            p.line([(-sw/2+3,line_y),(sw/2-3,line_y)],(.07,.07,.07),1/p.pixel_scale,.45)
            p.line([(0,line_y),(0,sh/2-3)],(.07,.07,.07),1/p.pixel_scale,.45)
        p.ctx.restore()
    return Model(variant,width,height,(rim,),draw,
                 checks={'family':'touchpad' if confirmed else 'pointer','gradient':(-40,0,80,.1),'gradient_min_levels':3,'surface_ratio':sw/sh,'click_zone':confirmed,'microtexture':confirmed,'panel_mask':False})
