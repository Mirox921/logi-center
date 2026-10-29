#!/usr/bin/env python3
"""S9 Dashboard/editor/macro/scale checks over in-memory HID pages only."""
# Allow direct execution without installing developer tools.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import scripts  # source-package bootstrap
from pathlib import Path
import os,sys,time,json


def exercise(app,root,bridge,finish):
    from PySide6.QtCore import QTimer,QObject,Qt,QPointF
    from PySide6.QtTest import QTest
    from unittest.mock import patch
    from tests.unit.test_eweadn import Wire,ITEM,TARGET
    from logi_center.adapters.eweadn.eweadn_adapter import hardware,capabilities
    from logi_center.core.devices.devices import Device,DeviceManager
    wire=Wire();writes=[]
    name_patch=patch.dict('logi_center.core.devices.device_presentation.SIMULATION_NAMES',{TARGET:'EWEADN S9 Ultra · SIM'});name_patch.start()
    device=Device('fixture-s9','EWEADN S9 Ultra','mouse','eweadn',TARGET,physical=ITEM['physical'],vid='372e',pid='1026',connection='wireless',simulated=True)
    device.capabilities=capabilities(TARGET,wire.state())
    manager=DeviceManager();manager.devices=[device]
    def runner(args,**kwargs):
        assert args[:2]==['logi-sdk','eweadn'],args
        with patch('logi_center.adapters.eweadn.eweadn_adapter.candidates',return_value=[ITEM]),patch('logi_center.adapters.eweadn.eweadn_adapter.time.sleep'),patch('logi_center.core.services.drafts.atomic_json'):
            if args[2]=='set':writes.append(args)
            return json.dumps(hardware(args[2],args[3],args[4] if len(args)>4 else None,json.loads(args[5]) if len(args)>5 else None,transport=lambda _:wire))
    bridge.editor.runner=runner
    bridge.refresh=lambda:bridge._accept_snapshot({'manager':manager},None)
    bridge.refresh();bridge.setCategory('all');bridge.setSearch('');assert bridge.devices.count==1
    forbidden=patch('logi_center.adapters.external.backend.run',side_effect=AssertionError('Unexpected real backend I/O in S9 smoke'));forbidden.start()
    folder=Path(os.environ['LOGI_CENTER_QML_SCREENSHOT_DIR']);folder.mkdir(parents=True,exist_ok=True)
    end=time.monotonic()+45
    def visual(item,name):
        if item.objectName()==name:return item
        for child in item.childItems():
            found=visual(child,name)
            if found:return found
    def checked(callback):
        try:callback()
        except BaseException:
            import traceback
            traceback.print_exc();root.grabWindow().save(str(folder/'failure.png'));forbidden.stop();app.exit(12)
    def wait(callback):
        if time.monotonic()>end:raise AssertionError('S9 smoke timed out')
        if bridge.editor.busy:QTimer.singleShot(10,lambda:checked(lambda:wait(callback)))
        else:callback()
    def initial():
        bridge.selectDevice(device.id);root.setProperty('page','device')
        QTimer.singleShot(10,lambda:checked(lambda:wait(exercise_fields)))
    def exercise_fields():
        ed=bridge.editor
        assert ed.eweadnState['model_id']=='s9ultra' and writes==[]
        assert bridge.selectedDevice['artworkSource']=='exact-model',bridge.selectedDevice
        ed.setSection('pointer');ed.edit('eweadn:dpi_config:x1',1200)
        assert ed.dirtyCount==2 and writes==[]
        ed.discardGroup();assert ed.dirtyCount==0
        ed.setSection('advanced');ed.edit('eweadn:sensor_config:debounce',7);ed.applyGroup()
        QTimer.singleShot(10,lambda:checked(lambda:wait(after_apply)))
    def after_apply():
        assert len(writes)==1 and bridge.editor.resultState=='confirmed'
        assert wire.pages[64][4]==7
        device.connected=False;bridge.editor.bind(manager,device)
        assert not bridge.editor.available
        device.connected=True;bridge.editor.bind(manager,device)
        QTimer.singleShot(10,lambda:checked(lambda:wait(capture_next)))
    hidpi=float(os.environ.get('QT_SCALE_FACTOR','1'))>1
    cases=[('ru',1280,800),('en',640,780)]
    pages=['dashboard','buttons'] if hidpi else ['dashboard','buttons','pointer','performance','advanced','other','macros','settings']
    shots=[(lang,width,height,page) for lang,width,height in cases for page in pages]
    counter=[0]
    def capture_next():
        if counter[0]>=len(shots):return capture_macro()
        lang,width,height,page=shots[counter[0]];counter[0]+=1
        bridge.setLanguage(lang);root.setWidth(width);root.setHeight(height)
        if page=='dashboard':root.setProperty('page','dashboard')
        elif page=='settings':
            root.setProperty('page','settings');bridge.setUiScale(150)
            assert bridge.uiScale==150 and bridge.scaleRestartRequired
        else:root.setProperty('page','device');bridge.editor.setSection(page)
        def save():
            assert root.grabWindow().save(str(folder/f'{page}-{lang}-{width}.png'))
            if page=='buttons':
                image=visual(root.contentItem(),'eweadn-button-artwork');assert image is not None and image.property('progress')==1 and image.property('paintedHeight')>0
                for index in range(5):
                    hit=visual(root.contentItem(),'eweadn-button-hit-'+str(index));assert hit and hit.isVisible()
                    point=hit.mapToItem(root.contentItem(),QPointF(hit.width()/2,hit.height()/2)).toPoint()
                    before=len(writes);QTest.mouseMove(root,point);assert len(writes)==before
                    QTest.mouseClick(root,Qt.LeftButton,Qt.NoModifier,point)
                    assert bridge.editor.selectedButton==index and len(writes)==before
            QTimer.singleShot(10,lambda:checked(capture_next))
        QTimer.singleShot(180,lambda:checked(save))
    def capture_macro():
        if hidpi:return done()
        root.setWidth(1280);root.setHeight(800);root.setProperty('page','device');bridge.editor.setSection('macros')
        panel=root.findChild(QObject,'eweadn-panel');window=panel.findChild(QObject,'macro-recorder-window')
        assert window is not None
        window.setProperty('visible',True);window.requestActivate()
        bridge.editor.createLibraryMacro('S9 recording');bridge.editor.setLibraryRepeatMode('held')
        QTimer.singleShot(150,lambda:checked(lambda:record(window)))
    def record(window):
        capture=visual(window.contentItem(),'macro-capture-area');assert capture
        bridge.editor.setCapturePauses(False);bridge.editor.beginMacroCapture(window,capture);capture.forceActiveFocus()
        QTest.keyClick(window,Qt.Key_A);QTest.keyClick(window,Qt.Key_Space)
        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,capture.mapToItem(window.contentItem(),QPointF(30,30)).toPoint())
        bridge.editor.stopRecording()
        events=bridge.editor._macro.tokens
        assert len(events)>=6,events
        assert len(writes)==1 and bridge.editor.libraryRepeatMode=='held'
        assert window.grabWindow().save(str(folder/'macro-recorder.png'))
        window.close();done()
    def done():
        bridge.setUiScale(100);assert not bridge.scaleRestartRequired
        forbidden.stop();name_patch.stop();print('PASS: S9 native fake Apply/readback, five hitboxes, drafts/reconnect, macro capture and UI scale; RU/EN 640/1280, no hardware I/O.')
        finish()
    QTimer.singleShot(10,lambda:checked(initial))


if __name__=='__main__':
    import argparse,subprocess
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='/tmp/logi-s9-review');parser.add_argument('--hidpi',action='store_true');args=parser.parse_args()
    env=dict(os.environ,QT_QPA_PLATFORM='offscreen',QT_QPA_PLATFORMTHEME='generic',LOGI_CENTER_QML_EWEADN_SMOKE='1',LOGI_CENTER_QML_SCREENSHOT_DIR=str(Path(args.output).resolve()))
    if args.hidpi:env['QT_SCALE_FACTOR']='2';env['QT_IMAGEIO_MAXALLOC']='32'
    raise SystemExit(subprocess.call([sys.executable,str(Path(__file__).resolve().parents[1]/'app.py'),'--ui','qml','--simulate','--smoke'],env=env,cwd=Path(__file__).resolve().parents[1]))
