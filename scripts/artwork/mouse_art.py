"""Vector mouse illustration shared by the GTK editor and offline previews."""
import math
import cairo
from logi_center.core.devices.mouse_models import layout

WIDTH=480;HEIGHT=440

def callouts(count):
    """Keep numbered controls outside the shell, with generous hit areas."""
    if count>12:return {i:(50+(i%8)*54,70+(i//8)*44) for i in range(count)}
    left=[i for i in range(count) if i%2==0];right=[i for i in range(count) if i%2]
    result={}
    for side,indices in [(False,left),(True,right)]:
        for row,index in enumerate(indices):
            result[index]=(426 if side else 54,74+row*min(56,290/max(1,len(indices)-1)))
    return result

def path(cr,points):
    for op,*values in points:getattr(cr,op)(*values)

def panel(cr,points,top,bottom,stroke=(.30,.33,.38)):
    path(cr,points);cr.close_path()
    gradient=cairo.LinearGradient(190,40,300,360);gradient.add_color_stop_rgb(0,*top);gradient.add_color_stop_rgb(1,*bottom)
    cr.set_source(gradient);cr.fill_preserve();cr.set_source_rgb(*stroke);cr.set_line_width(1);cr.stroke()

def render(cr,width,height,name,selected=None,count=11,studio=True):
    cr.save();scale=min(width/WIDTH,height/HEIGHT);cr.translate((width-WIDTH*scale)/2,(height-HEIGHT*scale)/2);cr.scale(scale,scale)
    if studio:
        # A soft studio halo and contact shadow keep the silhouette legible.
        halo=cairo.RadialGradient(252,205,25,252,205,240)
        halo.add_color_stop_rgba(0,.12,.36,.43,.24);halo.add_color_stop_rgba(1,.09,.13,.18,0)
        cr.set_source(halo);cr.rectangle(0,0,WIDTH,HEIGHT);cr.fill()
        for radius in range(14,0,-1):
            cr.save();cr.translate(248,375);cr.scale(1,.2);cr.arc(0,0,90+radius*2,0,math.tau);cr.set_source_rgba(0,0,0,.012);cr.fill();cr.restore()
    g502='G502' in name
    if g502:
        cr.set_source_rgb(.12,.14,.17);cr.set_line_width(8);cr.move_to(250,0);cr.curve_to(250,18,259,24,258,41);cr.stroke()
        # G502: angular right shell, flared thumb shelf and divided click plates.
        body=[('move_to',191,44),('curve_to',218,31,276,31,300,48),('line_to',324,116),('line_to',330,205),('curve_to',351,279,328,355,288,383),('curve_to',252,409,193,390,177,364),('line_to',143,326),('line_to',135,274),('line_to',159,242),('line_to',167,137),('close_path',)]
        panel(cr,body,(.20,.23,.27),(.065,.078,.10))
        panel(cr,[('move_to',172,203),('line_to',185,251),('line_to',173,318),('line_to',148,306),('line_to',145,272)],(.13,.15,.18),(.055,.065,.08))
        panel(cr,[('move_to',193,48),('curve_to',208,39,236,38,245,41),('line_to',243,165),('line_to',213,183),('line_to',178,161),('line_to',181,97)],(.30,.33,.37),(.14,.16,.20))
        panel(cr,[('move_to',269,41),('curve_to',281,41,294,44,300,52),('line_to',319,122),('line_to',315,176),('line_to',275,186),('line_to',265,160)],(.25,.28,.32),(.11,.13,.16))
        panel(cr,[('move_to',215,202),('line_to',272,202),('line_to',313,185),('line_to',322,258),('curve_to',326,318,304,367,278,381),('curve_to',246,397,211,376,195,352),('line_to',186,284)],(.16,.18,.22),(.085,.10,.125))
        # DPI paddles and two distinct thumb buttons.
        for x,y in [(185,77),(181,112)]:
            panel(cr,[('move_to',x,y),('line_to',x+12,y-5),('line_to',x+9,y+25),('line_to',x-4,y+29)],(.36,.38,.41),(.12,.14,.17))
        for y in [174,211]:
            panel(cr,[('move_to',163,y),('line_to',181,y-9),('line_to',183,y+20),('line_to',162,y+28)],(.31,.33,.36),(.10,.12,.15))
        panel(cr,[('move_to',147,261),('line_to',166,245),('line_to',173,267),('line_to',154,285)],(.26,.28,.31),(.09,.11,.14))
        # Rubber grip texture follows the thumb rest.
        cr.set_source_rgba(.48,.52,.57,.16);cr.set_line_width(1)
        for y in range(294,330,6):cr.move_to(155,y);cr.line_to(173,y+8);cr.stroke()
        # Small DPI indicators, purely schematic, never a reported device color.
        for y in [220,230,240]:cr.set_source_rgba(.22,.77,.88,.8);cr.rectangle(201,y,3,5);cr.fill()
    else:
        panel(cr,[('move_to',198,49),('curve_to',219,31,282,31,300,54),('curve_to',328,98,330,265,311,335),('curve_to',293,404,210,405,186,346),('curve_to',158,273,165,111,198,49)],(.25,.28,.32),(.075,.09,.115))
        for x,end in [(193,242),(268,307)]:
            panel(cr,[('move_to',x,64),('curve_to',x+8,45,end-6,44,end,57),('line_to',end,177),('line_to',x,184)],(.31,.34,.38),(.13,.15,.18))
        for y in [194,233]:
            panel(cr,[('move_to',174,y),('line_to',186,y-5),('line_to',184,y+24),('line_to',172,y+27)],(.27,.30,.33),(.10,.12,.15))
    # Metallic, ribbed scroll wheel with recessed housing.
    cr.set_source_rgb(.035,.045,.06);cr.rectangle(242,73,26,90);cr.fill()
    wheel=cairo.LinearGradient(246,0,264,0)
    for offset,shade in [(0,.22),(.3,.65),(.55,.73),(1,.24)]:wheel.add_color_stop_rgb(offset,shade,shade+.015,shade+.03)
    cr.set_source(wheel);cr.rectangle(247,82,16,62);cr.fill()
    cr.set_line_width(1);cr.set_source_rgba(.03,.04,.06,.8)
    for y in range(85,144,5):cr.move_to(247,y);cr.line_to(263,y);cr.stroke()
    panel(cr,[('move_to',246,179),('line_to',264,179),('line_to',266,193),('line_to',244,193)],(.26,.29,.32),(.10,.12,.15))
    # Subtle geometric palm mark, no external images or misleading live RGB.
    cr.set_source_rgba(.52,.70,.76,.50) if 'G502' in name or 'G305' in name else cr.set_source_rgba(0,0,0,0)
    cr.set_line_width(3);cr.move_to(265,314);cr.line_to(246,314);cr.line_to(238,324);cr.line_to(238,340);cr.line_to(259,340);cr.line_to(259,330);cr.line_to(250,330);cr.stroke()
    anchors=layout(name,count)
    for index,(x,y) in anchors.items():
        ax,ay=x*WIDTH,y*HEIGHT;cx,cy=callouts(count)[index];active=index==selected
        cr.set_line_width(1.6 if active else .8)
        cr.set_source_rgba(*((.30,.83,.96,.95) if active else (.55,.64,.71,.32)))
        direction=1 if cx<WIDTH/2 else -1
        if active:
            cr.move_to(cx+direction*19,cy);cr.line_to(cx+direction*43,cy);cr.line_to(ax-direction*12,ay);cr.line_to(ax,ay);cr.stroke()
        if active:
            cr.set_source_rgba(.22,.79,.95,.12);cr.arc(ax,ay,12,0,math.tau);cr.fill()
        cr.set_source_rgba(*((.40,.90,1.,1.) if active else (.55,.64,.71,.38)));cr.arc(ax,ay,3 if active else 2,0,math.tau);cr.fill()
    cr.restore()
