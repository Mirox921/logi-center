#!/usr/bin/env python3
"""Isolated G515 DeviceEditor interaction/render check. No device discovery/I/O."""
from pathlib import Path
import argparse,os,sys,tempfile,time
from concurrent.futures import ThreadPoolExecutor

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='/tmp/logi-g515');args=parser.parse_args()
    os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['QT_QPA_PLATFORMTHEME']='generic'
    os.environ['QSG_DISTANCEFIELD_ANTIALIASING']='gray'
    from PySide6.QtCore import QObject,Property,Slot,Signal,QUrl,QPoint,Qt,qInstallMessageHandler
    from PySide6.QtGui import QGuiApplication,QFontDatabase
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtTest import QTest
    from unittest.mock import Mock
    from devices import Device,DeviceManager
    from drafts import DraftStore
    from control_service import g515_controls
    from g515_layout import keys
    from qml_ui.bridge.editor import EditorController
    from i18n import tr,set_language
    errors=[]
    def log(kind,context,message):
        if any(s in message for s in ('ReferenceError','TypeError','Binding loop','Cannot assign','is not defined','Unable to assign')):errors.append(message)
        print(message,file=sys.stderr)
    qInstallMessageHandler(log)
    QQuickStyle.setStyle('Basic');app=QGuiApplication([])
    for path in (ROOT/'qml_ui/assets/fonts').glob('*.ttf'):QFontDatabase.addApplicationFont(str(path))
    class Owner(QObject):
        languageChanged=Signal()
        def __init__(self):
            super().__init__();self._keyboard_online=False;self._preferences_pool=ThreadPoolExecutor(max_workers=1)
            self.refresh=Mock();self.pool=ThreadPoolExecutor(max_workers=1);self.calls=[]
            self.temp=tempfile.TemporaryDirectory()
            self._editor=EditorController(self,self.pool,simulation=True,store=DraftStore(Path(self.temp.name)/'drafts.json'),runner=self.run_fake)
        @Slot(str,result=str)
        def translate(self,text):return tr(text)
        def tr(self,text):return tr(text)
        @Property(QObject,constant=True)
        def editor(self):return self._editor
        @Property(str,constant=True)
        def selectedDeviceId(self):return 'fixture-g515'
        @Property(int,notify=languageChanged)
        def languageToken(self):return 1
        def run_fake(self,args,**kwargs):self.calls.append(args);return ''
    owner=Owner();ed=owner.editor
    device=Device('fixture-g515','Logitech G515 LIGHTSPEED TKL','keyboard','solaar','G515',physical='/simulation/g515',simulated=True)
    manager=DeviceManager();manager.devices=[device];ed.bind(manager,device);owner._keyboard_online=True
    saved={'rgb_zone_1':{'ID':'1','color':'0xffffff','period':'3000','intensity':'100'},'per-key-lighting':{k['id']:'0xffffff' for k in keys()}}
    settings=[{'key':key,'value':value,'choices':choices} for key,value,choices in [
        ('rgb_control','true',['true','false']),('brightness_control','100',None),
        ('rgb_idle_timeout','1 Minute',['Disabled','15 Seconds','30 Seconds','1 Minute','2 Minutes','5 Minutes']),
        ('rgb_sleep_timeout','5 Minutes',['Disabled','2 Minutes','5 Minutes','10 Minutes','15 Minutes','30 Minutes'])]]
    ed._g515=g515_controls(settings,saved,device.id);ed._build()
    engine=QQmlApplicationEngine();engine.addImportPath(str(ROOT/'qml_ui/qml'))
    engine.setInitialProperties({'bridge':owner})
    engine.loadData(b'''import QtQuick
import QtQuick.Controls
import Theme 1.0
ApplicationWindow {
 id: win; required property var bridge
 width: 1280; height: 900; visible: true; color: Theme.background
 function tr(text) { const lang=bridge.languageToken; return bridge.translate(text) }
 DeviceEditor { anchors.fill: parent; anchors.margins: 16; bridge: win.bridge; windowRef: win }
}''',QUrl.fromLocalFile(str(ROOT/'qml_ui/qml/G515Review.qml')))
    assert engine.rootObjects(),'QML editor failed to load'
    window=engine.rootObjects()[0];folder=Path(args.output);folder.mkdir(parents=True,exist_ok=True)
    def visual(item,name):
        if item.objectName()==name:return item
        for child in item.childItems():
            found=visual(child,name)
            if found:return found
    def wait(ms=120):
        deadline=time.monotonic()+ms/1000
        while time.monotonic()<deadline:app.processEvents();time.sleep(.004)
    try:
        for lang,width in [('ru',1280),('en',640)]:
            set_language(lang);owner.languageChanged.emit();window.setWidth(width);window.setHeight(900 if width==1280 else 780)
            for section in ('lighting','freestyle','animations','assignments','keyboard_settings'):
                ed.setSection(section);wait()
                if section=='lighting':ed.edit('g515:effect',10);wait()
                if section=='freestyle':
                    key=visual(window.contentItem(),'g515-key-23');assert key and key.isEnabled()
                    point=key.mapToScene(key.boundingRect().center()).toPoint()
                    QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point);wait(30)
                    assert ed.g515SelectionCount==1
                    key.forceActiveFocus();QTest.keyClick(window,Qt.Key_Space);wait(30)
                    assert ed.g515SelectionCount==1 and owner.calls==[]
                    ed.selectG515Group('wasd');wait(30)
                    swatch=visual(window.contentItem(),'g515-paint-#f3aa32');assert swatch
                    QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,swatch.mapToScene(swatch.boundingRect().center()).toPoint());wait()
                    assert ed.dirtyCount==4 and owner.calls==[]
                    apply=visual(window.contentItem(),'editor-apply');assert apply and apply.isVisible() and apply.isEnabled()
                    for row in ed.g515Keys:
                        assert 0<=row['x'] and row['x']+row['w']<=18.5 and row['y']+row['h']<=6.5
                assert window.grabWindow().save(str(folder/f'{section}-{lang}-{width}.png'))
        assert owner.calls==[],'Navigation or painting sent a command'
        ed.setSection('freestyle');ed.applyGroup()
        deadline=time.monotonic()+3
        while ed.busy and time.monotonic()<deadline:wait(10)
        assert not ed.busy and ed.resultState=='sent_unverified'
        assert len(owner.calls)==6 and all(c[0]=='solaar' for c in owner.calls)
        assert ed.dirtyCount==4,'Unverified drafts were lost'
        assert not errors,errors
        print('PASS: G515 RU/EN 640/1280, key click, four drafts, guarded fake Apply; 10 screenshots; no hardware I/O.')
    finally:
        window.close();ed.shutdown();owner.pool.shutdown(wait=True);owner._preferences_pool.shutdown(wait=True);owner.temp.cleanup()
    return 0


if __name__=='__main__':raise SystemExit(main())
