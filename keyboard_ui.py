"""A labelled generic keyboard diagram; no unsupported per-key write controls."""
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gtk
from i18n import tr as _

class KeyboardDiagram(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        self.size=Gtk.DropDown.new_from_strings(['ANSI · TKL','ANSI · Full size','ISO · TKL'])
        self.append(self.size)
        self.keys=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4);self.append(self.keys)
        self.size.connect('notify::selected',lambda *unused:self.rebuild());self.rebuild()
        note=Gtk.Label(label=_('Справочная раскладка выбрана вручную. Переназначение и подсветка отдельных клавиш не обнаружены.'),wrap=True)
        note.add_css_class('dim-label');self.append(note)
    def rebuild(self):
        while self.keys.get_first_child():self.keys.remove(self.keys.get_first_child())
        rows=[['Esc',*['F'+str(i) for i in range(1,13)]],list('`1234567890-=')+['⌫'],['Tab',*list('QWERTYUIOP[]'),'\\'],['Caps',*list("ASDFGHJKL;'"),'Enter'],['Shift',*list('ZXCVBNM,./'),'Shift'],['Ctrl','Super','Alt','Space','Alt','Ctrl','←','↓','↑','→']]
        if self.size.get_selected()==2:rows[4].insert(1,'<>')
        for row_index,labels in enumerate(rows):
            if self.size.get_selected()==1:labels=labels+(['7','8','9'] if row_index<3 else ['4','5','6'])
            row=Gtk.Box(spacing=3,homogeneous=True)
            for key in labels:
                label=Gtk.Label(label=key,margin_top=6,margin_bottom=6);label.add_css_class('card');row.append(label)
            self.keys.append(row)
