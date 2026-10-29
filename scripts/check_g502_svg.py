#!/usr/bin/env python3
"""Compare Qt SVG output with offline librsvg reference renders; no hardware I/O."""
from pathlib import Path
import sys
from PySide6.QtCore import QRectF
from PySide6.QtGui import QGuiApplication,QImage,QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT=Path(__file__).resolve().parents[1]


def pixels(image):
    converted=image.convertToFormat(QImage.Format.Format_RGBA8888)
    return bytes(converted.constBits()),converted.bytesPerLine()


def check(kind,output):
    assets=ROOT/'qml_ui/assets/devices/exact'
    renderer=QSvgRenderer(str(assets/f'g502-top-{kind}-qt.svg'))
    assert renderer.isValid()
    image=QImage(410,760,QImage.Format.Format_ARGB32);image.fill(0)
    painter=QPainter(image);renderer.render(painter,QRectF(0,0,410,760));painter.end()
    reference=QImage(str(ROOT/f'tests/fixtures/artwork/g502/reference-{kind}.png'))
    assert not reference.isNull() and reference.size()==image.size()
    actual,stride=pixels(image);expected,ref_stride=pixels(reference)
    outside=missing=0
    # Permit one pixel of antialiasing at contours/the SVG viewport edge.
    for y in range(1,759):
        for x in range(1,409):
            if actual[y*stride+x*4+3]>32 and not any(expected[(y+dy)*ref_stride+(x+dx)*4+3]>32 for dy in (-1,0,1) for dx in (-1,0,1)):
                outside+=1
            if expected[y*ref_stride+x*4+3]>32 and not any(actual[(y+dy)*stride+(x+dx)*4+3]>32 for dy in (-1,0,1) for dx in (-1,0,1)):
                missing+=1
    assert outside<=8 and missing<=8,(kind,outside,missing)
    assert image.pixelColor(50,50).alpha()==0,'Transparent area became a panel'
    for x,y in ((140,220),(125,300)):
        measured=image.pixelColor(x,y);wanted=reference.pixelColor(x,y)
        assert max(abs(measured.red()-wanted.red()),abs(measured.green()-wanted.green()),abs(measured.blue()-wanted.blue()))<=3,'Gradient became black'
    cyan=sum(actual[i]<80 and actual[i+1]>150 and actual[i+2]>150 and actual[i+3]>200 for i in range(0,len(actual),4))
    assert cyan>1500,'LC mark or coloured indicators disappeared in masked group'
    image.save(str(output/f'qt-{kind}.png'))
    print(f'PASS: {kind}: transparent contour, gradients and coloured details; outside={outside}, missing={missing}')


if __name__=='__main__':
    app=QGuiApplication([])
    output=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/logi-g502-svg-check');output.mkdir(parents=True,exist_ok=True)
    for kind in ('wired','wireless'):check(kind,output)
