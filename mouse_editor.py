"""GTK model-aware mouse diagram and an opt-in keyboard/macro draft editor."""
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gtk,Gdk
from mouse_models import layout,linux_key,friendly,conflicts,MacroDraft
from operations import macro_tokens
from i18n import tr as _

class MouseEditor(Gtk.Box):
    def __init__(self,name,buttons,actions,types,on_apply):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=12)
        self.buttons={b['index']:b for b in buttons};self.actions=actions;self.types=types;self.on_apply=on_apply;self.selected=None;self.recording=False
        self.drafts={};self.widgets={}
        self.append(Gtk.Label(label=_('Схема мыши: выбери кнопку. Изменения остаются черновиком до применения.'),wrap=True))
        overlay=Gtk.Overlay();drawing=Gtk.DrawingArea(content_width=420,content_height=340);drawing.set_draw_func(self.draw);overlay.set_child(drawing)
        fixed=Gtk.Fixed(width_request=420,height_request=340,halign=Gtk.Align.CENTER,valign=Gtk.Align.CENTER);overlay.add_overlay(fixed)
        for index,(x,y) in layout(name,len(buttons)).items():
            button=Gtk.Button(label=str(index+1),width_request=38,height_request=32)
            button.connect('clicked',lambda widget,i=index:self.select(i));fixed.put(button,x*420-19,y*340-16);self.widgets[index]=button
        self.append(overlay)
        self.current=Gtk.Label(wrap=True,selectable=True);self.append(self.current)
        self.options=[_('Собственный макрос'),*actions]
        self.action=Gtk.DropDown.new_from_strings(self.options);self.append(self.action)
        tools=Gtk.Box(spacing=8)
        self.record=Gtk.ToggleButton(label=_('Записать клавиши'));self.record.connect('toggled',self.record_changed);tools.append(self.record)
        self.append(tools)
        self.events=Gtk.ListBox();scroll=Gtk.ScrolledWindow(min_content_height=120,max_content_height=240);scroll.set_child(self.events);self.append(scroll)
        delay=Gtk.SpinButton.new_with_range(1,10000,10);delay.set_value(100);tools.append(delay)
        add=Gtk.Button(label=_('Добавить паузу'));add.connect('clicked',lambda *unused:self.pause(delay.get_value_as_int()));tools.append(add)
        clear=Gtk.Button(label=_('Очистить'));clear.connect('clicked',lambda *unused:self.clear());tools.append(clear)
        self.warning=Gtk.Label(wrap=True);self.append(self.warning)
        commands=Gtk.Box(spacing=8,halign=Gtk.Align.END)
        undo=Gtk.Button(label=_('Отменить черновик'));undo.connect('clicked',lambda *unused:self.reset());commands.append(undo)
        apply=Gtk.Button(label=_('Применить'));apply.connect('clicked',self.apply);commands.append(apply);self.append(commands)
        keys=Gtk.EventControllerKey();keys.connect('key-pressed',self.key_pressed);keys.connect('key-released',self.key_released);self.add_controller(keys);self.set_focusable(True)
        if buttons:self.select(buttons[0]['index'])
    @staticmethod
    def draw(area,cr,width,height):
        cr.save();cr.translate(width/2-120,12);cr.scale(240/240,(height-24)/310)
        cr.set_source_rgb(.18,.20,.23);cr.move_to(45,15);cr.curve_to(65,-5,170,-5,195,20);cr.curve_to(225,55,245,230,210,280);cr.curve_to(170,322,60,322,27,275);cr.curve_to(-5,225,0,60,45,15);cr.close_path();cr.fill_preserve();cr.set_source_rgb(.5,.6,.7);cr.set_line_width(2);cr.stroke();cr.move_to(120,5);cr.line_to(120,110);cr.stroke();cr.restore()
    def select(self,index):
        self.record.set_active(False);self.selected=index
        for i,widget in self.widgets.items():
            if i==index:widget.add_css_class('suggested-action')
            else:widget.remove_css_class('suggested-action')
        button=self.buttons[index]
        tokens=macro_tokens(button['action']) if button['macro'] else []
        if index not in self.drafts:self.drafts[index]=MacroDraft(tokens=list(tokens))
        readable=' → '.join(friendly(t) for t in tokens) if button['macro'] else next((label for label,value in self.actions.items() if ' '.join(value[1:])==button['action']),_('Собственное назначение'))
        self.current.set_text(_('Кнопка ')+str(index+1)+' · '+_('Сейчас: ')+readable)
        option=next((label for label,value in self.actions.items() if not button['macro'] and ' '.join(value[1:])==button['action']),self.options[0])
        self.action.set_selected(self.options.index(option))
        supported=4 in self.types.get(index,[])
        self.record.set_sensitive(supported)
        self.warning.set_text('' if supported else _('Редактирование макросов не подтверждено backend для этой кнопки.'))
        self.render()
    def render(self):
        while self.events.get_first_child():self.events.remove(self.events.get_first_child())
        for index,token in enumerate(self.drafts[self.selected].tokens):
            row=Gtk.Box(spacing=8);row.append(Gtk.Label(label=friendly(token),hexpand=True,xalign=0))
            delete=Gtk.Button(icon_name='edit-delete-symbolic');delete.connect('clicked',lambda *unused,i=index:self.remove(i));row.append(delete);self.events.append(row)
    def record_changed(self,button):
        self.recording=button.get_active()
        button.set_label(_('Остановить запись клавиш') if self.recording else _('Записать клавиши'))
        if self.recording:
            self.action.set_selected(0);self.grab_focus();self.warning.set_text(_('Нажимай клавиши в этом окне. Системные сочетания могут перехватываться рабочим столом.'))
    def key_pressed(self,controller,keyval,keycode,state):
        if not self.recording:return False
        key=linux_key(Gdk.keyval_name(keyval) or '')
        if key:self.drafts[self.selected].press(key);self.render()
        else:self.warning.set_text(_('Эта клавиша пока не поддерживается редактором.'))
        return True
    def key_released(self,controller,keyval,keycode,state):
        if self.recording:self.drafts[self.selected].release(linux_key(Gdk.keyval_name(keyval) or ''));self.render()
    def pause(self,delay):self.drafts[self.selected].tokens.append('t'+str(delay));self.action.set_selected(0);self.render()
    def clear(self):self.drafts[self.selected]=MacroDraft();self.action.set_selected(0);self.render()
    def remove(self,index):self.drafts[self.selected].tokens.pop(index);self.render()
    def reset(self):self.drafts.pop(self.selected,None);self.select(self.selected)
    def apply(self,*unused):
        self.record.set_active(False)
        choice=self.action.get_selected()
        if choice==0:
            if 4 not in self.types.get(self.selected,[]):self.warning.set_text(_('Макросы для этой кнопки недоступны.'));return
            draft=self.drafts[self.selected]
            try:draft.validate()
            except ValueError as error:self.warning.set_text(str(error));return
            if conflicts(draft.tokens):
                self.warning.set_text(_('Сочетание может конфликтовать с рабочим столом. Нажми «Применить» повторно для подтверждения.'))
                if getattr(self,'last_warning',None)!=tuple(draft.tokens):self.last_warning=tuple(draft.tokens);return
            action=['macro',*draft.tokens]
        else:action=self.actions[self.options[choice]]
        self.on_apply(self.selected,action)
