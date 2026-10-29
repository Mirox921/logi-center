#!/usr/bin/env python3
"""Native/live editor navigation, guarded against setting writes and recording."""
from pathlib import Path
import os,sys,subprocess,time


def exercise(app,root,bridge,finish):
    from PySide6.QtCore import QTimer
    from unittest.mock import patch
    from backend import run as original_run
    folder=Path(os.environ.get('LOGI_CENTER_QML_SCREENSHOT_DIR','/tmp/logi-qml-readonly'));folder.mkdir(parents=True,exist_ok=True)
    def read_only(args,**kwargs):
        if args[:1]==['logi-sdk'] and (len(args)<3 or args[2] not in ('read','status','battery')):raise AssertionError('A setting write reached read-only smoke')
        if args[:1]==['ratbagctl'] and 'set' in args:raise AssertionError('A ratbag write reached read-only smoke')
        if args[:2]==['solaar','config'] and len(args)>4:raise AssertionError('A Solaar write reached read-only smoke')
        if args[:1]==['pactl'] and len(args)>1 and args[1].startswith('set-'):raise AssertionError('An audio write reached read-only smoke')
        if args[:1] in (['parec'],['paplay']):raise AssertionError('Audio capture/playback reached read-only smoke')
        return original_run(args,**kwargs)
    guard=patch('backend.run',side_effect=read_only);guard.start()
    devices=[d for d in bridge._current_devices() if d.connected is True and d.backend!='solaar-local' and d.kind in ('mouse','keyboard','audio')]
    targets=[]
    for backend in ('ratbagctl','mchose','mchose-ace68','headsetcontrol'):
        device=next((d for d in devices if backend in d.backends),None)
        if device:targets.append((backend,device))
    deadline=time.monotonic()+45
    def checked(fn):
        try:fn()
        except BaseException:
            import traceback
            traceback.print_exc();guard.stop();app.exit(13)
    def take(index=0):
        if index==len(targets):
            guard.stop();print('PASS: live read-only editor navigation:',','.join(key for key,d in targets));finish();return
        backend,device=targets[index];bridge.selectDevice(device.id);root.setProperty('page','device');root.resize(1000,780)
        def ready():
            if time.monotonic()>deadline:raise AssertionError('Live read-only editor timed out')
            if bridge.editor.busy:QTimer.singleShot(50,lambda:checked(ready));return
            if backend=='mchose-ace68':bridge.editor.setSection('keys')
            elif backend in ('ratbagctl','mchose'):bridge.editor.setSection('pointer')
            assert bridge.editor.available
            if backend=='mchose-ace68':assert len(bridge.editor.keyModel)==68
            def save():
                assert root.grabWindow().save(str(folder/(backend+'-1000.png')))
                print('Read-only:',backend,'controls',bridge.editor.fields.count,'sections',len(bridge.editor.sections))
                take(index+1)
            QTimer.singleShot(180,lambda:checked(save))
        QTimer.singleShot(50,lambda:checked(ready))
    checked(take)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--wayland',action='store_true');parser.add_argument('--output',default='/tmp/logi-qml-readonly');args=parser.parse_args()
    base=Path(__file__).resolve().parents[1];env=os.environ.copy();env['QT_QPA_PLATFORM']='wayland' if args.wayland else 'offscreen';env['QT_QPA_PLATFORMTHEME']='generic'
    env['LOGI_CENTER_QML_READONLY_SMOKE']='1';env['LOGI_CENTER_QML_SCREENSHOT_DIR']=str(Path(args.output).resolve())
    raise SystemExit(subprocess.call([sys.executable,str(base/'app.py'),'--ui','qml','--smoke'],cwd=base,env=env))
