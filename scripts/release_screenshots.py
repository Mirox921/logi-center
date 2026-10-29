#!/usr/bin/env python3
"""Capture live English QML windows on workspace 9, without setting writes."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def exercise(app,root,bridge,finish):
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QGuiApplication
    assert QGuiApplication.platformName()=='wayland'
    folder=Path(os.environ['LOGI_RELEASE_SCREENSHOTS']);folder.mkdir(parents=True,exist_ok=True)
    bridge.setLanguage('en');bridge.setShowBuiltin(False);bridge.setSearch('')
    root.showMaximized();root.requestActivate()
    devices=bridge._current_devices()
    mouse=next((d for d in devices if d.kind=='mouse' and 'ratbagctl' in d.backends),None)
    keyboard=next((d for d in devices if d.kind=='keyboard' and 'mchose-ace68' in d.backends),None)
    jobs=[('dashboard',None,None)]
    if mouse:jobs += [('mouse-buttons',mouse,'buttons'),('mouse-side',mouse,'buttons'),('mouse-lighting',mouse,'lighting')]
    if keyboard:jobs += [('keyboard',keyboard,'keys'),('keyboard-lighting',keyboard,'lighting')]
    jobs += [('audio',None,None),('settings',None,None),('diagnostics',None,None)]
    captures=[];deadline=time.monotonic()+150

    def checked(work):
        try:work()
        except BaseException:
            import traceback
            traceback.print_exc();app.exit(14)

    def take(index=0):
        if index==len(jobs):
            (folder/'capture.json').write_text(json.dumps({'language':'en','workspace':9,
                'platform':'wayland','source':'live read-only devices; no mock values',
                'captures':captures},indent=2)+'\n')
            print('PASS: English live QML gallery on workspace 9:',len(captures),'screenshots; no settings writes/capture/playback.')
            finish();return
        name,device,section=jobs[index]
        if device:
            bridge.selectDevice(device.id);root.setProperty('page','device')
        else:root.setProperty('page',name)
        def ready():
            if time.monotonic()>deadline:raise AssertionError('Release capture timed out')
            if bridge.busy or bridge.editor.busy:QTimer.singleShot(75,lambda:checked(ready));return
            if section:
                bridge.editor.setSection(section)
                if section=='buttons':bridge.editor.setG502View('side' if name=='mouse-side' else 'top')
            def save():
                clients=json.loads(subprocess.check_output(['hyprctl','-j','clients'],text=True))
                own=[c for c in clients if c.get('pid')==os.getpid()]
                assert own and all(c['workspace']['id']==9 for c in own),'Capture window is not on workspace 9'
                shot=root.grabWindow();assert not shot.isNull()
                assert shot.save(str(folder/(name+'.png')))
                captures.append({'file':name+'.png','width':shot.width(),'height':shot.height()})
                QTimer.singleShot(75,lambda:checked(lambda:take(index+1)))
            QTimer.singleShot(350,lambda:checked(save))
        QTimer.singleShot(100,lambda:checked(ready))
    QTimer.singleShot(250,lambda:checked(take))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default=str(ROOT/'docs/screenshots/releases/v0.5.0'))
    options=parser.parse_args()
    previous=json.loads(subprocess.check_output(['hyprctl','-j','activeworkspace'],text=True))['id']
    os.environ.update(QT_QPA_PLATFORM='wayland',QT_QPA_PLATFORMTHEME='generic',
        LOGI_CENTER_QML_READONLY_SMOKE='1',LOGI_RELEASE_SCREENSHOTS=str(Path(options.output).resolve()))
    from backend import run as original_run
    def read_only(args,*params,**kwargs):
        if args[:1]==['logi-sdk'] and (len(args)<3 or args[2] not in ('read','status','battery','discover')):
            raise AssertionError('Hardware write in release capture')
        if args[:1]==['ratbagctl'] and 'set' in args:raise AssertionError('Ratbag write in release capture')
        if args[:2]==['solaar','config'] and len(args)!=5:raise AssertionError('Solaar write/enumeration in release capture')
        if args[:1]==['pactl'] and len(args)>1 and args[1].startswith(('set-','move-','load-','unload-','suspend-')):
            raise AssertionError('Audio write in release capture')
        if args[:1] in (['parec'],['paplay']):raise AssertionError('Audio capture/playback in release capture')
        return original_run(args,*params,**kwargs)
    # Hyprland 0.55+ Lua dispatcher, per the current official hyprctl docs.
    subprocess.run(['hyprctl','dispatch','hl.dsp.focus({ workspace = "9" })'],check=True,stdout=subprocess.DEVNULL)
    try:
        with patch('backend.run',side_effect=read_only),patch('scripts.qml_readonly_smoke.exercise',exercise):
            from qml_ui.main import run
            return run(['release-screenshots','--smoke'])
    finally:
        subprocess.run(['hyprctl','dispatch','hl.dsp.focus({ workspace = '+json.dumps(str(previous))+' })'],check=False,stdout=subprocess.DEVNULL)


if __name__=='__main__':raise SystemExit(main())
