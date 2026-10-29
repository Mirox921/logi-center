"""Flat ANSI cases and keycaps; all key positions come from layouts.py."""
import cairo
from ..layouts import LAYOUTS
from ..render import Model
from ..shapes import rounded_rect
from ..palette import AMBER


def build(variant='65', backlight=.55):
    backlight=max(0.,min(1.,float(backlight)))
    layout = LAYOUTS[variant]
    width, height = layout.size_mm
    case = rounded_rect(-width / 2, -height / 2, width, height, min(width, height) * .027)
    margin = 5 if variant != 'laptop' else 2
    pitch = min((width - 2 * margin) / layout.width_u, (height - 2 * margin) / layout.height_u)
    start_x, start_y = -layout.width_u * pitch / 2, -layout.height_u * pitch / 2
    plate = rounded_rect(start_x - 1.1, start_y - 1.1,
                         layout.width_u * pitch + 2.2, layout.height_u * pitch + 2.2, 1.7)
    centres = []

    def draw(p):
        p.object(case, bevel=1.2 if variant != 'laptop' else .65, rim=True)
        p.object(plate,'graphite_matte' if variant=='laptop' else 'rubber_dark',bevel=.35 if variant=='laptop' else .6,panel=False)
        if backlight:
            p.ctx.save();plate.path(p.ctx);p.ctx.clip()
            for key in layout.keys:
                shape=rounded_rect(start_x+key.x*pitch,start_y+key.y*pitch,
                                   key.width*pitch,key.height*pitch,1.1)
                for pixels,alpha in ((6,.025),(3,.055),(1,.78)):
                    shape.path(p.ctx)
                    p.ctx.set_source_rgba(*AMBER,alpha*backlight*(.25 if variant=='laptop' else 1))
                    p.ctx.set_line_width(pixels/p.pixel_scale);p.ctx.stroke()
            if variant!='laptop':
                plate.path(p.ctx);p.ctx.set_source_rgba(*AMBER,.5*backlight)
                p.ctx.set_line_width(1/p.pixel_scale);p.ctx.stroke()
            p.ctx.restore()
        for key in layout.keys:
            gap = pitch * (.085 if variant == 'laptop' else .07)
            x, y = start_x + key.x * pitch + gap / 2, start_y + key.y * pitch + gap / 2
            w, h = key.width * pitch - gap, key.height * pitch - gap
            cap = rounded_rect(x, y, w, h, min(w, h) * .075)
            p.detail_shadow(cap, .5)
            p.object(cap, 'keycap_pbt', bevel=min(w,h)*(.035 if variant=='laptop' else .085), rim=False)
            p.ctx.save()
            cap.path(p.ctx)
            p.ctx.clip()
            dish = cairo.LinearGradient(x, y, x, y + h)
            dish.add_color_stop_rgba(0, 0, 0, 0, 0)
            dish.add_color_stop_rgba(.48, 0, 0, 0, .045)
            dish.add_color_stop_rgba(1, 0, 0, 0, 0)
            p.ctx.set_source(dish)
            p.ctx.paint()
            p.ctx.restore()

    for key in layout.keys:
        centres.append((start_x + (key.x + key.width / 2) * pitch,
                        start_y + (key.y + key.height / 2) * pitch))
    probes = {'family': 'keyboard', 'layout': variant, 'key_centres': centres,
              'case': ((12.5-layout.width_u/2)*pitch,start_y+5.05*pitch) if variant=='laptop' else (0,height/2-2), 'backlight':backlight,
              'gradient_min_levels': 3,
              'gradient': (-width / 2 + 8, -height / 2 + 1.9, width * .65, .15)}
    if variant == 'laptop':
        # The thin top lip touches the function-row plate at 1x. Probe the
        # uninterrupted left rail rather than a legitimate detail boundary.
        probes['gradient_line'] = ((-width / 2 + 1.3, -height / 2 + 6),
                                   (-width / 2 + 1.3, -height / 2 + 6 + height * .8))
    return Model('keyboard_' + variant, width, height, (case,), draw, checks=probes)
