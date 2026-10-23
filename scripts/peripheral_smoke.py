#!/usr/bin/env python3
"""Read-only live GTK category/width review. Capture only this application's widgets."""
from pathlib import Path
import sys,tempfile,json,subprocess,os,shutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.argv=['logi-peripheral-review']
from unittest.mock import patch
from app import Center,Gtk,GLib
from drafts import DraftStore
from peripheral_ui import populate
from keyboard_ui import MagneticKeyboardEditor
from gi.repository import Gsk
app=Center();app.set_application_id('local.mirox.LogiCenter.PeripheralReview'+str(__import__('os').getpid()))
private=tempfile.TemporaryDirectory(prefix='logi-peripheral-review-');app.draft_store=DraftStore(Path(private.name)/'drafts.json')
output=Path('/tmp/logi-peripheral-review');output.mkdir(exist_ok=True)
checks=[]
def resize(width,height):
    if not shutil.which('hyprctl'):return
    clients=json.loads(subprocess.check_output(['hyprctl','-j','clients'],text=True))
    own=next((w for w in clients if w.get('pid')==os.getpid()),None)
    if own:
        target='address:'+own['address']
        if not own.get('floating'):
            subprocess.run(['hyprctl','dispatch',f'hl.dsp.window.float({{ window = {json.dumps(target)}, action = \"toggle\" }})'],check=True,stdout=subprocess.DEVNULL)
        subprocess.run(['hyprctl','dispatch',f'hl.dsp.window.resize({{ window = {json.dumps(target)}, x = {width}, y = {height} }})'],check=True,stdout=subprocess.DEVNULL)
def descendants(widget):
    yield widget
    child=widget.get_first_child()
    while child:
        yield from descendants(child);child=child.get_next_sibling()
def capture(name):
    widget=app.win
    snapshot=Gtk.Snapshot();Gtk.WidgetPaintable.new(widget).snapshot(snapshot,widget.get_width(),widget.get_height())
    node=snapshot.to_node()
    if node is None:raise RuntimeError('Widget snapshot not ready: '+name)
    texture=widget.get_renderer().render_texture(node,None)
    texture.save_to_png(str(output/(name+'.png')))
def step(index=0):
    try:
        if app.active_jobs:
            GLib.timeout_add(200,lambda:step(index));return False
        if index==0:
            mice=app.device_manager.active('mouse');keyboards=app.device_manager.active('keyboard')
            assert not any('K7 Ultra Keyboard' in d.name for d in keyboards)
            print('Live mice:',[(d.name,d.connected) for d in mice],flush=True)
            print('Live keyboards:',[(d.name,d.connected) for d in keyboards],flush=True)
            k7=next((d for d in mice if d.backend=='mchose'),None)
            if k7:
                app.selected_peripherals['mouse']=k7.id;populate(app,'mouse',{})
                assert any(c.name=='battery_status' and c.value is not None for c in k7.capabilities)
            resize(1000,780)
            app.stack.set_visible_child_name('mouse')
            GLib.timeout_add(700,lambda:(capture('mouse-wide'),step(1),False)[-1]);return False
        if index==1:
            ace=next((d for d in app.device_manager.active('keyboard') if 'mchose-ace68' in d.backends),None)
            if ace:
                app.selected_peripherals['keyboard']=ace.id;populate(app,'keyboard',{})
            app.stack.set_visible_child_name('keyboard')
            for widget in descendants(app.pages['keyboard']):
                if isinstance(widget,Gtk.Stack) and widget.get_child_by_name('keys'):widget.set_visible_child_name('keys')
            GLib.timeout_add(1400,lambda:(capture('keyboard-wide'),step(2),False)[-1]);return False
        if index==2:
            resize(640,780)
            clamp=app.pages['keyboard'].get_parent();clamp.set_maximum_size(520);clamp.set_tightening_threshold(520)
            GLib.timeout_add(700,lambda:(capture('keyboard-narrow'),step(3),False)[-1]);return False
        if index==3:
            editor=next((w for w in descendants(app.pages['keyboard']) if isinstance(w,MagneticKeyboardEditor)),None)
            if editor:
                minimum,natural,*_=editor.diagram.measure(Gtk.Orientation.HORIZONTAL,-1)
                print('Keyboard minimum/natural width:',minimum,natural,'allocated:',editor.diagram.get_width(),flush=True)
                if editor.diagram.get_width()>520:
                    offenders=[]
                    for w in descendants(app.pages['keyboard']):
                        m,*_=w.measure(Gtk.Orientation.HORIZONTAL,-1)
                        if m>520:offenders.append((type(w).__name__,m))
                    print('Wide minimums:',offenders[:30],flush=True)
                assert minimum<=520
                assert editor.diagram.get_width()<=520
            print('Actual narrow window:',app.win.get_width(),app.win.get_height(),flush=True)
            assert app.pages['keyboard'].get_width()<=520
            adjustment=app.stack.get_child_by_name('keyboard').get_hadjustment()
            assert adjustment.get_upper()<=adjustment.get_page_size()+1
            app.review_editor=editor
            app.poll_peripherals()
            GLib.timeout_add(1000,lambda:step(4));return False
        if index==4:
            editor=next((w for w in descendants(app.pages['keyboard']) if isinstance(w,MagneticKeyboardEditor)),None)
            assert editor is app.review_editor
            checks.append('live-categories-and-widths');app.quit();return False
    except BaseException:
        import traceback;traceback.print_exc();app.quit();return False
GLib.timeout_add_seconds(6,step)
GLib.timeout_add_seconds(45,lambda:(app.quit(),False)[1])
with patch('app.save_preferences'):app.run(['logi-peripheral-review'])
assert checks==['live-categories-and-widths'],checks
print('Live peripheral review passed:',output)
