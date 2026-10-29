"""One continuous shell; button zones are clipped light fields, not added boxes."""
from ..render import Model
from ..shapes import rounded_rect,Outline,bezier,offset_fill,catmull_rom
from ..light import set_gradient,multiply
from ..materials import MATERIALS
import cairo


def shell(width,height,variant):
    # 20 controls based on iteration4. Cubic B-spline expressed as Bezier spans is C2,
    # including the periodic closure; no conditional waist displacement.
    # Authoritative silhouette: iteration4, retained by user's latest correction.
    right=[(0,-60),(14,-59),(24,-55),(28,-48),(29,-30),(29,-12),
           (31,8),(33,29),(30,44),(21,55),(0,60)]
    left=[(-x,y) for x,y in reversed(right[1:-1])]
    if variant=='gaming':
        import math
        left=[(x+2.5*math.exp(-((y+5)/22)**4),y) for x,y in left]
    controls=right+left
    curve=[];spans=[]
    for i in range(len(controls)):
        a,b,c,d=[controls[(i+j)%len(controls)] for j in range(4)]
        p0=tuple((a[k]+4*b[k]+c[k])/6 for k in range(2))
        p1=tuple((2*b[k]+c[k])/3 for k in range(2))
        p2=tuple((b[k]+2*c[k])/3 for k in range(2))
        p3=tuple((b[k]+4*c[k]+d[k])/6 for k in range(2))
        spans.append((p0,p1,p2,p3))
        curve.extend(bezier(p0,p1,p2,p3,steps=32)[:-1])
    shape=Outline(tuple(curve));x,y,w,h=shape.bounds
    def transform(point):return ((point[0]-x-w/2)*width/w,(point[1]-y-h/2)*height/h)
    return Outline(tuple(map(transform,curve))),tuple(tuple(map(transform,span)) for span in spans)


def build(variant='generic'):
    width,height=(55,103) if variant=='compact' else (70,124) if variant=='gaming' else (66,120)
    body,spans=shell(width,height,variant);sy=height/120
    ww=max(6,min(7,width*.1))
    wh=max(16,min(18,ww*2.5))
    gap=max(.8,min(1.,width*.9/70))
    wheel_y=-44*sy
    seam=-height/2+height*.45
    slot=rounded_rect(-(ww+1.8)/2,wheel_y-1.4,ww+1.8,wh+3,3.5)
    wheel=rounded_rect(-ww/2,wheel_y,ww,wh,ww*.45)
    def edge(y):
        values=[]
        points=body.points
        for a,b in zip(points,points[1:]+points[:1]):
            if a[1]<=y<b[1] or b[1]<=y<a[1]:values.append(a[0]+(b[0]-a[0])*(y-a[1])/(b[1]-a[1]))
        return min(values)
    side_shapes=[];side_info=[]
    if variant in ('gaming','wireless'):
        for center in (-height/2+height*.38,-height/2+height*.38+13):
            points=[]
            for y,offset in ((center-5,.6),(center-3.5,-.4),(center+3.5,-.4),(center+5,.6),
                             (center+4,2.6),(center-4,2.6)):
                points.append((edge(y)+offset,y))
            shape=catmull_rom(points,steps=12);side_shapes.append(shape)
            protrusion=max(edge(y)-x for x,y in shape.points)
            side_info.append({'center_y':center,'fraction':(center+height/2)/height,'protrusion_mm':protrusion})
    def draw(p):
        p.object(body,bevel=1.05,rim=True)
        base=MATERIALS['graphite_matte'].base
        offset_fill(p.ctx,body,1.3,lambda:set_gradient(p.ctx,body.bounds,multiply(base,1.12),multiply(base,.87),p.pixel_scale,curved=True))
        p.ctx.save();body.path(p.ctx);p.ctx.clip()
        crown=cairo.RadialGradient(-width*.15,height*.05,1,0,height*.12,width*.95)
        crown.add_color_stop_rgba(0,1,1,1,.045);crown.add_color_stop_rgba(1,1,1,1,0)
        p.ctx.set_source(crown);p.ctx.paint()
        p.ctx.save();p.ctx.rectangle(-width/2,-height/2,width,height*.45);p.ctx.clip()
        offset_fill(p.ctx,body,1.15,lambda:set_gradient(p.ctx,body.bounds,multiply(base,1.09),multiply(base,.91),p.pixel_scale));p.ctx.restore()
        p.line([(-width/2,seam),(width/2,seam)],(.025,.025,.025),gap,.9)
        p.line([(-width/2,seam-.55),(width/2,seam-.55)],(.36,.36,.36),.22,.35)
        p.line([(0,-height/2),(0,seam)],(.02,.02,.02),gap,.92)
        p.line([(-.55,-height/2),(-.55,seam-.5)],(.4,.4,.4),.2,.35)
        p.ctx.restore()
        p.object(slot,'rubber_dark',bevel=.25,panel=False)
        p.detail_shadow(wheel,.35);p.object(wheel,'rubber_dark',bevel=.2,panel=False)
        p.ctx.save();wheel.path(p.ctx);p.ctx.clip()
        set_gradient(p.ctx,wheel.bounds,(.13,.13,.13),(.055,.055,.055),p.pixel_scale);p.ctx.paint();p.ctx.restore()
        p.ctx.save();wheel.path(p.ctx);p.ctx.clip()
        for i in range(14):
            y=wheel_y+1.3+i*1.05;p.line([(-ww/2+.4,y),(ww/2-.4,y)],(.35,.35,.35),.18,.19)
        p.ctx.restore()
        p.line([(-ww/2+.7,wheel_y+2),(-ww/2+.3,wheel_y+5)],(.55,.55,.55),.24,.45)
        for side in side_shapes:
            p.detail_shadow(side,.20);p.object(side,'side_control',bevel=.28,panel=True)
        if variant=='gaming':
            # User-requested class artwork, never an exact hardware model claim.
            p.object(rounded_rect(-1.8,-20*sy,3.6,2.4*sy,.7),'rubber_dark',bevel=.18)
            mark=Outline(((0,36*sy),(1,37*sy),(0,38*sy),(-1,37*sy)))
            p.glow(mark,.18)
        elif variant=='wireless':p.glow(rounded_rect(-1,37*sy,2,.55,.2),.12)
    return Model('mouse_'+variant,width,height,(body,*side_shapes),draw,
                 checks={'family':'mouse','gap':(0,-14*sy),'button':(-15,-19*sy),'gradient':(0,22*sy,16,10*sy),
                         'control_count':20,'button_length_ratio':.45,'wheel_width_ratio':ww/width,'wheel_width_mm':ww,'bezier_spans':spans,
                         'wheel_length_mm':wh,'variant':variant,'side_buttons':tuple(side_info), 'contour':body.points,'mark_length_mm':2 if variant=='gaming' else .55 if variant=='wireless' else 0},
                 symmetry_outlines=(body,) if variant!='gaming' else ())
