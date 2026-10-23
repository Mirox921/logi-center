"""A labelled generic keyboard diagram; no unsupported per-key write controls."""
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gtk
from i18n import tr as _

class KeyboardDiagram(Gtk.Box):
    def __init__(self,model=None,on_select=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        self.buttons={};self.on_select=on_select;self.selected=None
        if model=='ace68':
            from ace68_adapter import LAYOUT
            from ace68_protocol import KEY_INDICES
            ids=iter(KEY_INDICES)
            for labels in LAYOUT:
                row=Gtk.Box(spacing=3,homogeneous=False)
                for label in labels:
                    index=str(next(ids));button=Gtk.Button(label=label,hexpand=True,tooltip_text=label)
                    button.set_size_request(70 if label=='Space' else 30,-1)
                    button.connect('clicked',lambda unused,k=index:self.select(k));self.buttons[index]=button;row.append(button)
                self.append(row)
            return
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

    def select(self,index):
        if self.selected in self.buttons:self.buttons[self.selected].remove_css_class('suggested-action')
        self.selected=index
        if index in self.buttons:self.buttons[index].add_css_class('suggested-action')
        if self.on_select:self.on_select(index)


KEY_LABELS={'actuation':'Точка срабатывания, мм','rapid_trigger':'Режим Rapid Trigger','rt_press':'RT при нажатии, мм','rt_release':'RT при отпускании, мм','press_dead_zone':'Верхняя мёртвая зона, мм','release_dead_zone':'Нижняя мёртвая зона, мм'}

class MagneticKeyboardEditor(Gtk.Box):
    """Shared diagram + parameter-driven selected-key editor, no key capture."""
    def __init__(self,center,device):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=12)
        self.center=center;self.device=device
        self.caps={c.name:c for c in device.capabilities if c.backend=='mchose-ace68'}
        self.profile=self.caps.get('profiles').value if self.caps.get('profiles') else '?'
        self.diagram=KeyboardDiagram('ace68',self.edit_key);self.append(self.diagram)
        self.form=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);self.append(self.form)
        if not hasattr(center,'ace_selected'):center.ace_selected={}
        self.diagram.select(center.ace_selected.get(device.id,'50'))
    def edit_key(self,index):
        from gi.repository import Adw
        from ace68_protocol import validate_key_value
        import math
        self.center.ace_selected[self.device.id]=index
        while self.form.get_first_child():self.form.remove(self.form.get_first_child())
        name=self.diagram.buttons[index].get_label()
        title=Gtk.Label(label=name+' · '+_('Встроенный профиль')+' '+str(self.profile),xalign=0);title.add_css_class('title-3');self.form.append(title)
        if not all(k in self.caps for k in KEY_LABELS):
            self.form.append(Gtk.Label(label=_('Параметры клавиш не прочитаны. Проверь доступ и диагностику устройства.'),wrap=True));return
        details=self.caps['key_details'].value[index];self.controls={};keys=[]
        for field,label in KEY_LABELS.items():
            cap=self.caps[field];actual=cap.value[index]
            row=Gtk.Box(spacing=12);text=Gtk.Label(label=_(label)+' · '+_('Текущее значение: ')+str(actual),xalign=0,hexpand=True,wrap=True);row.append(text)
            key='ace68:'+self.device.id+':profile:'+str(self.profile)+':key:'+index+':'+field;keys.append(key)
            if field=='rapid_trigger':
                widget=Gtk.DropDown.new_from_strings([_('Выключено'),'Rapid Trigger',_('Непрерывный RT')]);getter=widget.get_selected;setter=widget.set_selected;signal='notify::selected'
            else:
                base=details['press_base' if field=='rt_press' else 'release_base'] if field in ['rt_press','rt_release'] else 100
                low,high=(.1,3.3) if field=='actuation' else (0,.5) if field.endswith('dead_zone') else (2/base,min(3.3,500/base))
                widget=Gtk.SpinButton.new_with_range(low,high,1/base);widget.set_digits(3 if base==200 else 2)
                getter=lambda w=widget:round(w.get_value(),3);setter=widget.set_value;signal='value-changed'
            self.center.bind_draft(widget,key,actual,getter,setter,signal);widget.set_sensitive(cap.writable)
            row.append(widget);self.form.append(row);self.controls[field]=(getter,key,actual)
        buttons=Gtk.Box(spacing=12,halign=Gtk.Align.END);self.form.append(buttons)
        cancel=Gtk.Button(label=_('Отменить черновик'))
        def reset(*unused):
            for key in keys:self.center.draft_store.discard(key)
            self.edit_key(index)
        cancel.connect('clicked',reset);buttons.append(cancel)
        apply=Gtk.Button(label=_('Применить к выбранной клавише'),sensitive=all(self.caps[f].writable for f in KEY_LABELS));apply.add_css_class('suggested-action');buttons.append(apply)
        def submit(*unused):
            try:
                plans=[];submitted=[]
                current_profile=next(c.value for d in self.center.device_manager.devices if d.id==self.device.id for c in d.capabilities if c.backend=='mchose-ace68' and c.name=='profiles')
                if current_profile!=self.profile:raise ValueError('Profile changed; reload before applying this draft')
                for field,(get,key,actual) in self.controls.items():
                    value=get()
                    if value==actual:continue
                    validate_key_value({'key_details':{index:details}},field,index,value)
                    cap=self.center.device_manager.route(self.device.id,field,'mchose-ace68')
                    plans.append(cap.plan({index:value}));submitted.append(key)
                if plans:self.center.submit_drafts(submitted,lambda:self.center.apply_batch([p.command for p in plans],verified_plans=plans,after=lambda results:self.center.refresh(force=False)))
            except Exception as error:self.center.present_fault(error)
        apply.connect('clicked',submit)
