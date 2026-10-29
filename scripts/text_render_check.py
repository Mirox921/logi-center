#!/usr/bin/env python3
"""Hardware-free text comparison; PNGs retain physical pixels, crops use nearest neighbour."""
# Allow direct execution without installing developer tools.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import scripts  # source-package bootstrap
import argparse, os, sys, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--wayland',action='store_true');p.add_argument('--aa',choices=('gray','subpixel','default'),default='gray');p.add_argument('--first-style',type=int,choices=(0,1,2),default=0);a=p.parse_args()
if a.aa != 'default':os.environ['QSG_DISTANCEFIELD_ANTIALIASING']=a.aa
os.environ['QT_QPA_PLATFORM']='wayland' if a.wayland else 'offscreen'
os.environ['QT_QPA_PLATFORMTHEME']='generic'
from PySide6.QtCore import QTimer,QUrl,Qt
from PySide6.QtGui import QGuiApplication,QFontDatabase
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
app=QGuiApplication([])
for f in ('NotoSans-Regular.ttf','NotoSans-Bold.ttf','JetBrainsMonoNerdFont-Regular.ttf'):
    QFontDatabase.addApplicationFont(str(ROOT/'assets/fonts'/f))
from logi_center.resources import configure_engine
engine=QQmlApplicationEngine();configure_engine(engine);engine.addImportPath(str(ROOT/'src/logi_center/qml_ui/qml'))
# Each column is independently rendered, not an enlarged screenshot of another mode.
qml='import QtQuick\nimport Theme 1.0\nimport "../src/logi_center/qml_ui/qml"\nWindow { width: 1000; height: 660; visible: true; color: Theme.background\nRow { x: 16; y: 16; spacing: 20\nRepeater { model: 3\nColumn { required property int index; spacing: 12; width: 310\nText { text: ["Qt / No hint", "Qt / Vertical hint", "Native / Vertical hint"][parent.index]; color: Theme.text; font.pixelSize: 14 }\nRepeater { model: ["USB", "Нет данных", "libratbag →", "15 настроек", "Игровая мышь", "46%", "Logitech G502 HERO", "Мыши / Клавиатуры", "4 внешних · 2 встроенных", "No data", "15 settings", "Gaming mouse", "Mice / Keyboards", "4 external · 2 built-in"]\nText { required property string modelData; text: modelData; color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 13; height: 26\nrenderType: parent.index === 2 ? Text.NativeRendering : Text.QtRendering\nfont.hintingPreference: parent.index === 0 ? Font.PreferNoHinting : Font.PreferVerticalHinting\n}\n}\n}\n}\n}\nConnectionTag { x: 20; y: 580; label: "USB" }\nSegmentedBattery { x: 150; y: 580; width: 320; percent: -1; label: "Нет данных / No data" }\n}'
qml=qml.replace('parent.index',f'((parent.index+{a.first_style})%3)')
engine.loadData(qml.encode(),QUrl.fromLocalFile(str(ROOT/'scripts/TextReview.qml')))
if not engine.rootObjects():raise SystemExit(2)
root=engine.rootObjects()[0]
out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
def capture():
    image=root.grabWindow()
    assert not image.isNull() and image.save(str(out/'text-1x.png'))
    image.scaled(image.width()*4,image.height()*4,Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.FastTransformation).save(str(out/'text-4x.png'))
    d=root.devicePixelRatio()
    left=image.copy(int(16*d),int(60*d),min(int(310*d),image.width()-int(16*d)),min(int(500*d),image.height()-int(60*d)))
    left.scaled(left.width()*4,left.height()*4,Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.FastTransformation).save(str(out/'labels-4x.png'))
    crop=image.copy(0,int(560*d),int(500*d),int(95*d))
    crop.scaled(crop.width()*4,crop.height()*4,Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.FastTransformation).save(str(out/'components-4x.png'))
    pixels=fringed=0
    for y in range(int(65*d),min(int(560*d),image.height())):
        for x in range(int(16*d),min(int(326*d),image.width())):
            color=image.pixelColor(x,y)
            coverage=((color.red()-23)/172,(color.green()-23)/165,(color.blue()-19)/154)
            if .08 < sum(coverage)/3 < .92:
                pixels+=1
                fringed+=max(coverage)-min(coverage)>.11
    metrics={'platform':app.platformName(),'dpr':d,'scale':os.getenv('QT_SCALE_FACTOR'),'rounding':app.highDpiScaleFactorRoundingPolicy().name,'graphics':root.rendererInterface().graphicsApi().name,'antialiasing':os.environ.get('QSG_DISTANCEFIELD_ANTIALIASING','default'),'first_style':a.first_style,'edge_pixels':pixels,'chromatic_edge_pixels':fringed}
    (out/'environment.json').write_text(json.dumps(metrics,indent=2))
    print('PASS: text comparison captured',out,'DPR',d);app.quit()
QTimer.singleShot(500,capture);sys.exit(app.exec())
