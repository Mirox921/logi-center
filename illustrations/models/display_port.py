"""Front-facing monitor with a confirmed HDMI/DP connector or neutral audio."""
from ..render import Model
from ..shapes import rounded_rect,Outline,circle
from ..palette import AMBER


def build(variant='audio'):
    case=rounded_rect(-140,-91,280,169,4)
    stand=rounded_rect(-13,66,26,37,2);base=rounded_rect(-57,100,114,7,2)
    def draw(p):
        p.object(stand,'metal_dark',bevel=1.3);p.object(base,'metal_dark',bevel=1)
        p.object(case,bevel=1.9,rim=True)
        p.object(rounded_rect(-135,-86,270,156,1.2),'glass_dark',bevel=.5)
        if variant in ('hdmi','dp'):
            points=((-22,-10),(22,-10),(22,4),(14,12),(-14,12),(-22,4)) if variant=='hdmi' else ((-22,-11),(14,-11),(22,-3),(22,11),(-22,11))
            p.line([*points,points[0]],AMBER,1.8,.85)
            for x in range(-15,16,5):p.line([(x,-3),(x,4)],(.8,.8,.8),1,.7)
        else:
            p.fill(Outline(((-18,-6),(-9,-6),(3,-17),(3,17),(-9,6),(-18,6))),AMBER,.8)
            for x,h in ((11,9),(20,15)):p.line([(x,-h),(x,h)],AMBER,1.7,.65)
        p.glow(rounded_rect(118,73,3,.7,.25),.2)
    return Model('display_'+variant,280,198,(case,stand,base),draw,
                 checks={'family':'display','gradient':(-110,73.5,220,.1)})
