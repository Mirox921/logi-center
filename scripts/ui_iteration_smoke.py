#!/usr/bin/env python3
"""Reproduce Dashboard toolbar/card QA with isolated DeviceManager fixtures."""
import argparse
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def exercise(app,root,bridge,finished):
    from PySide6.QtCore import QTimer,QPointF,QObject,Qt
    from PySide6.QtTest import QTest
    folder=Path(os.environ['LOGI_CENTER_ITERATION_OUTPUT']);folder.mkdir(parents=True,exist_ok=True)
    phase=os.environ['LOGI_CENTER_ITERATION_STAGE']
    root.setProperty('page','dashboard');root.requestActivate()

    def visual(item,name):
        if item.objectName()==name:return item
        for child in item.childItems():
            match=visual(child,name)
            if match is not None:return match
        return None

    def checked(fn):
        try:fn()
        except BaseException:
            import traceback
            traceback.print_exc()
            from shiboken6 import isValid
            if isValid(root):root.grabWindow().save(str(folder/'failure.png'))
            app.exit(11)

    tasks=[]
    for language in ('ru','en'):
        for width in (640,800,1000,1280,1600,1920):
            tasks.append((language,width))

    def take(index=0):
        if index==len(tasks):keyboard_test();return
        language,width=tasks[index]
        bridge.setLanguage(language);root.resize(width,820)
        def save():
            assert root.width()==width,('Requested width not applied',width,root.width())
            viewport=visual(root.contentItem(),'inventoryScroll')
            assert viewport is not None
            top=viewport.mapToItem(root.contentItem(),QPointF(0,0)).y()
            assert 109<=top<=112,('Toolbar height',top)
            assert root.grabWindow().save(str(folder/f'dashboard-{language}-{width}.png'))
            take(index+1)
        QTimer.singleShot(180,lambda:checked(save))

    def keyboard_test():
        bridge.setLanguage('ru');root.resize(1000,820);bridge.setSearch('')
        QTimer.singleShot(180,lambda:checked(type_search))

    def type_search():
        QTest.keyClick(root,Qt.Key.Key_K,Qt.KeyboardModifier.ControlModifier)
        search=visual(root.contentItem(),'dashboardSearch')
        assert search is not None and search.property('activeFocus')
        assert root.grabWindow().save(str(folder/'search-focus-1000.png'))
        for key in (Qt.Key.Key_M,Qt.Key.Key_C,Qt.Key.Key_H,Qt.Key.Key_O,Qt.Key.Key_S,Qt.Key.Key_E):QTest.keyClick(root,key)
        assert bridge.searchQuery.casefold()=='mchose'
        assert bridge.categoryCounts['all']==2
        assert bridge.devices.count==2
        assert bridge.categoryCounts['mouse']==1 and bridge.categoryCounts['keyboard']==1
        QTest.keyClick(root,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier)
        QTest.keyClick(root,Qt.Key.Key_Z)
        assert bridge.devices.count==0
        QTimer.singleShot(150,lambda:checked(empty_done))

    def empty_done():
        assert root.grabWindow().save(str(folder/'search-empty-1000.png'))
        bridge.setSearch('');bridge.setCategory('mouse')
        assert bridge.devices.count==4
        bridge.setShowBuiltin(False);assert bridge.devices.count==3
        bridge.setCategory('all');bridge.setShowBuiltin(True)
        root.resize(640,820)
        QTimer.singleShot(180,lambda:checked(compact_test))

    def compact_test():
        QTest.keyClick(root,Qt.Key.Key_K,Qt.KeyboardModifier.ControlModifier)
        field=visual(root.contentItem(),'compactDashboardSearch')
        assert field is not None and field.property('activeFocus')
        popup=root.findChild(QObject,'compactSearchPopup')
        assert popup is not None and popup.property('visible')
        assert root.grabWindow().save(str(folder/'search-compact-640.png'))
        QTest.keyClick(root,Qt.Key.Key_Escape)
        assert root.property('page')=='dashboard' and not popup.property('visible')
        bridge.setReducedMotion(True)
        assert bridge.reducedMotion
        bridge.setReducedMotion(False)
        assert not bridge.reducedMotion
        from PySide6.QtCore import QMetaObject,Q_ARG
        QMetaObject.invokeMethod(root,'openTools',Q_ARG('QVariant','settings'))
        QMetaObject.invokeMethod(root,'openTools',Q_ARG('QVariant','backups'))
        QMetaObject.invokeMethod(root,'goBack')
        assert root.property('page')=='dashboard', 'Tools navigation must not trap Back between siblings'
        if phase=='cards':
            check_cards();return
        # Filtering is local; no additional discovery was requested.
        from scripts import ui_iteration_smoke
        assert ui_iteration_smoke.DISCOVERY_CALLS==1,ui_iteration_smoke.DISCOVERY_CALLS
        print('PASS: Dashboard toolbar 110px, six widths/RU/EN, Ctrl+K typing, category counts, built-in filter, compact search/Escape and reduced motion.')
        finished()

    def check_cards():
        root.resize(1000,820)
        QTimer.singleShot(180,lambda:checked(measure_cards))

    def measure_cards():
        import json
        from scripts.card_metrics import measure
        rows=[bridge.devices.get(i) for i in range(bridge.devices.count)]
        output=[];heights=set()
        for data in rows:
            card=visual(root.contentItem(),'device-card-'+data['deviceId'])
            assert card is not None
            metric=measure(card,visual,root.devicePixelRatio())
            assert not metric['clipped'],(data['name'],metric)
            assert metric['scene_height']==240 and metric['scene_width']==320
            tag=visual(card,'connectionText')
            if tag is not None:
                parent=tag.parentItem();x=tag.x();assert x>=6 and x+tag.width()<=parent.width()-6
            battery_item=visual(card,'cardBattery')
            assert battery_item.property('visible')==data['showBattery']
            assert metric['sha256']==data['artworkHash']
            if data['artGeometry']['family']=='mouse':assert .745<=metric['height_fraction']<=.845,(data['name'],metric)
            if data['artGeometry']['family']=='keyboard':assert .835<=metric['width_fraction']<=.865,(data['name'],metric)
            assert metric['minimum_y_margin']>=.079,(data['name'],metric)
            if data['artworkKey'] in ('touchpad','pointer_generic') or data['artGeometry']['family']=='mouse':assert metric['minimum_x_margin']>=.115,(data['name'],metric)
            assert metric['file'].endswith('@2x.png') and metric['source_pixel_scale']<=1,(data['name'],metric)
            heights.add(card.height());output.append(dict(name=data['name'],**metric))
        assert len(heights)==1
        (folder/'card-metrics.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
        duplicate=[data for data in rows if 'G502' in data['name']]
        assert len(duplicate)==2 and len({d['deviceId'] for d in duplicate})==2
        assert {d['sourceLabel'] for d in duplicate}=={'libratbag','Solaar'}
        assert all(d['showSource'] for d in duplicate)
        device=next(d for d in bridge._manager.devices if d.target=='review-mouse')
        card=visual(root.contentItem(),'device-card-'+device.id)
        scene=visual(card,'deviceScene');battery=visual(card,'cardBattery')
        source=visual(card,'deviceArtwork').property('source').toString()
        scene_y=scene.mapToItem(card,QPointF(0,0)).y()
        card.forceActiveFocus()
        viewport=visual(root.contentItem(),'inventoryScroll')
        viewport.setProperty('contentY',250)
        from devices import Device,Capability
        def delta(value,charging):
            observed=Device('battery-delta','Battery','mouse','kernel-battery',physical=device.physical,capabilities=[
                Capability('battery_status','simulation',True,True,value=value,source='simulation'),
                Capability('charging','simulation',True,True,value=charging,source='simulation')])
            bridge._accept_battery(([],[observed],None,None),bridge._battery_epoch.token(),None)
        delta(72,False)
        assert visual(root.contentItem(),'device-card-'+device.id)==card
        assert battery.property('percent')==72 and not battery.property('charging')
        assert visual(card,'deviceArtwork').property('source').toString()==source
        assert card.property('activeFocus') and viewport.property('contentY')==250
        delta(None,True)
        assert battery.property('percent')==-1 and battery.property('charging')
        assert scene.mapToItem(card,QPointF(0,0)).y()==scene_y
        assert not bridge._battery_timer.isActive(), 'Simulation must not schedule real reads'
        viewport.setProperty('contentY',0)
        bridge.setSearch('MCHOSE K7')
        QTimer.singleShot(150,lambda:checked(lambda:unknown_charge(device,delta)))

    def unknown_charge(device,delta):
        assert root.grabWindow().save(str(folder/'battery-unknown-charging.png'))
        from execution import Fault,FaultCode
        device.faults=[Fault(FaultCode.PERMISSION,'simulation','simulated')]
        delta(80,False)
        row=bridge.devices.byId(device.id)
        assert row['batteryPercent']==-1 and row['batteryState']=='denied'
        assert root.grabWindow().save(str(folder/'battery-denied.png'))
        device.faults=[];delta(64,True)
        bridge.setSearch('')
        disconnect(device)

    def disconnect(device):
        from PySide6.QtCore import QMetaObject,Q_ARG
        QMetaObject.invokeMethod(root,'openDevice',Q_ARG('QVariant',device.id))
        manager=bridge._manager;original=list(manager.devices)
        manager.devices=[d for d in original if d.id!=device.id]
        bridge._accept_snapshot({'manager':manager},None)
        assert not bridge.devices.byId(device.id)
        assert bridge.selectedDeviceId==device.id and not bridge.selectedDevice['connected']
        assert bridge.selectedDevice['batteryPercent']==-1 and not bridge.selectedDevice['charging']
        manager.devices=original;bridge._accept_snapshot({'manager':manager},None)
        assert bridge.selectedDeviceId==device.id and bridge.selectedDevice['connected']
        QMetaObject.invokeMethod(root,'goBack')
        from scripts import ui_iteration_smoke
        assert ui_iteration_smoke.DISCOVERY_CALLS==1
        print('PASS: uniform cards/scenes; real PNG bounds/hash; separate G502 provider records; battery delta keeps card/focus/scroll; charging without percent, denied state and reconnect; no real I/O.')
        if os.environ.get('LOGI_CENTER_ITERATION_MATRIX')=='1':matrix_capture()
        else:finished()

    def matrix_capture():
        states=[(language,width,state) for language in ('ru','en') for width in (800,1000,1280,1600,1920) for state in ('hover','hover-touchpad','focus','search-focus','empty','mouse','keyboard','audio','builtin-off','last-row','section-02','section-03')]
        def next_state(index=0):
            if index==len(states):device_pages();return
            language,width,state=states[index]
            bridge.setLanguage(language);root.resize(width,820);root.setProperty('page','dashboard')
            bridge.setCategory('all');bridge.setShowBuiltin(True);bridge.setSearch('')
            viewport=visual(root.contentItem(),'inventoryScroll');viewport.setProperty('contentY',0)
            QTest.mouseMove(root,__import__('PySide6.QtCore',fromlist=['QPoint']).QPoint(0,0))
            if state=='empty':bridge.setSearch('__no_matching_device__')
            elif state=='builtin-off':bridge.setShowBuiltin(False)
            elif state in ('mouse','keyboard','audio'):bridge.setCategory(state)
            def ready():
                if state in ('section-02','section-03'):
                    section=visual(root.contentItem(),'builtinSection' if state=='section-02' else 'audioSection')
                    offset=section.mapToItem(viewport,QPointF(0,0)).y()+viewport.property('contentY')-12
                    viewport.setProperty('contentY',min(max(0,offset),max(0,viewport.property('contentHeight')-viewport.height())))
                if state=='last-row':viewport.setProperty('contentY',max(0,viewport.property('contentHeight')-viewport.height()))
                if state=='search-focus':QTest.keyClick(root,Qt.Key.Key_K,Qt.KeyboardModifier.ControlModifier)
                if state in ('focus','hover','hover-touchpad'):
                    row=next(bridge.devices.get(i) for i in range(bridge.devices.count) if bridge.devices.get(i)['artworkKey']=='touchpad') if state=='hover-touchpad' else bridge.devices.get(0);card=visual(root.contentItem(),'device-card-'+row['deviceId'])
                    if state=='hover-touchpad':
                        offset=card.mapToItem(viewport,QPointF(0,0)).y()+viewport.property('contentY')-12
                        viewport.setProperty('contentY',min(max(0,offset),max(0,viewport.property('contentHeight')-viewport.height())))
                    if state=='focus':card.forceActiveFocus();assert card.property('activeFocus')
                    else:
                        point=card.mapToItem(root.contentItem(),QPointF(card.width()/2,card.height()/2))
                        QTest.mouseMove(root,__import__('PySide6.QtCore',fromlist=['QPoint']).QPoint(round(point.x()),round(point.y())))
                def save():
                    if state=='hover-touchpad':
                        from scripts.card_metrics import measure
                        assert measure(card,visual,root.devicePixelRatio())['minimum_x_margin']>=.119
                    assert root.grabWindow().save(str(folder/f'{state}-{language}-{width}.png'))
                    QTest.keyClick(root,Qt.Key.Key_Escape) if state=='search-focus' and width<960 else None
                    next_state(index+1)
                QTimer.singleShot(160,lambda:checked(save))
            QTimer.singleShot(100,lambda:checked(ready))
        next_state()

    def device_pages():
        tasks=[(language,target,width) for language in ('ru','en') for target in ('review-mouse','review-ace','review-headset') for width in (640,1000)]
        def capture(index=0):
            if index==len(tasks):
                print('PASS: visual matrix RU/EN, five widths, hover/focus/search/empty/categories/built-in/last row and six device details; no writes.')
                finished();return
            language,target,width=tasks[index];bridge.setSearch('');bridge.setCategory('all');bridge.setShowBuiltin(True)
            bridge.setLanguage(language);root.resize(width,820)
            device=next(d for d in bridge._manager.devices if d.target==target)
            from PySide6.QtCore import QMetaObject,Q_ARG
            QMetaObject.invokeMethod(root,'openDevice',Q_ARG('QVariant',device.id))
            def save():
                assert root.grabWindow().save(str(folder/f'device-{target}-{language}-{width}.png'))
                QMetaObject.invokeMethod(root,'goBack');capture(index+1)
            QTimer.singleShot(180,lambda:checked(save))
        capture()

    QTimer.singleShot(150,lambda:checked(take))


DISCOVERY_CALLS=0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=('toolbar','cards'),default='toolbar')
    parser.add_argument('--output',default='docs/screenshots/redesign/header/stage2')
    parser.add_argument('--matrix',action='store_true')
    parser.add_argument('--wayland',action='store_true')
    args=parser.parse_args()
    os.environ['QT_QPA_PLATFORM']='wayland' if args.wayland else 'offscreen'
    os.environ['QT_QPA_PLATFORMTHEME']='generic'
    os.environ['LOGI_CENTER_ITERATION_STAGE']=args.stage
    os.environ['LOGI_CENTER_ITERATION_MATRIX']='1' if args.matrix else '0'
    os.environ['LOGI_CENTER_ITERATION_OUTPUT']=str(Path(args.output).resolve())
    from unittest.mock import patch
    from scripts.illustration_dashboard import fixture_snapshot
    # __main__ and imported hooks must share a single counter.
    from scripts import ui_iteration_smoke
    def snapshot(*a,**k):
        ui_iteration_smoke.DISCOVERY_CALLS+=1
        return fixture_snapshot(*a,**k)
    from qml_ui.main import run
    with patch('backend.run',side_effect=AssertionError('Real CLI forbidden in UI smoke')),patch('device_service.collect_device_snapshot',side_effect=snapshot):
        return run(['ui-iteration-smoke','--simulate','--smoke'])


if __name__=='__main__':raise SystemExit(main())
