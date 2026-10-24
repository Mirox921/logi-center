#!/usr/bin/env python3
"""Desktop-only read/GUI check. Never click Apply or start audio capture."""
from pathlib import Path
import sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.argv=['logi-center-smoke','--smoke']
from unittest.mock import patch,Mock
from app import Center,Gtk,GLib
from mouse_editor import MouseEditor
from microphone_ui import MicrophonePanel
from backups import preview
from test_backups import sample
from discovery import MousePresence
from drafts import DraftStore
from backend import parse_mouse_info
from i18n import set_language

application=Center();application.set_application_id('local.mirox.LogiCenter.Smoke'+str(__import__('os').getpid()));application.preferences['language']='ru';set_language('ru')
temporary=tempfile.TemporaryDirectory(prefix='logi-gui-check-');application.draft_store=DraftStore(Path(temporary.name)/'drafts.json')
checks=[]
def descendants(widget):
    yield widget
    child=widget.get_first_child()
    while child:
        yield from descendants(child);child=child.get_next_sibling()
def check():
    assert not application.audio_session.processes and not application.audio_session.recording
    editors=[w for w in descendants(application.win) if isinstance(w,MouseEditor)]
    for editor in editors:
        if editor.buttons:editor.select(next(iter(editor.buttons)));editor.reset()
    fixture=parse_mouse_info("Model: usb:1234:5678:0\nProfile 0: (active)\n  Report Rate: 1000Hz\n    0: 800dpi (active) (default)\n  Button: 0 is mapped to 'button 1'\n  Button: 1 is mapped to 'button 2'\n  LED: 0, depth: rgb, mode: on, color: 445566\n")
    fixture.update(dpis=[800,1600],rates=[500,1000],button_types={0:[0,1,3,4],1:[0,1]},led_modes={0:['on','off']})
    previous_name=application.current_mouse_name;application.current_mouse_name='Generic fixture mouse'
    application.mouse_controls('fixture-mouse',fixture);application.current_mouse_name=previous_name
    # Exercise editable draft state even with all real mice unplugged.
    fake_buttons=[{'index':0,'action':'button 1','macro':False},{'index':1,'action':'button 2','macro':False}]
    actions={'Left':['button','1'],'Right':['button','2']};applied=Mock();changes=[]
    editor=MouseEditor('Generic test mouse',fake_buttons,actions,{0:[1,4],1:[1,4]},applied,on_draft=changes.append)
    application.pages['mouse'].append(editor)
    editor.select(0);editor.pause(100);editor.select(1);editor.select(0)
    assert editor.action.get_selected()==0 and editor.drafts[0].tokens==['t100']
    restored=MouseEditor('Generic test mouse',fake_buttons,actions,{0:[1,4],1:[1,4]},applied,state=editor.state())
    assert restored.drafts[0].tokens==['t100'];applied.assert_not_called()
    query='__no_such_device_for_smoke__'
    application.inventory_search.set_text(query);application.inventory_search.emit('search-changed')
    assert all(not group.get_visible() for name,group in application.inventory_groups)
    assert application.inventory_empty.get_visible()==bool(application.inventory_groups)
    from device_ui import populate_inventory
    populate_inventory(application,application.device_manager.devices,application.device_manager.faults)
    assert application.inventory_search.get_text()==query
    assert all(not group.get_visible() for name,group in application.inventory_groups)
    application.inventory_search.set_text('');application.inventory_search.emit('search-changed')
    assert all(group.get_visible() for name,group in application.inventory_groups)
    # Exercise new provider widgets with no hardware commands, including persistent drafts.
    from test_backend_expansion import OpenRGBTests,config
    from openrgb_adapter import describe,OpenRGBAdapter
    from mchose_adapter import MchoseAdapter
    from devices import DeviceManager
    import json
    fake=OpenRGBTests();fake.client()
    rgb=OpenRGBAdapter(lambda args:json.dumps([describe(fake.device)])).discover()
    rgb[0].kind='mouse'
    item={'node':'fake','physical':'/sys/fixture','vid':'3837','pid':'1001','name':'K7 fixture'}
    with patch('mchose_adapter.candidates',return_value=[item]):mice=MchoseAdapter(lambda args:json.dumps(config())).discover()
    old_manager=application.device_manager
    application.device_manager=DeviceManager();application.device_manager.devices=rgb+mice
    from peripheral_ui import populate as populate_peripheral
    populate_inventory(application,rgb+mice)
    from gi.repository import Adw
    expanders=[w for w in descendants(application.pages['devices']) if isinstance(w,Adw.ExpanderRow)]
    assert len(expanders)==len([d for d in rgb+mice if d.kind!='interface']) and all(not row.get_expanded() for row in expanders)
    expanded_id=application.inventory_groups[0][1].get_title()
    expanders[0].set_expanded(True);assert expanders[0].get_expanded()
    populate_inventory(application,rgb+mice)
    reopened=next(row for row in descendants(application.pages['devices']) if isinstance(row,Adw.ExpanderRow) and row.get_title()==expanded_id)
    assert reopened.get_expanded()
    reopened.set_expanded(False);assert not reopened.get_expanded()
    assert not any(isinstance(w,Gtk.ColorDialogButton) for w in descendants(application.pages['devices']))
    populate_peripheral(application,'mouse',{})
    assert any(isinstance(w,Gtk.ColorDialogButton) for w in descendants(application.pages['mouse']))
    spins=[w for w in descendants(application.pages['mouse']) if isinstance(w,Gtk.SpinButton)]
    assert spins
    spins[0].set_value(42)
    populate_peripheral(application,'mouse',{})
    spins=[w for w in descendants(application.pages['mouse']) if isinstance(w,Gtk.SpinButton)]
    assert spins[0].get_value_as_int()==42
    from test_ace68 import MemoryWire,ITEM
    from ace68_adapter import Ace68Adapter,hardware
    from keyboard_ui import MagneticKeyboardEditor
    wire=MemoryWire()
    with patch('ace68_adapter.candidates',return_value=[ITEM]):
        ace=Ace68Adapter(runner=lambda args:json.dumps(hardware('read',args[3],transport=lambda node:wire))).discover()[0]
    application.device_manager.devices=[ace]
    magnetic=MagneticKeyboardEditor(application,ace);application.pages['keyboard'].append(magnetic)
    assert len(magnetic.diagram.buttons)==68
    magnetic.diagram.select('50')
    control=next(w for w in descendants(magnetic.form) if isinstance(w,Gtk.SpinButton))
    control.set_value(.31)
    magnetic.diagram.select('0');magnetic.diagram.select('50')
    control=next(w for w in descendants(magnetic.form) if isinstance(w,Gtk.SpinButton))
    assert control.get_value()==.31
    restored_keyboard=MagneticKeyboardEditor(application,ace)
    control=next(w for w in descendants(restored_keyboard.form) if isinstance(w,Gtk.SpinButton))
    assert restored_keyboard.diagram.selected=='50' and control.get_value()==.31
    assert not wire.writes
    populate_peripheral(application,'keyboard',{})
    application.device_manager.devices=[];populate_peripheral(application,'keyboard',{})
    assert not any(isinstance(w,MagneticKeyboardEditor) for w in descendants(application.pages['keyboard']))
    application.device_manager.devices=[ace];populate_peripheral(application,'keyboard',{})
    recovered=next(w for w in descendants(application.pages['keyboard']) if isinstance(w,MagneticKeyboardEditor))
    assert next(w for w in descendants(recovered.form) if isinstance(w,Gtk.SpinButton)).get_value()==.31
    application.device_manager=old_manager
    populate_inventory(application,old_manager.devices,old_manager.faults)
    original_presence=application.mouse_presence
    application.mouse_presence=MousePresence('Logitech G502 HERO',False);application.update_batteries()
    assert all('Logitech G502 HERO' not in label.get_text() for label,icon in application.battery_widgets.values())
    application.mouse_presence.invalidate();application.update_batteries()
    assert all('Подключена по USB' not in label.get_text() for label,icon in application.battery_widgets.values())
    application.mouse_presence=original_presence;application.update_batteries()
    application.stack.set_visible_child_name('audio')
    checks.append('widgets')
    language=Gtk.DropDown.new_from_strings(['Русский','English']);language.set_selected(1)
    application.change_language(language,None)
    checks.append('language')
    application.show_diagnostics([{'component':'smoke','state':'read-only','description':'No capture or device writes'}])
    application.restore_dialog(preview(sample(1600),sample(),'smoke'),'smoke')
    pending=[];session=Mock()
    panel=MicrophonePanel([{'index':1,'name':'mock-mic'}],session,lambda fn,done,**kw:pending.append(done))
    application.pages['audio'].append(panel)
    panel.record_clicked();panel.clear()
    complete=pending.pop();complete(('mock-mic',None))
    session.record.assert_not_called()
    checks.append('dialogs-and-cancel')
    return False
GLib.timeout_add_seconds(7,check)
with patch('app.save_preferences'):
    application.run(['logi-center-smoke'])
assert checks==['widgets','language','dialogs-and-cancel'],checks
assert not application.audio_session.recording
print('GUI smoke: no writes/capture; editor, language, dialogs and cancellation passed')
