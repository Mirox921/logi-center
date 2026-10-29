#!/usr/bin/env python3
"""Qt vs librsvg check for the supplied S9 vector; offline, no device access."""
from pathlib import Path
import os,sys,subprocess,tempfile
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['QT_QPA_PLATFORMTHEME']='generic'
from PySide6.QtGui import QGuiApplication,QImage,QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QRectF
root=Path(__file__).resolve().parents[1];folder=root/'qml_ui/assets/devices/exact'
app=QGuiApplication([])
with tempfile.TemporaryDirectory() as tmp:
    source=Path(tmp)/'reference.png'
    subprocess.run(['rsvg-convert','-w','350','-h','679',str(folder/'eweadn-s9-original.svg'),'-o',str(source)],check=True)
    reference=QImage(str(source)).convertToFormat(QImage.Format.Format_RGBA8888)
    result=QImage(350,679,QImage.Format.Format_ARGB32);result.fill(0)
    renderer=QSvgRenderer(str(folder/'eweadn-s9.svg'));assert renderer.isValid()
    painter=QPainter(result);renderer.render(painter,QRectF(0,0,350,679));painter.end()
    actual=result.convertToFormat(QImage.Format.Format_RGBA8888)
    a=bytes(actual.constBits());b=bytes(reference.constBits())
    different=sum(max(abs(a[i+j]-b[i+j]) for j in range(4))>32 for i in range(0,len(a),4))
    assert different<350*679*.012,different
    assert actual.pixelColor(0,0).alpha()==0 and actual.pixelColor(349,678).alpha()==0
    color=actual.pixelColor(180,420);assert color.red()>color.green()*2 and color.alpha()>240
    print('PASS: Qt SVG preserves source silhouette/material; significant different pixels:',different,'of',350*679)
