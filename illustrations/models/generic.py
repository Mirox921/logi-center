"""Different neutral silhouettes; no unknown transport implies a speaker."""
from ..render import Model
from ..shapes import rounded_rect,circle,Outline
from ..palette import AMBER


def build(variant='unknown'):
    width,height={'usb_audio':(144,76),'builtin_audio':(205,28),
                  'bluetooth_audio':(90,90),'audio_unknown':(128,56)}.get(variant,(94,98))
    case=(Outline(((-47,-35),(-33,-49),(47,-49),(47,35),(33,49),(-47,49)))
          if variant=='unknown' else circle(0,0,45) if variant=='bluetooth_audio' else rounded_rect(-width/2,-height/2,width,height,4))
    def draw(p):
        p.object(case,bevel=1.1,rim=True)
        if variant=='builtin_audio':
            p.object(rounded_rect(-width/2+3,-height/2+3,width-6,height-6,1),'rubber_dark',bevel=.4)
            for y in range(-7,8,3):
                for x in range(-95,96,3):p.object(circle(x,y,.5),'metal_dark',bevel=.15,panel=False)
        elif variant=='bluetooth_audio':
            # Neutral wireless audio receiver, not an asserted portable speaker.
            p.object(circle(0,0,38),'panel',bevel=.65)
            p.line([(0,-28),(11,-17),(-11,5),(0,16),(0,-28),(-11,-17),(11,5),(0,16)],AMBER,1.35,.82)
            for x in (-12,0,12):p.line([(x,25),(x,28)],(.1,.1,.1),1,.7)
        elif variant=='audio_unknown':
            p.object(circle(-32,0,18),'metal_dark',bevel=1.2)
            p.object(circle(-32,0,14),'rubber_dark',bevel=.9)
            for index in range(5):
                h=5+index*2;p.line([(-3+index*8,-h),(-3+index*8,h)],(.39,.39,.39),2,.8)
        elif variant=='usb_audio':
            for x,r in ((-42,13),(-5,8),(26,8)):
                p.object(circle(x,-4,r),'metal_dark',bevel=1,shadow=True)
                p.object(circle(x,-4,r-2),'rubber_dark',bevel=.8)
                p.line([(x,-r+1),(x,-r+4)],(.8,.8,.8),.7,.7)
            p.object(rounded_rect(48,-12,11,15,1),'rubber_dark',bevel=.5)
        else:
            p.object(rounded_rect(-38,-38,76,72,1.5),'panel',bevel=.5)
            for row in range(5):
                for col in range(7):p.object(rounded_rect(-30+col*9,-28+row*11,3,3,.4),'metal_dark',bevel=.3)
        if variant=='bluetooth_audio':p.glow(rounded_rect(-3.5,33,7,1.1,.4),.18)
        elif variant!='builtin_audio':p.glow(rounded_rect(width/2-19,height/2-10,7,1.1,.4),.18)
    return Model(variant,width,height,(case,),draw,checks={'family':'module'})
