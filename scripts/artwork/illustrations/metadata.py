"""Offline opaque bounds for runtime framing; GUI never imports Cairo."""
import json
from pathlib import Path
import cairo
from .checks import Pixels


def family(key):
    if key in ('mouse','mouse_gaming','mouse_wireless','mouse_compact'):return 'mouse'
    if key.startswith('keyboard'):return 'keyboard'
    return key


def write_metadata(output):
    output=Path(output);classes={};families={}
    for path in sorted(output.glob('*@1x.png')):
        key=path.name.removesuffix('@1x.png').replace('-','_')
        surface=cairo.ImageSurface.create_from_png(str(path))
        l,t,r,b=Pixels(surface).bounds(245)
        if r<l:raise ValueError('Empty illustration: '+key)
        bounds=[l/surface.get_width(),t/surface.get_height(),(r+1)/surface.get_width(),(b+1)/surface.get_height()]
        sl,st,sr,sb=Pixels(surface).bounds(1)
        shadow=[sl/surface.get_width(),st/surface.get_height(),(sr+1)/surface.get_width(),(sb+1)/surface.get_height()]
        group=family(key)
        classes[key]={'bounds':bounds,'shadow_bounds':shadow,'family':group}
        maxima=families.setdefault(group,[0,0])
        maxima[0]=max(maxima[0],bounds[2]-bounds[0]);maxima[1]=max(maxima[1],bounds[3]-bounds[1])
    for row in classes.values():row['family_width'],row['family_height']=families[row['family']]
    (output/'geometry.json').write_text(json.dumps({'version':1,'classes':classes},sort_keys=True,indent=2)+'\n')
    return classes


if __name__=='__main__':
    from .render_all import OUT
    print('Opaque framing metadata:',len(write_metadata(OUT)),'classes')
