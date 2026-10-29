#!/usr/bin/env python3
"""Functional QML migration exercise; writes go only to in-memory transports."""
from pathlib import Path
import copy,json,os,sys,time


def exercise(app,root,bridge,finish):
    from PySide6.QtCore import QTimer,Qt,QPoint,QPointF,QObject
    from PySide6.QtTest import QTest
    from unittest.mock import patch
    from devices import Device,Capability,DeviceManager
    from operations import Plan,Observation
    from execution import Fault,FaultCode
    from ace68_adapter import setting_plan
    from ace68_protocol import KEY_INDICES,KEY_FIELDS,MODES,state as read_ace_state
    from test_ace68_advanced import AdvancedWire
    from test_ace68 import ITEM
    from ace68_adapter import hardware,selector
    from qml_ui.bridge.audio_simulation import AudioSimulation
    audio=AudioSimulation();writes=[]
    stabilization=os.environ.get('LOGI_CENTER_EDITOR_STABILIZATION')=='1'
    button_count=11 if stabilization else 6
    ratbag={'active':0,'text':'Model: usb:046d:c08b:0' if stabilization else '',
        'dpis':[400,800,1600,3200],'rates':[500,1000],
        'button_types':{i:[0,1,2,3,4] for i in range(button_count)},'led_modes':{0:['on','off','breathing','cycle']},
        'profiles':[{'index':0,'active':True,'rate':1000,'resolutions':[{'index':0,'dpi':800,'active':True,'disabled':False},{'index':1,'dpi':1600,'active':False,'disabled':False}],
          'buttons':[{'index':i,'action':'button '+str(min(i+1,5)),'macro':False} for i in range(button_count)],'leds':[{'index':0,'depth':'rgb','mode':'on','color':'f3aa32','duration':0,'brightness':0}]},
         {'index':1,'active':False,'rate':500,'resolutions':[],'buttons':[],'leds':[]}]}
    ace_wire=AdvancedWire()
    for key in KEY_INDICES:ace_wire.tables[160][key*8+2]=29
    state=read_ace_state(ace_wire)
    mouse=Device('sim:migration-mouse','Logitech G502 HERO · SIM' if stabilization else 'Mouse · SIM','mouse','ratbagctl','sim-editor',physical='/simulation/mouse',
                 vid='046d' if stabilization else '',pid='c08b' if stabilization else '',connection='usb',simulated=True)
    if stabilization:
        mouse.capabilities += [
            Capability('debounce','fixture',True,True,True,True,4,'simulation',minimum=0,maximum=20,step=1,plan=lambda value:Plan(['fixture-only'],value)),
            Capability('motion_sync','fixture',True,True,False,False,True,'simulation')]
    keyboard=Device('sim:migration-keyboard','MCHOSE Ace68-II · SIM','keyboard','mchose-ace68','sim-ace',physical='/simulation/keyboard',vid='41e4',pid='2116',connection='usb',simulated=True)
    for field in ('firmware_version','profiles','polling_rate','brightness','lighting_mode','lighting_speed','lighting_palette','lighting_direction','lighting','win_lock','stability_mode','key_debounce','adaptive_calibration','keyboard_mode','key_details',*KEY_FIELDS):
        value=state[field]
        cap=Capability(field,'mchose-ace68',True,True,field not in ('key_details','firmware_version'),True,copy.deepcopy(value),'simulation',
            choices=state['profile_choices'] if field=='profiles' else [1000,2000,4000,8000] if field=='polling_rate' else list(MODES.values()) if field=='lighting_mode' else ['Single color','Random colors'] if field=='lighting_palette' else [0,1] if field=='lighting_direction' else ['Windows','Mac'] if field=='keyboard_mode' else [],
            minimum=0 if field in ('brightness','lighting_speed') else None,maximum=100 if field=='brightness' else 4 if field=='lighting_speed' else None,
            plan=lambda value,f=field:setting_plan('sim-ace',f,value,state['profiles']))
        keyboard.capabilities.append(cap)
    for field in ('socd','dks','mod_tap','key_remap','macros'):
        keyboard.capabilities.append(Capability(field,'mchose-ace68',None,limitation='Not implemented in the existing backend'))
    headset=Device('sim:migration-headset','Logitech G PRO X · SIM','audio','pactl','simulation-output',physical='/simulation/audio',connection='usb',simulated=True)
    plain=Device('sim:migration-plain','Basic mouse · SIM','mouse','linux-input',physical='/simulation/basic',connection='usb',simulated=True)
    k7=Device('sim:migration-k7','RealTek MCHOSE K7 Ultra','mouse','mchose','sim-k7',physical='/simulation/k7',
              vid='3837',pid='1001',connection='wireless',simulated=True) if stabilization else None
    if k7:
        from mchose_adapter import dock_capability,dock_values,k7_capabilities,setting_plan as mouse_setting_plan
        from test_k7_settings import NativeTransport
        native=NativeTransport()
        native.raw[0]=0
        dock_record=bytes([1,1,0,100,0,3,1,0,0,255,0,0,255,0,0])
        k7.capabilities=[Capability(name,'mchose',True,True,False,False,value,'device') for name,value in
                         [('profiles',0),('charging',False),('battery_status',52),
                          ('motion_sync',False),('ripple',False),('angle_snap',False)]]
        k7.capabilities.append(Capability('stage','mchose',True,True,True,True,0,'device',
            choices=list(range(6)),plan=lambda value:Plan(['fixture-only'],value)))
        k7.capabilities.append(dock_capability('sim-k7',{'dock_lighting':dock_values(dock_record),'dock_rgb_record':list(dock_record)}))
        k7.capabilities.extend(k7_capabilities('sim-k7',native.read()))
        for name,low,high in [('sleep',0,255),('debounce',0,20),('polling_rate',None,None)]:
            cap=Capability(name,'mchose',True,True,True,True,native.read()[name],'device',
                choices=[125,500,1000,2000,4000,8000] if name=='polling_rate' else [],minimum=low,maximum=high)
            cap.plan=lambda value,n=name:mouse_setting_plan('sim-k7',n,value,0)
            k7.capabilities.append(cap)
    manager=DeviceManager();manager.devices=[mouse,keyboard,headset,plain,*([k7] if k7 else [])]
    def snapshot():return {'manager':manager,**audio.snapshot()}
    def runner(args,**unused):
        nonlocal dock_record
        if args[0]=='pactl':return audio.run(args)
        if args[:2]==['logi-sdk','mchose'] and k7:
            from mchose_adapter import dock_values,prepare_dock_record
            if args[2]=='set':
                changes=json.loads(args[-1])['changes']
                if args[4]=='dock_lighting':dock_record=prepare_dock_record(dock_record,changes)
                else:
                    from k7_settings import prepare
                    frames,unused=prepare(native.raw,args[4],changes,native.ident['mode'])
                    for report,command,payload in frames:native.exchange(report,command,payload,reply=False)
                writes.append(('mchose',args[4],changes));return ''
            values={c.name:copy.deepcopy(c.value) for c in k7.capabilities}
            values.update(native.read(),dock_lighting=dock_values(dock_record),dock_rgb_record=list(dock_record))
            return json.dumps(values)
        if args[:2]==['logi-sdk','mchose-ace68']:
            field=args[4] if len(args)>4 else None;value=json.loads(args[5]) if len(args)>5 else None
            if args[2]=='set':writes.append(('ace',field.split('/')[-1],value))
            with patch('ace68_adapter.candidates',return_value=[ITEM]),patch('drafts.atomic_json'):
                observed=hardware(args[2],selector(ITEM),field,value,transport=lambda node:ace_wire)
            state.update(observed)
            for cap in keyboard.capabilities:
                if cap.name in state:cap.value=copy.deepcopy(state[cap.name])
            return json.dumps(observed)
        if args[:2]==['ratbagctl','sim-editor']:
            profile=next(p for p in ratbag['profiles'] if p['index']==ratbag['active'])
            if args[2:]==['profile','active','get']:return str(ratbag['active'])
            if args[2:5]==['profile','active','set']:ratbag['active']=int(args[-1]);writes.append(('profile',ratbag['active']));return ''
            if 'led' in args:
                led=profile['leds'][int(args[args.index('led')+1])]
                if 'set' in args:
                    offset=args.index('set');led[args[offset+1]]=args[offset+2];writes.append(('led',args[offset+1]));return ''
                return 'LED: 0, depth: rgb, mode: '+led['mode']+', color: '+led['color']+', duration: '+str(led['duration'])+', brightness: '+str(led['brightness'])
            if 'rate' in args:
                if 'set' in args:profile['rate']=int(args[-1]);writes.append(('rate',int(args[-1])));return ''
                return str(profile['rate'])
            if 'button' in args:
                index=int(args[args.index('button')+1]);button=profile['buttons'][index]
                if 'set' in args:
                    action=args[args.index('set')+1:];writes.append(('button',index,action));button['macro']=action[0]=='macro'
                    button['action']=' '.join(('↓'+t[1:] if t.startswith('+') else '↑'+t[1:] if t.startswith('-') else '↕'+t if t.startswith('KEY_') else t) for t in action[1:]) if button['macro'] else ' '.join(action)
                    return ''
                return ('macro ' if button['macro'] else '')+button['action']
            if 'dpi' in args:
                resolution=profile['resolutions'][int(args[args.index('resolution')+1])]
                if 'set' in args:resolution['dpi']=int(args[-1]);writes.append(('dpi',int(args[-1])));return ''
                return str(resolution['dpi'])
        raise AssertionError('Unexpected fixture command: '+repr(args[:3]))
    bridge._editor.runner=runner;bridge._editor.reader=lambda target:copy.deepcopy(ratbag)
    bridge._audio.fixture=None;bridge._audio.runner=runner
    bridge.refresh=lambda:bridge._accept_snapshot(snapshot(),None)
    bridge._accept_snapshot(snapshot(),None)
    bridge.setLanguage('ru')
    folder=Path(os.environ.get('LOGI_CENTER_QML_SCREENSHOT_DIR','/tmp/logi-qml-functional'));folder.mkdir(parents=True,exist_ok=True)
    deadline=time.monotonic()+45
    forbidden=patch('backend.run',side_effect=AssertionError('REAL HARDWARE I/O IN FUNCTIONAL SMOKE'))
    real=forbidden.start()
    timings={};start=time.monotonic()
    def checked(callback):
        try:callback()
        except BaseException:
            import traceback
            traceback.print_exc();root.grabWindow().save(str(folder/'failure.png'));forbidden.stop();app.exit(12)
    def wait(callback):
        if time.monotonic()>deadline:raise AssertionError('Functional smoke timed out')
        if bridge.editor.busy or bridge.audio.busy or bridge.diagnosticController.busy:QTimer.singleShot(15,lambda:checked(lambda:wait(callback)))
        else:callback()
    def select(identifier,section):
        bridge.selectDevice(identifier);root.setProperty('page','device');bridge.editor.setSection(section)
    def mouse_ready():
        bridge.editor.setSection('pointer')
        timings['mouse_open_ms']=round((time.monotonic()-start)*1000,1)
        assert bridge.editor.fields.count>0
        bridge.editor.edit('ratbagctl:dpi',1600);assert writes==[]
        bridge.editor.edit('ratbagctl:polling_rate',500)
        bridge.editor.applyGroup();QTimer.singleShot(30,lambda:checked(lambda:wait(mouse_written)))
    def mouse_written():
        assert ratbag['profiles'][0]['resolutions'][0]['dpi']==1600,(bridge.editor.message,bridge.editor.resultState,writes)
        assert ratbag['profiles'][0]['rate']==500
        assert bridge.editor.resultState=='sent_unverified'
        bridge.editor.setSection('buttons');bridge.editor.clearMacro();bridge.editor.setCapturePauses(False);bridge.editor.setRecording(True)
        for name,pressed in [('Control_L',True),('c',True),('c',False),('Control_L',False)]:bridge.editor.recordKey(name,pressed)
        bridge.editor.stopRecording();assert len(bridge.editor.macroEvents)==4
        bridge.editor.applyMacro();QTimer.singleShot(30,lambda:checked(lambda:wait(profile_start)))
    def profile_start():
        bridge.editor.setSection('profiles');bridge.editor.edit('ratbagctl:profiles',1);bridge.editor.applyGroup()
        QTimer.singleShot(30,lambda:checked(lambda:wait(profile_restore)))
    def profile_restore():
        assert ratbag['active']==1
        bridge.editor.edit('ratbagctl:profiles',0);bridge.editor.applyGroup()
        QTimer.singleShot(30,lambda:checked(lambda:wait(lighting_start)))
    def lighting_start():
        assert ratbag['active']==0
        bridge.editor.setSection('lighting');bridge.editor.edit('ratbagctl:led:0:color',[10,20,30]);bridge.editor.edit('ratbagctl:led:0:mode','breathing');bridge.editor.applyGroup()
        QTimer.singleShot(30,lambda:checked(lambda:wait(keyboard_start)))
    def keyboard_start():
        assert any(item[0]=='button' for item in writes)
        assert ratbag['profiles'][0]['leds'][0]['color']=='0a141e'
        expected_led_writes=['duration','brightness','mode','color'] if stabilization else ['mode','color']
        assert [item[1] for item in writes if item[0]=='led']==expected_led_writes,writes
        select(keyboard.id,'keys');bridge.editor.selectKey('50')
        assert len(bridge.editor.keyModel)==68 and bridge.editor.fields.count==6
        QTimer.singleShot(80,lambda:checked(keyboard_input))
    def visual(item,name):
        if item.objectName()==name and item.isVisible():return item
        for child in item.childItems():
            result=visual(child,name)
            if result is not None:return result
        return None
    def keyboard_input():
        field=visual(root.contentItem(),'control-value-key:50:actuation');assert field is not None
        field.forceActiveFocus();QTest.keyClick(root,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier)
        for key in (Qt.Key.Key_0,Qt.Key.Key_Period,Qt.Key.Key_3,Qt.Key.Key_1):QTest.keyClick(root,key)
        QTest.keyClick(root,Qt.Key.Key_Return)
        assert bridge.editor._desired(bridge.editor._field('key:50:actuation'))[0]==.31
        QTimer.singleShot(40,lambda:checked(keyboard_apply))
    def keyboard_apply():
        from PySide6.QtCore import QPoint,QPointF
        button=visual(root.contentItem(),'editor-apply');assert button is not None
        point=button.mapToItem(root.contentItem(),QPointF(button.width()/2,button.height()/2))
        QTest.mouseClick(root,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(round(point.x()),round(point.y())))
        QTimer.singleShot(30,lambda:checked(lambda:wait(audio_start)))
    def audio_start():
        assert state['actuation']['50']==.31
        assert bridge.editor.resultState=='confirmed'
        bridge.selectDevice(headset.id);root.setProperty('page','audio')
        bridge.audio.editVolume('sink',42);bridge.audio.applyEndpoint('sink','volume')
        QTimer.singleShot(30,lambda:checked(lambda:wait(diagnostics_start)))
    def diagnostics_start():
        assert bridge.audio.selectedOutput['volume']==42
        assert bridge.audio.session is None and bridge.audio.testState=='idle'
        bridge.diagnosticController.collect()
        report=json.loads(bridge.diagnosticController.reportText)
        assert report['format']=='logi-center-public-diagnostics'
        assert all('physical' not in row and 'target' not in row for row in report['devices'])
        capture(0)
    sizes=[(640,780),(800,780),(1000,780),(1280,800),(1600,900),(1920,1080)] if os.environ.get('LOGI_CENTER_MIGRATION_MATRIX')=='1' else [(1000,780)]
    cases=[(name,lang,w,h) for name in ('dashboard','mouse','keyboard','audio') for lang in ('ru','en') for w,h in sizes]
    cases += [('macro','ru',1000,780),('backups','ru',1000,780),('diagnostics','ru',1000,780),('read-error','ru',1000,780)]
    if stabilization:
        cases=[(name,lang,w,h) for name in ('dashboard','buttons','buttons-side','buttons-wireless','buttons-side-wireless','buttons-edit','lighting','advanced','audio','effects-empty','k7-pointer','k7-buttons','k7-buttons-shortcuts','k7-advanced','k7-read-error','k7-indicators','k7-dock','k7-dock-static','k7-dock-wave') for lang in ('ru','en') for w,h in ((640,780),(1280,800))]
        cases += [(name,'ru',1000,780) for name in ('effects-unavailable','effects-error','effects-loading','effects-ready')]
    if os.environ.get('LOGI_CENTER_ACE_EDITOR')=='1':
        cases=[('ace-'+name,lang,w,h) for name in ('lighting','keys','key_assignments','advanced_keys','performance','profiles') for lang in ('ru','en') for w,h in ((640,780),(1280,800))]
        cases += [('ace-'+name+'-controls',lang,w,h) for name in ('keys','key_assignments','advanced_keys','performance') for lang in ('ru','en') for w,h in ((640,780),(1280,800))]
    requested=os.environ.get('LOGI_CENTER_MIGRATION_CAPTURE_PAGES','').split(',')
    if requested!=['']:cases=[case for case in cases if case[0] in requested]
    def capture(index):
        if index==len(cases):
            real.assert_not_called();forbidden.stop()
            print('PASS: mouse DPI/cache readback, macro, Ace68 selected key/device readback, audio/server readback, diagnostics; no real I/O.')
            print('Migration mock timings:',json.dumps(timings,sort_keys=True))
            finish();return
        page,language,width,height=cases[index]
        bridge.setLanguage(language)
        if page=='mouse':select(mouse.id,'pointer')
        elif page in ('macro','buttons','buttons-side','buttons-wireless','buttons-side-wireless','buttons-edit'):
            select(mouse.id,'buttons')
            bridge.editor.setG502View('side' if 'side' in page else 'top')
        elif page in ('lighting','advanced'):select(mouse.id,page)
        elif page.startswith('k7-'):select(k7.id,'dock' if page.startswith('k7-dock') else 'buttons' if page.startswith('k7-buttons') else 'pointer' if page=='k7-read-error' else page.removeprefix('k7-'))
        elif page.startswith('effects-'):
            bridge.selectDevice(headset.id);root.setProperty('page','audio')
        elif page=='keyboard':select(keyboard.id,'keys')
        elif page.startswith('ace-'):
            select(keyboard.id,page.removeprefix('ace-').removesuffix('-controls'))
            if page=='ace-keys':bridge.editor.selectAceKeys('wasd')
        elif page=='audio':bridge.selectDevice(headset.id);root.setProperty('page','audio')
        elif page=='read-error':
            plain.faults=[Fault(FaultCode.CONNECTION,'simulation','Technical protocol failure')]
            bridge.selectDevice(plain.id);root.setProperty('page','device')
            assert 'Technical protocol' not in bridge.editor.message
        else:root.setProperty('page',page)
        root.resize(width,height)
        if stabilization and page.startswith('buttons'):
            mouse.connection='wireless' if 'wireless' in page else 'usb'
            bridge._refresh_artwork_row(mouse);bridge.editor.changed.emit()
        if stabilization and page.startswith('k7-'):
            legacy='device:'+k7.id+':stage'
            if page=='k7-read-error':
                bridge.editor.store.values[legacy]={'base':0,'desired':1}
                bridge.editor._state_error=bridge.tr('Нет доступа к устройству')
            else:
                bridge.editor.store.values.pop(legacy,None)
                bridge.editor._state_error=''
            bridge.editor._render()
            if page.startswith('k7-dock'):
                bridge.editor.discardGroup()
                if page=='k7-dock-static':
                    bridge.editor.edit('mchose:dock:mode','static')
                    bridge.editor.edit('mchose:dock:color',[220,80,60])
                elif page=='k7-dock-wave':bridge.editor.edit('mchose:dock:mode','wave')
        if stabilization and page=='k7-indicators':
            from threading import Event
            # Simulate a fresh device charging report after opening the editor.
            bridge._accept_battery(([(k7.id,'mchose','sim-k7',
                                      {'battery_status':52,'charging':True,'identity':{'mode':1}},None)],
                                     [],None,None),Event(),None)
        if stabilization and page.startswith('effects-'):
            audio_page=visual(root.contentItem(),'audio-page');assert audio_page is not None
            audio_page.setProperty('section','effects')
            controller=bridge.audio
            controller._preset_state=page.removeprefix('effects-')
            controller._effects_available=controller._preset_state!='unavailable'
            controller._presets={'input':[],'output':['Studio · SIM'] if controller._preset_state=='ready' else []}
            controller.changed.emit()
        elif stabilization and page=='audio':
            visual(root.contentItem(),'audio-page').setProperty('section','sound')
        macro_scrolled=[False]
        lighting_previewed=[False]
        dock_clicked=[False]
        k7_clicked=[False]
        ace_scrolled=[False]
        ace_tested=[False]
        def save():
            if bridge.editor.busy:QTimer.singleShot(30,lambda:checked(save));return
            if page=='ace-advanced_keys-controls' and not ace_tested[0]:
                area=visual(root.contentItem(),'ace-key-test-area');assert area is not None
                before=len(writes);area.forceActiveFocus()
                QTest.keyPress(root,Qt.Key.Key_C)
                pressed=area.property('pressed');pressed=pressed.toVariant() if hasattr(pressed,'toVariant') else pressed
                assert 'C' in pressed.values(),pressed
                QTest.keyRelease(root,Qt.Key.Key_C)
                QTest.keyClick(root,Qt.Key.Key_Escape)
                assert not area.hasActiveFocus() and len(writes)==before
                ace_tested[0]=True
            if page.startswith('ace-') and page.endswith('-controls') and not ace_scrolled[0]:
                scroll=visual(root.contentItem(),'deviceEditorScroll');assert scroll is not None
                content=scroll.property('contentItem')
                content.setProperty('contentY',min(380,max(0,content.property('contentHeight')-content.property('height'))))
                if 'advanced_keys' in page:
                    panel=visual(root.contentItem(),'ace-advanced-panel');assert panel is not None
                    panel.setProperty('kind','dks')
                ace_scrolled[0]=True;QTimer.singleShot(80,lambda:checked(save));return
            if stabilization and page=='lighting' and not lighting_previewed[0]:
                bridge.editor.edit('ratbagctl:led:0:mode','cycle')  # Draft preview; no setting write.
                lighting_previewed[0]=True
            target_section='dock' if page.startswith('k7-dock') else 'pointer' if page=='k7-read-error' else 'buttons' if page in ('macro','buttons','buttons-edit') or page.startswith('k7-buttons') else page.removeprefix('k7-') if page.startswith('k7-') else page if page in ('lighting','advanced') else ''
            if target_section and bridge.editor.section!=target_section:
                bridge.editor.setSection(target_section);QTimer.singleShot(70,lambda:checked(save));return
            if page=='k7-dock' and not dock_clicked[0]:
                button=visual(root.contentItem(),'dock-mode-static');assert button is not None
                point=button.mapToItem(root.contentItem(),QPointF(button.width()/2,button.height()/2))
                assert 0<=point.y()<root.height()
                before=len(writes)
                QTest.mouseClick(root,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(round(point.x()),round(point.y())))
                assert bridge.editor.dockState['mode']=='static' and len(writes)==before
                bridge.editor.discardGroup();root.contentItem().forceActiveFocus();dock_clicked[0]=True
                QTimer.singleShot(70,lambda:checked(save));return
            if page.startswith('k7-dock'):
                picker=visual(root.contentItem(),'dock-color-picker')
                assert (picker is not None)==(page=='k7-dock-static')
            if page=='k7-pointer' and not k7_clicked[0]:
                before=len(writes)
                numeric=visual(root.contentItem(),'k7-dpi-input-x0');assert numeric is not None
                point=numeric.mapToItem(root.contentItem(),QPointF(numeric.width()/2,numeric.height()/2))
                QTest.mouseClick(root,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(round(point.x()),round(point.y())))
                QTest.keyClick(root,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier)
                for key in (Qt.Key.Key_8,Qt.Key.Key_5,Qt.Key.Key_0):QTest.keyClick(root,key)
                assert numeric.property('text')=='850'
                bridge.editor.telemetryUpdated()
                assert numeric.property('text')=='850', 'Telemetry must preserve the focused DPI entry'
                button=visual(root.contentItem(),'k7-dpi-count-2');assert button is not None
                point=button.mapToItem(root.contentItem(),QPointF(button.width()/2,button.height()/2))
                QTest.mouseClick(root,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(round(point.x()),round(point.y())))
                assert bridge.editor.k7Fields['mchose:dpi_config:count']['value']==2
                assert len(writes)==before
                bridge.editor.discardGroup();k7_clicked[0]=True
                QTimer.singleShot(50,lambda:checked(save));return
            if page=='k7-buttons':
                before=len(writes)
                buttons=[visual(root.contentItem(),'k7-button-label-'+str(i)) for i in range(5)]
                assert all(b is not None for b in buttons)
                for i,button in enumerate(buttons):
                    point=button.mapToItem(root.contentItem(),QPointF(button.width()/2,button.height()/2))
                    assert 0<=point.x()<root.width() and 0<=point.y()<root.height()
                    QTest.mouseClick(root,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(round(point.x()),round(point.y())))
                    assert bridge.editor.k7SelectedButton==i
                    anchor=visual(root.contentItem(),'k7-button-anchor-'+str(i));assert anchor is not None
                    point=anchor.mapToItem(root.contentItem(),QPointF(anchor.width()/2,anchor.height()/2))
                    assert 0<=point.x()<root.width() and 0<=point.y()<root.height()
                    bridge.editor.selectK7Button((i+1)%5)
                    QTest.mouseClick(root,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(round(point.x()),round(point.y())))
                    assert bridge.editor.k7SelectedButton==i
                assert len(writes)==before
            if page=='k7-buttons-shortcuts' and not k7_clicked[0]:
                panel=visual(root.contentItem(),'k7-button-panel');assert panel is not None
                bridge.editor.selectK7Button(4);panel.setProperty('category','hotkey')
                k7_clicked[0]=True
                QTimer.singleShot(70,lambda:checked(save));return
            if page=='k7-buttons-shortcuts':
                scroll=visual(root.contentItem(),'deviceEditorScroll');assert scroll is not None
                flick=scroll.property('contentItem');flick.setProperty('contentY',max(0,flick.property('contentHeight')-flick.height()-160))
                button=visual(root.contentItem(),'k7-hotkey-assign');assert button is not None
                point=button.mapToItem(root.contentItem(),QPointF(button.width()/2,button.height()/2))
                assert 0<=point.y()<root.height()
                before=len(writes)
                QTest.mouseClick(root,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(round(point.x()),round(point.y())))
                assert bridge.editor.k7Fields['mchose:button_bindings:4']['value']==[2,0x010400]
                assert len(writes)==before
            if stabilization and page.startswith('buttons') and page!='buttons-edit':
                bridge.editor.setSection('buttons');app.processEvents()
                scroll=visual(root.contentItem(),'deviceEditorScroll');flick=scroll.property('contentItem')
                flick.setProperty('contentY',0);app.processEvents()
                view='side' if 'side' in page else 'top'
                toggle=visual(root.contentItem(),'g502-view-'+view)
                point=toggle.mapToItem(root.contentItem(),QPointF(toggle.width()/2,toggle.height()/2))
                QTest.mouseClick(root,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(round(point.x()),round(point.y())))
                app.processEvents();assert bridge.editor.g502View==view
                diagram=visual(root.contentItem(),'g502-button-diagram');assert diagram is not None
                art=visual(root.contentItem(),'g502-button-artwork');assert art is not None
                assert art.property('artworkReady'),art.property('source')
                raster=art.property('sourceSize')
                assert 0<raster.width()<=1024 and raster.height()<=0,raster
                expected=bridge.editor.g502Canvas['file']
                assert art.property('source').toString().endswith(expected)
                canvas=bridge.editor.g502Canvas
                assert abs(art.width()/art.height()-canvas['width']/canvas['height'])<.001
                scroll=visual(root.contentItem(),'deviceEditorScroll');flick=scroll.property('contentItem')
                point=diagram.mapToItem(root.contentItem(),QPointF(0,0))
                flick.setProperty('contentY',max(0,min(flick.property('contentHeight')-flick.height(),flick.property('contentY')+point.y()-125)))
                app.processEvents()
                rows=bridge.editor.g502Buttons
                for row in rows:
                    hit=visual(root.contentItem(),'g502-button-anchor-'+str(row['index']))
                    assert (hit.width(),hit.height())==(12,12)
                    overlay=visual(root.contentItem(),'g502-button-overlay-'+str(row['index']))
                    route=overlay.property('routePoints');route=route.toVariant() if hasattr(route,'toVariant') else route
                    assert all(0<=p['x']<=diagram.width() and 0<=p['y']<=diagram.height() for p in route)
                    assert all(a['x']==b['x'] or a['y']==b['y'] for a,b in zip(route,route[1:])),route
                labels=[visual(root.contentItem(),'g502-button-label-'+str(row['index'])) for row in rows]
                for label in labels:
                    assert label is not None
                    assert label.x()>=0 and label.y()>=0 and label.x()+label.width()<=diagram.width() and label.y()+label.height()<=diagram.height()
                    for other in labels:
                        if label is not other:assert label.x()+label.width()<=other.x() or other.x()+other.width()<=label.x() or label.y()+label.height()<=other.y() or other.y()+other.height()<=label.y()
                for row in rows:
                    for prefix in ('g502-button-label-','g502-button-anchor-'):
                        item=visual(root.contentItem(),prefix+str(row['index']))
                        top=flick.mapToItem(root.contentItem(),QPointF(0,0)).y()
                        point=item.mapToItem(root.contentItem(),QPointF(item.width()/2,item.height()/2))
                        flick.setProperty('contentY',max(0,min(flick.property('contentHeight')-flick.height(),flick.property('contentY')+point.y()-top-flick.height()/2)))
                        app.processEvents()
                        item=visual(root.contentItem(),prefix+str(row['index']))
                        point=item.mapToItem(root.contentItem(),QPointF(item.width()/2,item.height()/2))
                        assert top<=point.y()<top+flick.height(),(row['index'],point.y(),top)
                        QTest.mouseClick(root,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(round(point.x()),round(point.y())))
                        app.processEvents()
                        assert bridge.editor.selectedButton==row['index'],(prefix,row['index'],bridge.editor.selectedButton)
                point=diagram.mapToItem(root.contentItem(),QPointF(0,0))
                top=flick.mapToItem(root.contentItem(),QPointF(0,0)).y()
                flick.setProperty('contentY',max(0,flick.property('contentY')+point.y()-top))
                app.processEvents()
                assert set(row['index'] for row in rows)==({3,4,5} if 'side' in page else {0,1,2,6,7,8,9,10})
                if language=='ru' and width==1280 and page in ('buttons','buttons-side'):
                    chosen=4 if view=='side' else 7
                    bridge.editor.selectButton(chosen);app.processEvents()
                    baseline=(bridge.editor.selectedButton,len(writes),bridge.editor.dirtyCount)
                    def move_to(item):
                        point=item.mapToItem(root.contentItem(),QPointF(item.width()/2,item.height()/2))
                        top=flick.mapToItem(root.contentItem(),QPointF(0,0)).y()
                        flick.setProperty('contentY',max(0,min(flick.property('contentHeight')-flick.height(),flick.property('contentY')+point.y()-top-flick.height()/2)))
                        app.processEvents()
                        point=item.mapToItem(root.contentItem(),QPointF(item.width()/2,item.height()/2))
                        QTest.mouseMove(root,QPoint(round(point.x()),round(point.y())))
                        QTest.qWait(200)
                    QTest.mouseMove(root,QPoint(5,75));QTest.qWait(200)
                    for row in rows:
                        overlay=visual(root.contentItem(),'g502-button-overlay-'+str(row['index']))
                        assert overlay.property('lineAlpha')==(1 if row['index']==chosen else 0)
                        assert overlay.property('chosen')==(row['index']==chosen)
                    assert root.grabWindow().save(str(folder/f'overlay-selected-{view}.png'))
                    for row in rows:
                        if row['index']==chosen:continue
                        hit=visual(root.contentItem(),'g502-button-anchor-'+str(row['index']))
                        move_to(hit)
                        overlay=visual(root.contentItem(),'g502-button-overlay-'+str(row['index']))
                        assert overlay.property('hoverActive') and overlay.property('lineAlpha')>.7
                        tooltip=hit.findChild(QObject,'g502-button-tooltip-'+str(row['index']))
                        assert tooltip is not None and tooltip.property('text')==row['label']
                        assert (bridge.editor.selectedButton,len(writes),bridge.editor.dirtyCount)==baseline
                    hovered=3 if view=='side' else 6
                    for prefix in ('g502-button-label-','g502-button-anchor-'):
                        move_to(visual(root.contentItem(),prefix+str(hovered)))
                        assert visual(root.contentItem(),'g502-button-overlay-'+str(hovered)).property('hoverActive')
                        assert (bridge.editor.selectedButton,len(writes),bridge.editor.dirtyCount)==baseline
                    QTest.qWait(180)
                    assert root.grabWindow().save(str(folder/f'overlay-hover-{view}.png'))
                    QTest.mouseMove(root,QPoint(5,75));QTest.qWait(200)
                    assert visual(root.contentItem(),'g502-button-overlay-'+str(hovered)).property('lineAlpha')==0
            if stabilization and page=='buttons-edit':
                bridge.editor.setSection('buttons');app.processEvents()
                from PySide6.QtGui import QGuiApplication
                panel=visual(root.contentItem(),'g502-button-panel');panel.openMacros()
                app.processEvents()
                window=panel.property('macroWindow')
                assert window.isVisible()
                window.requestActivate();QTest.qWait(100)
                editor=bridge.editor
                editor.createLibraryMacro('Keyboard · SIM');editor.setCapturePauses(False)
                area=visual(window.contentItem(),'macro-capture-area')
                toggle=visual(window.contentItem(),'macro-record-toggle')
                editor.beginMacroCapture(window,area);toggle.forceActiveFocus();QTest.qWait(30)
                for key in (Qt.Key.Key_Space,Qt.Key.Key_A,Qt.Key.Key_Left,Qt.Key.Key_F5,Qt.Key.Key_Semicolon):QTest.keyClick(window,key)
                assert editor.recording,'Space must not activate the focused Stop control'
                point=area.mapToItem(window.contentItem(),QPointF(area.width()/2,area.height()/2))
                for button in (Qt.MouseButton.LeftButton,Qt.MouseButton.RightButton):QTest.mouseClick(window,button,Qt.KeyboardModifier.NoModifier,QPoint(round(point.x()),round(point.y())))
                QTest.qWait(30)
                point=toggle.mapToItem(window.contentItem(),QPointF(toggle.width()/2,toggle.height()/2))
                QTest.mouseClick(window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(round(point.x()),round(point.y())))
                app.processEvents()
                if editor.recording:
                    window.grabWindow().save(str(folder/'macro-failure.png'))
                assert not editor.recording,'Stop button must end recording'
                tokens=[row['token'] for row in editor.macroEvents]
                assert all(t in tokens for t in ('+KEY_A','-KEY_A','+KEY_SPACE','-KEY_SPACE','+KEY_LEFT','+KEY_F5','+KEY_SEMICOLON','+BTN_LEFT','-BTN_LEFT','+BTN_RIGHT','-BTN_RIGHT')),tokens
                from mouse_models import validate_macro
                validate_macro(tokens)
                window=panel.property('macroWindow')
                assert window.isVisible()
                assert window.grabWindow().save(str(folder/f'macro-window-{language}-{width}.png'))
                window.close();app.processEvents()
            if stabilization and (page=='dashboard' or not bridge.editor.g502Editor):
                # Include invisible instances: the original bug decoded generic.svg
                # in hidden G502 panels before any editor was opened.
                def assert_idle_art(item):
                    if item.objectName()=='g502-button-artwork':assert item.property('source').isEmpty()
                    for child in item.childItems():assert_idle_art(child)
                assert_idle_art(root.contentItem())
            if stabilization and page=='dashboard':
                assert any(row['deviceId']==mouse.id and row['artworkSource']=='exact-model' and
                           'g502-top-wired-qt.svg' in row['imageSource'] for row in bridge._all_presentations)
            if stabilization and page=='k7-indicators':
                assert bridge.selectedDevice['charging'] is True
                assert bridge.editor.k7Status['charging']==('Заряжается' if language=='ru' else 'Charging')
            if page=='k7-read-error':
                warning=visual(root.contentItem(),'editor-live-read-error');assert warning is not None
                point=warning.mapToItem(root.contentItem(),QPointF(0,0))
                assert 0<=point.y()<root.height()-warning.height()
            if stabilization and page.startswith('effects-'):
                for kind in ('input','output'):
                    button=visual(root.contentItem(),'preset-apply-'+kind);assert button is not None
                    assert button.isEnabled()==(page=='effects-ready' and kind=='output')
            assert root.grabWindow().save(str(folder/f'{page}-{language}-{width}.png'))
            QTimer.singleShot(10,lambda:checked(lambda:capture(index+1)))
        QTimer.singleShot(180,lambda:checked(save))
    select(mouse.id,'pointer')
    QTimer.singleShot(30,lambda:checked(lambda:wait(mouse_ready)))


if __name__=='__main__':
    import argparse,subprocess
    parser=argparse.ArgumentParser();parser.add_argument('--wayland',action='store_true');parser.add_argument('--stabilization',action='store_true');parser.add_argument('--ace',action='store_true');parser.add_argument('--matrix',action='store_true');parser.add_argument('--output',default='/tmp/logi-qml-functional');args=parser.parse_args()
    base=Path(__file__).resolve().parents[1]
    if args.stabilization:os.environ['LOGI_CENTER_EDITOR_STABILIZATION']='1'
    if args.ace:os.environ['LOGI_CENTER_ACE_EDITOR']='1'
    env=os.environ.copy();env['LOGI_CENTER_QML_FUNCTIONAL_SMOKE']='1';env['LOGI_CENTER_QML_SCREENSHOT_DIR']=str(Path(args.output).resolve());env['LOGI_CENTER_MIGRATION_MATRIX']='1' if args.matrix else '0'
    env['QT_QPA_PLATFORM']='wayland' if args.wayland else 'offscreen';env['QT_QPA_PLATFORMTHEME']='generic'
    raise SystemExit(subprocess.call([sys.executable,str(base/'app.py'),'--ui','qml','--simulate','--smoke'],cwd=base,env=env))
