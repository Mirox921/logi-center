"""Developer-only opaque PNG bounds projected through the actual QML Image."""
import hashlib
from pathlib import Path

_CACHE={}


def measure(card,visual,dpr=1):
    from PySide6.QtGui import QImage
    art=visual(card,'deviceArtwork');scene=visual(card,'deviceScene')
    assert art is not None and scene is not None
    source=Path(art.property('source').toLocalFile())
    key=(str(source),source.stat().st_mtime_ns)
    if key not in _CACHE:
        png=QImage(str(source)).convertToFormat(QImage.Format.Format_RGBA8888)
        assert not png.isNull()
        l,t,r,b=png.width(),png.height(),-1,-1
        sl,st,sr,sb=png.width(),png.height(),-1,-1
        for y in range(png.height()):
            line=png.constScanLine(y)
            for x in range(png.width()):
                if line[x*4+3]>=1:sl,st,sr,sb=min(sl,x),min(st,y),max(sr,x),max(sb,y)
                if line[x*4+3]>=245:l,t,r,b=min(l,x),min(t,y),max(r,x),max(b,y)
        _CACHE[key]=(l,t,r+1,b+1,png.width(),png.height(),hashlib.sha256(source.read_bytes()).hexdigest(),(sl,st,sr+1,sb+1))
    l,t,r,b,w,h,digest,outer=_CACHE[key]
    pw,ph=art.property('paintedWidth'),art.property('paintedHeight')
    x=art.x()+(art.width()-pw)/2;y=art.y()+(art.height()-ph)/2
    bounds=[x+l/w*pw,y+t/h*ph,x+r/w*pw,y+b/h*ph]
    sl,st,sr,sb=outer
    projected=[x+sl/w*pw,y+st/h*ph,x+sr/w*pw,y+sb/h*ph]
    minimum_x=min(projected[0],scene.width()-projected[2])/scene.width()
    minimum_y=min(projected[1],scene.height()-projected[3])/scene.height()
    clipped=bounds[0]<-.6 or bounds[1]<-.6 or bounds[2]>scene.width()+.6 or bounds[3]>scene.height()+.6
    return {'file':source.name,'sha256':digest,'bounds':bounds,'clipped':clipped,
            'height_fraction':(bounds[3]-bounds[1])/scene.height(),
            'width_fraction':(bounds[2]-bounds[0])/scene.width(),
            'outer_bounds':projected,'minimum_x_margin':minimum_x,'minimum_y_margin':minimum_y,'source_pixel_scale':pw/w*dpr,
            'scene_height':scene.height(),'scene_width':scene.width(),'card_height':card.height()}
