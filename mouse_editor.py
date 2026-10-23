"""GTK model-aware mouse diagram and an opt-in keyboard/macro draft editor."""
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gtk,Gdk
from mouse_art import render as render_mouse,callouts,WIDTH,HEIGHT
from mouse_models import layout,linux_key,friendly,conflicts,MacroDraft,assignment_label,action_allowed
from operations import macro_tokens,read_action,same
from i18n import tr as _

class MouseEditor(Gtk.Box):
    def __init__(self,name,buttons,actions,types,on_apply,state=None,on_draft=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=12)
        self.buttons={b['index']:b for b in buttons};self.actions=actions;self.types=types;self.on_apply=on_apply;self.selected=None;self.recording=False
        self.drafts={};self.widgets={};self.choices={};self.on_draft=on_draft;self.loading=True
        self.append(Gtk.Label(label=_('Схема мыши: выбери кнопку. Изменения остаются черновиком до применения.'),wrap=True))
        self.model_name=name
        card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        card.add_css_class('logi-mouse-card')
        title=Gtk.Label(label=name,margin_top=18);title.add_css_class('heading');card.append(title)
        overlay=Gtk.Overlay(halign=Gtk.Align.CENTER)
        self.drawing=Gtk.DrawingArea(content_width=WIDTH,content_height=HEIGHT)
        self.drawing.set_draw_func(self.draw);overlay.set_child(self.drawing)
        click=Gtk.GestureClick();click.connect('pressed',self.diagram_clicked);self.drawing.add_controller(click)
        self.drawing.set_cursor_from_name('pointer')
        fixed=Gtk.Fixed(width_request=WIDTH,height_request=HEIGHT,halign=Gtk.Align.CENTER,valign=Gtk.Align.CENTER);overlay.add_overlay(fixed)
        for index,(x,y) in callouts(len(buttons)).items():
            button=Gtk.Button(label=str(index+1),width_request=36,height_request=36)
            button.add_css_class('logi-mouse-pin')
            button.set_tooltip_text(_('Кнопка ')+str(index+1))
            button.connect('clicked',lambda widget,i=index:self.select(i))
            fixed.put(button,x-18,y-18);self.widgets[index]=button
        card.append(overlay)
        note=Gtk.Label(label=_('Схема расположения кнопок · не отображает текущий цвет подсветки'),wrap=True,margin_bottom=16)
        note.add_css_class('dim-label');note.add_css_class('caption');card.append(note)
        style=Gtk.CssProvider()
        style.load_from_data(b"""
        .logi-mouse-card { background: #141a22; border: 1px solid #303b48; border-radius: 20px; color: #e2e9f1; }
        .logi-mouse-pin { border-radius: 18px; padding: 0; min-width: 34px; min-height: 34px; background: #202b38; color: #bac9d8; border: 1px solid #445262; box-shadow: none; font-weight: 700; }
        .logi-mouse-pin:hover { background: #314658; color: white; border-color: #70cfdf; }
        .logi-mouse-pin.suggested-action { background: #143f50; border-color: #63d8ef; color: #b4f2ff; box-shadow: 0 0 0 3px alpha(#63d8ef, 0.12); }
        """)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),style,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.append(card)
        self.current=Gtk.Label(wrap=True,selectable=True);self.append(self.current)
        self.options=[_('Собственный макрос'),*actions,_('Не изменять')]
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
        self.action.connect('notify::selected',self.choice_changed)
        if state and isinstance(state,dict):
            for key,tokens in state.get('tokens',{}).items():
                if str(key).isdigit() and int(key) in self.buttons and isinstance(tokens,list) and all(isinstance(t,str) for t in tokens):self.drafts[int(key)]=MacroDraft(tokens=tokens)
            self.choices={int(k):v for k,v in state.get('choices',{}).items() if str(k).isdigit() and int(k) in self.buttons}
        selected=state.get('selected') if isinstance(state,dict) else None
        if buttons:self.select(selected if selected in self.buttons else buttons[0]['index'])
        self.loading=False
    def draw(self,area,cr,width,height):
        render_mouse(cr,width,height,self.model_name,self.selected,len(self.buttons))
    def diagram_clicked(self,gesture,count,x,y):
        width=self.drawing.get_width();height=self.drawing.get_height()
        scale=min(width/WIDTH,height/HEIGHT)
        if scale<=0:return
        x=(x-(width-WIDTH*scale)/2)/scale;y=(y-(height-HEIGHT*scale)/2)/scale
        anchors=layout(self.model_name,len(self.buttons))
        if not anchors:return
        index=min(anchors,key=lambda i:(anchors[i][0]*WIDTH-x)**2+(anchors[i][1]*HEIGHT-y)**2)
        if (anchors[index][0]*WIDTH-x)**2+(anchors[index][1]*HEIGHT-y)**2<=24**2:self.select(index)
        elif 185<x<317 and 47<y<180:
            index=0 if x<249 else 1
            if index in self.buttons:self.select(index)
    def select(self,index):
        self.loading=True
        self.record.set_active(False);self.selected=index
        self.drawing.queue_draw()
        for i,widget in self.widgets.items():
            if i==index:widget.add_css_class('suggested-action')
            else:widget.remove_css_class('suggested-action')
        button=self.buttons[index]
        tokens=macro_tokens(button['action']) if button['macro'] else []
        if index not in self.drafts:self.drafts[index]=MacroDraft(tokens=list(tokens))
        known=assignment_label(button,self.actions)
        readable=known or (' → '.join(friendly(t) for t in tokens) if button['macro'] else _('Собственное назначение'))
        self.current.set_text(_('Кнопка ')+str(index+1)+' · '+_('Сейчас: ')+readable)
        previous=self.choices.get(index)
        option=(_('Не изменять') if previous==['unchanged'] else next((label for label,value in self.actions.items() if value==previous),self.options[0])) if index in self.choices else known or (self.options[0] if button['macro'] else _('Не изменять'))
        self.action.set_selected(self.options.index(option))
        supported=4 in self.types.get(index,[])
        self.record.set_sensitive(supported)
        self.warning.set_text('' if supported else _('Редактирование макросов не подтверждено backend для этой кнопки.'))
        self.render();self.loading=False
    def has_changes(self):
        for index,draft in self.drafts.items():
            button=self.buttons[index]
            if draft.tokens!=(macro_tokens(button['action']) if button['macro'] else []):return True
        for index,choice in self.choices.items():
            if choice is None or choice==['unchanged']:continue
            button=self.buttons[index];actual=read_action(('macro ' if button['macro'] else '')+button['action'])
            if not same(choice,actual):return True
        return False
    def state(self):
        return {"dirty":self.has_changes(),"selected":self.selected,"tokens":{str(i):d.tokens[:] for i,d in self.drafts.items()},"choices":{str(i):v for i,v in self.choices.items()}}
    def changed(self):
        if not self.loading and self.on_draft:self.on_draft(self.state())
    def choice_changed(self,*unused):
        if self.loading or self.selected is None:return
        choice=self.action.get_selected();self.choices[self.selected]=None if choice==0 else ['unchanged'] if self.options[choice]==_('Не изменять') else self.actions[self.options[choice]]
        self.changed()
    def render(self):
        while self.events.get_first_child():self.events.remove(self.events.get_first_child())
        for index,token in enumerate(self.drafts[self.selected].tokens):
            row=Gtk.Box(spacing=8);row.append(Gtk.Label(label=friendly(token),hexpand=True,xalign=0))
            delete=Gtk.Button(icon_name='edit-delete-symbolic');delete.connect('clicked',lambda *unused,i=index:self.remove(i));row.append(delete);self.events.append(row)
        self.changed()
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
    def reset(self):
        self.drafts.pop(self.selected,None);self.choices.pop(self.selected,None);self.select(self.selected);self.changed()
    def apply(self,*unused):
        self.record.set_active(False)
        choice=self.action.get_selected()
        if self.options[choice]==_('Не изменять'):return
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
        if not action_allowed(action,self.types.get(self.selected,[])):
            self.warning.set_text(_('Backend не подтвердил поддержку этого назначения для выбранной кнопки.'));return
        self.on_apply(self.selected,action)
