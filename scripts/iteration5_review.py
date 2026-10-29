#!/usr/bin/env python3
"""Developer-only brand/contrast review sheets; no device I/O."""
from pathlib import Path
import argparse,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def logos():
    from PySide6.QtGui import QGuiApplication,QImage,QPainter,QColor,QFont
    from PySide6.QtCore import QRectF
    from PySide6.QtSvg import QSvgRenderer
    app=QGuiApplication.instance() or QGuiApplication([])
    root=ROOT/'docs/screenshots/redesign/header/iteration5'
    image=QImage(960,360,QImage.Format.Format_ARGB32_Premultiplied);p=QPainter(image)
    p.setFont(QFont('monospace',10))
    for row,(bg,fg) in enumerate((('#171713','#f4f0e7'),('#f4f0e7','#211f1a'))):
        p.fillRect(0,row*180,960,180,QColor(bg));p.setPen(QColor(fg))
        for variant,key in enumerate(('lc','mouse','key')):
            renderer=QSvgRenderer(str(root/'logo-variants'/f'{key}.svg'))
            for col,size in enumerate((16,24,32,40)):
                x=variant*320+20+col*73;renderer.render(p,QRectF(x,row*180+30,size,size))
                p.drawText(x,row*180+110,f'{size}px')
            p.drawText(variant*320+20,row*180+150,key.upper())
    p.end();image.save(str(root/'logo-candidates.png'))


def accent(source,output):
    import cairo,colorsys,json
    output.mkdir(parents=True,exist_ok=True);measurements=[]
    for path in sorted(source.glob('dashboard-*.png')):
        if not any(path.name.endswith(f'-{w}.png') for w in (1000,1280,1600,1920)):continue
        image=cairo.ImageSurface.create_from_png(str(path));image.flush()
        w,h=image.get_width(),image.get_height();data=bytes(image.get_data());stride=image.get_stride()
        grey=cairo.ImageSurface(cairo.FORMAT_ARGB32,w,h);mask=cairo.ImageSurface(cairo.FORMAT_ARGB32,w,h)
        g,m=grey.get_data(),mask.get_data();count=0
        for y in range(h):
            for x in range(w):
                i=y*stride+x*4
                b,green,r,a=data[i:i+4] if sys.byteorder=='little' else (data[i+3],data[i+2],data[i+1],data[i])
                hue,saturation,value=colorsys.rgb_to_hsv(r/255,green/255,b/255)
                amber=18<=hue*360<=52 and saturation>=.4 and value>=.25
                count+=amber;level=round(.2126*r+.7152*green+.0722*b);v=255 if amber else 0
                g[i:i+4]=bytes((level,level,level,255));m[i:i+4]=bytes((v,v,v,255))
        grey.mark_dirty();mask.mark_dirty();grey.write_to_png(str(output/(path.stem+'-grey.png')));mask.write_to_png(str(output/(path.stem+'-amber.png')))
        percent=100*count/(w*h);measurements.append({'image':path.name,'amber_percent':round(percent,4),'pixels':count,'total':w*h})
        print(path.name,f'{percent:.3f}% amber')
        if percent>5:raise RuntimeError('Accent budget exceeds5%')
    (output/'accent-metrics.json').write_text(json.dumps(measurements,indent=2)+'\n')


def art_crops(source,output):
    import cairo
    from illustrations.checks import Pixels
    keys=('mouse','mouse_gaming','mouse_wireless','mouse_compact','touchpad','pointer_generic')
    output.mkdir(parents=True,exist_ok=True)
    for key in keys:
        for density in (1,2):
            path=source/(key.replace('_','-')+f'@{density}x.png')
            if not path.is_file():continue
            png=cairo.ImageSurface.create_from_png(str(path));l,t,r,b=Pixels(png).bounds(1)
            l=max(0,l-6*density);t=max(0,t-6*density);r=min(png.get_width(),r+6*density);b=min(png.get_height(),b+6*density)
            scale=4/density;w=round((r-l)*scale);h=round((b-t)*scale)
            for name,background in (('dark',(0,0,0)),('light',(1,1,1))):
                sheet=cairo.ImageSurface(cairo.FORMAT_ARGB32,w,h);ctx=cairo.Context(sheet);ctx.set_source_rgb(*background);ctx.paint()
                ctx.scale(scale,scale);ctx.set_source_surface(png,-l,-t);ctx.get_source().set_filter(cairo.FILTER_NEAREST);ctx.paint()
                sheet.write_to_png(str(output/(key.replace('_','-')+f'-{name}@{density}x-crop4.png')))
    print('PASS: 4x crops, both densities/backgrounds:',output)


def comparison(before,after,output):
    import cairo
    from illustrations.checks import Pixels
    keys=('mouse','mouse_gaming','mouse_wireless','mouse_compact','touchpad','pointer_generic')
    output.mkdir(parents=True,exist_ok=True)
    for name,bg,fg in (('dark',(0,0,0),(.9,.9,.9)),('light',(1,1,1),(.1,.1,.1))):
        sheet=cairo.ImageSurface(cairo.FORMAT_ARGB32,1024,len(keys)*360);p=cairo.Context(sheet);p.set_source_rgb(*bg);p.paint()
        for row,key in enumerate(keys):
            stem=key.replace('_','-');old=before/(stem+'@2x.png')
            if not old.exists() and key=='pointer_generic':old=before/'mouse-builtin@2x.png'
            new=after/(stem+'@2x.png')
            images=[cairo.ImageSurface.create_from_png(str(path)) for path in (old,new)]
            for column,image in enumerate(images):
                p.save();p.translate(column*512,row*360+28);p.scale(.5,.5);p.set_source_surface(image);p.paint();p.restore()
                p.set_source_rgb(*fg);p.select_font_face('monospace');p.set_font_size(14);p.move_to(column*512+16,row*360+22);p.show_text(key+' / '+('ITERATION4' if column==0 else 'REFINED'))
            boxes=[Pixels(i).bounds(1) for i in images];l=min(b[0] for b in boxes);t=min(b[1] for b in boxes);r=max(b[2] for b in boxes)+1;b=max(b[3] for b in boxes)+1
            w,h=(r-l+12)*2,(b-t+12)*2
            pair=cairo.ImageSurface(cairo.FORMAT_ARGB32,w*2,h);ctx=cairo.Context(pair);ctx.set_source_rgb(*bg);ctx.paint()
            for col,image in enumerate(images):
                ctx.save();ctx.rectangle(col*w,0,w,h);ctx.clip();ctx.translate(col*w,0);ctx.scale(2,2);ctx.set_source_surface(image,-l+6,-t+6);ctx.get_source().set_filter(cairo.FILTER_NEAREST);ctx.paint();ctx.restore()
            pair.write_to_png(str(output/(stem+'-'+name+'-before-after4.png')))
        sheet.write_to_png(str(output/('before-after-'+name+'.png')))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--logos',action='store_true');parser.add_argument('--accent',type=Path);parser.add_argument('--crops',type=Path);parser.add_argument('--compare-source',type=Path);parser.add_argument('--output',type=Path,default=ROOT/'docs/screenshots/redesign/header/iteration5/accent');args=parser.parse_args()
    if args.logos:logos()
    if args.accent:accent(args.accent,args.output)
    if args.crops:art_crops(args.crops,args.output)
    if args.compare_source and args.crops:comparison(args.compare_source,args.crops,args.output)
