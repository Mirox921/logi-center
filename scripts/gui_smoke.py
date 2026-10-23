#!/usr/bin/env python3
"""Desktop-only read/GUI check. Never click Apply or start audio capture."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.argv=['logi-center-smoke','--smoke']
from unittest.mock import patch,Mock
from app import Center,Gtk,GLib
from mouse_editor import MouseEditor
from microphone_ui import MicrophonePanel
from backups import preview
from test_backups import sample
from discovery import MousePresence
from i18n import set_language

application=Center();application.set_application_id('local.mirox.LogiCenter.Smoke');application.preferences['language']='ru';set_language('ru')
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
    original_presence=application.mouse_presence
    application.mouse_presence=MousePresence('Logitech G502 HERO',False);application.update_batteries()
    assert application.battery_widgets['G305'][0].get_text()=='G502 HERO · Не в сети'
    application.mouse_presence.invalidate();application.update_batteries()
    assert 'Подключена по USB' not in application.battery_widgets['G305'][0].get_text()
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
