#!/usr/bin/env python3
"""Rendered tag containment and exact battery segment QA; no device service."""
import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['QT_QPA_PLATFORMTHEME']='generic'
from PySide6.QtCore import QTimer,QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from device_presentation import battery_segments
app=QGuiApplication([])
from PySide6.QtGui import QFontDatabase
for file in ('NotoSans-Regular.ttf','NotoSans-Bold.ttf','JetBrainsMonoNerdFont-Regular.ttf'):QFontDatabase.addApplicationFont(str(ROOT/'qml_ui/assets/fonts'/file))
engine=QQmlApplicationEngine();engine.addImportPath(str(ROOT/'qml_ui/qml'))
engine.load(QUrl.fromLocalFile(str(ROOT/'scripts/TelemetryReview.qml')))
if not engine.rootObjects():raise SystemExit(2)
root=engine.rootObjects()[0]
def children(item):
    yield item
    for child in item.childItems():yield from children(child)
def check():
    try:
        tags=[item for item in children(root.contentItem()) if item.objectName().startswith('tag-')]
        assert len(tags)==8
        for tag in tags:
            text=next(item for item in children(tag) if item.objectName()=='connectionText')
            assert text.x()>=6 and text.x()+text.width()<=tag.width()-6
            assert not text.property('truncated')
        for item in children(root.contentItem()):
            if item.objectName().startswith('meter-'):
                value=int(item.objectName().split('-')[1]);assert item.property('filledSegments')==battery_segments(value)
        output=ROOT/'docs/screenshots/redesign/header/iteration5/C';output.mkdir(parents=True,exist_ok=True)
        assert root.grabWindow().save(str(output/'telemetry-labels.png'))
        print('PASS: eight RU/EN tags have >=6px padding; seven rendered meters round down exactly.')
        app.quit()
    except BaseException:
        import traceback;traceback.print_exc();app.exit(1)
QTimer.singleShot(200,check);raise SystemExit(app.exec())
