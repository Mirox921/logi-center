#!/usr/bin/env python3
import concurrent.futures, subprocess, re, json, sys
from pathlib import Path
import gi
gi.require_version('Gtk','4.0');gi.require_version('Adw','1')
from gi.repository import Gtk, Adw, GLib, Gio, Gdk
from i18n import tr as _, set_language
from backend import run, mouse_list, solaar_settings, audio_devices, volume, wireless_batteries, battery_label, load_preferences, save_preferences, saved_keyboard, import_preset, keyboard_online, keyboard_saved_settings
POOL=concurrent.futures.ThreadPoolExecutor(max_workers=1)

class Center(Adw.Application):
    def __init__(self):
        super().__init__(application_id='local.mirox.LogiCenter')
        self.keyboard_connected=None
        self.keyboard_polling=False
        self.preferences=load_preferences()
        set_language(self.preferences.get('language','ru'))
        self.connect('activate',self.activate)
    def activate(self,*unused):
        if hasattr(self,'win'):self.win.present();return
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        self.win=Adw.ApplicationWindow(application=self,title='Logi Center',default_width=1000,default_height=780)
        self.toast=Adw.ToastOverlay();self.win.set_content(self.toast)
        layout=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);self.toast.set_child(layout)
        header=Adw.HeaderBar();header.set_title_widget(Adw.WindowTitle(title='Logi Center',subtitle=_('Твои устройства · один центр управления')))
        refresh=Gtk.Button(icon_name='view-refresh-symbolic',tooltip_text=_('Обновить устройства'));refresh.connect('clicked',lambda *unused:self.refresh());header.pack_end(refresh)
        languages=Gtk.DropDown.new_from_strings(['Русский','English']);languages.set_tooltip_text('Язык / Language')
        languages.set_selected(1 if self.preferences.get('language','ru')=='en' else 0)
        languages.connect('notify::selected',self.change_language)
        header.pack_start(languages);layout.append(header)
        self.stack=Adw.ViewStack();switcher=Adw.ViewSwitcherBar(stack=self.stack,reveal=True);layout.append(switcher)
        self.pages={}
        for key,title,icon in [('mouse','G305','input-mouse-symbolic'),('keyboard','G515','input-keyboard-symbolic'),('audio','G Pro X','audio-headphones-symbolic')]:
            box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=20,margin_top=24,margin_bottom=24,margin_start=32,margin_end=32)
            clamp=Adw.Clamp(maximum_size=860);clamp.set_child(box)
            scroll=Gtk.ScrolledWindow(vexpand=True);scroll.set_child(clamp)
            self.stack.add_titled_with_icon(scroll,key,title,icon);self.pages[key]=box
        battery_box=Gtk.Box(spacing=24,halign=Gtk.Align.CENTER,margin_top=10,margin_bottom=12)
        self.battery_widgets={}
        for model,title in [('G305',_('Мышь G305')),('G515',_('Клавиатура G515'))]:
            box=Gtk.Box(spacing=8)
            icon=Gtk.Image.new_from_icon_name('battery-missing-symbolic');icon.set_pixel_size(24)
            label=Gtk.Label(label=title+_(' · Проверка заряда…'))
            box.append(icon);box.append(label);battery_box.append(box)
            self.battery_widgets[model]=(label,icon)
        layout.append(battery_box)
        self.update_batteries()
        self.battery_timer=GLib.timeout_add_seconds(30,self.poll_keyboard)
        layout.append(self.stack)
        if '--keyboard' in sys.argv:self.stack.set_visible_child_name('keyboard')
        if '--audio' in sys.argv:self.stack.set_visible_child_name('audio')
        self.status=Gtk.Label(label=_('Чтение устройств…'),margin_bottom=12,wrap=True);layout.append(self.status)
        self.refresh();self.win.present()
        if '--smoke' in sys.argv:GLib.timeout_add_seconds(12,lambda:(self.quit(),False)[1])
    def change_language(self,dropdown,param):
        language=['ru','en'][dropdown.get_selected()]
        if language==self.preferences.get('language','ru'):return
        self.preferences['language']=language;save_preferences(self.preferences);set_language(language)
        if hasattr(self,'battery_timer'):GLib.source_remove(self.battery_timer)
        old_window=self.win
        page=self.stack.get_visible_child_name()
        del self.win
        self.activate()
        self.stack.set_visible_child_name(page)
        old_window.destroy()
    def job(self,fn,done=None):
        self.status.set_label(_('Выполняется…'))
        future=POOL.submit(fn)
        def finish(f):
            try: value=f.result();error=None
            except Exception as exc:value=None;error=str(exc)
            def deliver():
                if error:
                    print(error,file=sys.stderr)
                    self.status.set_label(_('Не удалось выполнить действие. Проверь подключение устройства.'))
                    self.toast.add_toast(Adw.Toast(title=_('Настройка не применена. Проверь подключение и попробуй ещё раз.')))
                else:
                    self.status.set_label(_('Готово'))
                    if done:done(value)
                return False
            GLib.idle_add(deliver)
        future.add_done_callback(finish)
    def apply(self,args):
        def write():
            result=run(args)
            if args[0]=='headsetcontrol' and '-s' in args:self.preferences['sidetone']=args[-1]
            if args[0]=='easyeffects' and '-l' in args:self.preferences['preset']=args[-1]
            save_preferences(self.preferences)
            return result
        self.job(write,lambda text:self.toast.add_toast(Adw.Toast(title=_('Настройка применена'))))

    def group(self,page,title,description=None):
        g=Adw.PreferencesGroup(title=title,description=description);self.pages[page].append(g);return g
    def row(self,g,title,subtitle=''):
        r=Adw.ActionRow(title=GLib.markup_escape_text(title),subtitle=GLib.markup_escape_text(subtitle));r.set_subtitle_lines(3);g.add(r);return r
    def button(self,row,label,callback):
        b=Gtk.Button(label=label,valign=Gtk.Align.CENTER);b.connect('clicked',callback);row.add_suffix(b);return b
    def choice(self,g,title,items,current,callback,subtitle=''):
        row=self.row(g,title,subtitle);combo=Gtk.DropDown.new_from_strings([str(x) for x in items]);combo.set_valign(Gtk.Align.CENTER)
        if str(current) in [str(x) for x in items]:combo.set_selected([str(x) for x in items].index(str(current)))
        row.add_suffix(combo);self.button(row,_('Применить'),lambda *unused:callback(str(items[combo.get_selected()])))
    def launch(self,command):
        try:subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except OSError as e:self.toast.add_toast(Adw.Toast(title=str(e)))
    def choose_preset(self,*unused):
        dialog=Gtk.FileDialog(title=_('Импортировать готовый эффект'))
        filter=Gtk.FileFilter();filter.set_name(_('Пресеты EasyEffects (*.json)'));filter.add_pattern('*.json');filter.add_pattern('*.JSON')
        filters=Gio.ListStore.new(Gtk.FileFilter);filters.append(filter);dialog.set_filters(filters)
        def selected(dialog,result):
            try:
                file=dialog.open_finish(result)
                path=file.get_path()
                if not path:
                    self.toast.add_toast(Adw.Toast(title=_('Сначала скачай файл на компьютер.')));return
            except GLib.Error:return
            def install():
                try:return import_preset(path),None
                except (ValueError,OSError) as error:return None,str(error)
            def completed(outcome):
                value,error=outcome
                if error:
                    self.toast.add_toast(Adw.Toast(title=_('Не удалось импортировать: ')+_(error)[:180]));return
                name,kinds=value
                self.preferences['preset']=name;save_preferences(self.preferences)
                self.refresh()
                self.toast.add_toast(Adw.Toast(title=_('Эффект добавлен: ')+name+_('. Выбери его и нажми «Применить».')))
            self.job(install,completed)
        dialog.open(self.win,None,selected)
    def poll_keyboard(self):
        if self.keyboard_polling:return True
        self.keyboard_polling=True
        future=POOL.submit(keyboard_online)
        def finish(f):
            try:connected=f.result()
            except Exception:connected=None
            def deliver():
                self.keyboard_connected=connected;self.keyboard_polling=False
                self.update_batteries()
                return False
            GLib.idle_add(deliver)
        future.add_done_callback(finish)
        return True
    def update_batteries(self):
        batteries=wireless_batteries()
        for model,(label,icon) in self.battery_widgets.items():
            battery=next((b for b in batteries if model.lower() in b['model'].lower()),None)
            text,image=battery_label(battery)
            text=_(text)
            if model=='G515':
                if self.keyboard_connected is False:text,image=_('Не в сети'),'battery-missing-symbolic'
                elif self.keyboard_connected is None:text,image=_('Связь не подтверждена'),'battery-missing-symbolic'
            label.set_text((_('Мышь ') if model=='G305' else _('Клавиатура '))+model+' · '+text)
            icon.set_from_icon_name(image)
            label.set_tooltip_text(_('Обновляется каждые 30 секунд. ')+(_('Мышь сообщает уровень заряда без точного процента.') if battery and battery['percent'] is None else _('Показание устройства.')))
        return True
    def refresh(self):
        self.update_batteries()
        for box in self.pages.values():
            while box.get_first_child():box.remove(box.get_first_child())
        self.group('mouse',_('Поиск мыши…'));self.group('keyboard',_('Поиск клавиатуры…'));self.group('audio',_('Чтение аудиоустройств…'))
        def collect():
            data={}
            for key,args in [('mice',['ratbagctl','list']),('headset',['headsetcontrol','-o','json']),('sinks',['pactl','-f','json','list','sinks']),('sources',['pactl','-f','json','list','sources'])]:
                try:data[key]=run(args,40)
                except Exception as e:data[key+'_error']=str(e)
            data['keyboard_online']=keyboard_online()
            return data
        self.job(collect,self.populate)
    def clear(self,key):
        b=self.pages[key]
        while b.get_first_child():b.remove(b.get_first_child())
    def populate(self,data):
        self.clear('mouse');self.clear('keyboard');self.clear('audio')
        mice=mouse_list(data.get('mice',''))
        g=self.group('mouse','Logitech G305',_('Настрой скорость движения указателя, плавность и действия кнопок.'))
        if mice:
            for device,name in mice:
                row=self.row(g,name,_('Подключена'));self.button(row,_('Прочитать настройки'),lambda *unused,d=device:self.job(lambda:run(['ratbagctl',d,'info']),lambda text,d=d:self.mouse_controls(d,text)))
            self.job(lambda:run(['ratbagctl',mice[0][0],'info']),lambda text:self.mouse_controls(mice[0][0],text))
        else:self.row(g,_('Мышь недоступна'),_('Включи мышь и подключи USB-приёмник.'))
        row=self.row(g,_('Расширенный редактор'),_('Полный интерфейс Piper: профили и макросы.'));self.button(row,_('Открыть Piper'),lambda *unused:self.launch(['piper']))
        kg=self.group('keyboard','Logitech G515 Lightspeed TKL',_('Выбери яркость, цвет и поведение подсветки.'))
        self.keyboard_connected=data.get('keyboard_online')
        self.update_batteries()
        settings=keyboard_saved_settings()
        if self.keyboard_connected is not True:
            self.row(kg,_('Клавиатура не в сети') if self.keyboard_connected is False else _('Не удалось проверить связь'),_('Сохранённые настройки доступны для просмотра. Включи клавиатуру и обнови список.'))
        saved=saved_keyboard()
        for setting in settings:
            previous=saved.get(setting['key'])
            if isinstance(previous,str) and setting['key'] not in ['rgb_idle_timeout','rgb_sleep_timeout']:setting['value']=previous.capitalize() if previous.lower() in ['true','false'] else previous
        if not settings:self.row(kg,_('Настройки недоступны'),_('Подключи клавиатуру и нажми кнопку обновления вверху окна.'))
        labels={'rgb_control':_('Управление подсветкой из приложения'),
                'rgb_idle_timeout':_('Приглушать подсветку при бездействии'),
                'rgb_sleep_timeout':_('Выключать подсветку при бездействии')}
        translations={'true':_('Включено'),'false':_('Выключено'),'Disabled':_('Никогда'),
                      '15 Seconds':_('Через 15 секунд'),'30 Seconds':_('Через 30 секунд'),
                      '1 Minute':_('Через минуту'),'2 Minutes':_('Через 2 минуты'),
                      '5 Minutes':_('Через 5 минут'),'10 Minutes':_('Через 10 минут'),
                      '15 Minutes':_('Через 15 минут'),'30 Minutes':_('Через 30 минут')}
        for setting in settings:
            key=setting['key']
            if setting['choices'] and key in labels:
                values=setting['choices'];display=[translations.get(v,v) for v in values]
                current=setting['value'].lower() if values==['true','false'] else setting['value']
                current=translations.get(current,current)
                mapping=dict(zip(display,values))
                self.choice(kg,labels[key],display,current,
                    lambda value,k=key,m=mapping:self.apply(['solaar','config','G515',k,m[value]]))
            elif key=='brightness_control':
                values=[_('Выключена'),'12%','25%','50%','100%']
                mapping=dict(zip(values,['0','12','25','50','100']))
                current=next((k for k,v in mapping.items() if v==setting['value']),'100%')
                self.choice(kg,_('Яркость подсветки'),values,current,
                    lambda value,m=mapping:self.apply(['solaar','config','G515','brightness_control',m[value]]))
        if any(x['key']=='rgb_zone_1' for x in settings):
            r=self.row(kg,_('Режим подсветки'),_('Выбери эффект и цвет, затем нажми «Применить».'))
            modes=Gtk.DropDown.new_from_strings([_('Статичный цвет'),_('Дыхание'),_('Цикл цветов'),_('Выключено')]);modes.set_valign(Gtk.Align.CENTER);r.add_suffix(modes)
            dialog=Gtk.ColorDialog(title=_('Выбери цвет подсветки'));dialog.set_with_alpha(False)
            color=Gtk.ColorDialogButton(dialog=dialog,valign=Gtk.Align.CENTER,tooltip_text=_('Выбрать любой цвет'))
            previous=saved.get('rgb_zone_1',{})
            if not isinstance(previous,dict):previous={}
            try:
                last_mode=int(previous.get('ID',self.preferences.get('light_effect',1)))
                last_color=int(str(previous.get('color',self.preferences.get('light_color','0x44aaff'))),0)
            except (ValueError,TypeError):last_mode=1;last_color=0x44aaff
            if last_mode in [1,10,21,0]:modes.set_selected([1,10,21,0].index(last_mode))
            initial=Gdk.RGBA();initial.parse(f'#{last_color:06x}');color.set_rgba(initial);r.add_suffix(color)
            palette=Gtk.Box(spacing=8,halign=Gtk.Align.CENTER,margin_top=8,margin_bottom=8)
            palette.set_accessible_role(Gtk.AccessibleRole.GROUP)
            for label,code in [(_('Белый'),'#ffffff'),(_('Красный'),'#ff3030'),(_('Оранжевый'),'#ff9500'),(_('Жёлтый'),'#ffdc00'),(_('Зелёный'),'#30d158'),(_('Голубой'),'#44aaff'),(_('Синий'),'#304ffe'),(_('Фиолетовый'),'#bf5af2'),(_('Розовый'),'#ff4f9a')]:
                rgba=Gdk.RGBA();rgba.parse(code)
                swatch=Gtk.DrawingArea(content_width=30,content_height=30)
                def paint(area,ctx,w,h,c=rgba):
                    ctx.set_source_rgba(c.red,c.green,c.blue,1);ctx.arc(w/2,h/2,min(w,h)/2-2,0,6.2832);ctx.fill()
                swatch.set_draw_func(paint)
                b=Gtk.Button(child=swatch,tooltip_text=label)
                b.update_property([Gtk.AccessibleProperty.LABEL],[label])
                b.connect('clicked',lambda *unused,c=rgba:color.set_rgba(c));palette.append(b)
            kg.add(palette)
            def color_sensitivity(*unused):color.set_sensitive(modes.get_selected() in [0,1]);palette.set_sensitive(modes.get_selected() in [0,1])
            modes.connect('notify::selected',color_sensitivity)
            color_sensitivity()
            def light(*unused):
                rgba=color.get_rgba()
                hexcolor=''.join(f'{round(c*255):02x}' for c in [rgba.red,rgba.green,rgba.blue])
                effect=[1,10,21,0][modes.get_selected()]
                value='!LEDEffectSetting {ID: '+str(effect)+', color: 0x'+hexcolor+', period: 3000, intensity: 100}'
                def write():
                    run(['solaar','config','G515','rgb_control','true'])
                    result=run(['solaar','config','G515','rgb_zone_1',value])
                    self.preferences.update(light_effect=effect,light_color='0x'+hexcolor)
                    save_preferences(self.preferences)
                    return result
                self.job(write,lambda text:self.toast.add_toast(Adw.Toast(title=_('Подсветка применена'))))
            self.button(r,_('Применить'),light)
        kg.set_sensitive(self.keyboard_connected is True)
        row=self.row(kg,_('Все настройки клавиатуры'),_('Цвета по клавишам и сложные параметры пока редактируются в Solaar.'));self.button(row,_('Открыть Solaar'),lambda *unused:self.launch(['solaar','--window=show']))
        ag=self.group('audio',_('Звук и микрофон'),_('Выбери USB-карту G Pro X. Уровни применяются только по кнопке; выше 100% усиление не задаётся.'))
        found=False
        for kind,title,cmd in [('sinks',_('Выход'),'sink'),('sources',_('Микрофон'),'source')]:
            try:devices=json.loads(data.get(kind,'[]'))
            except ValueError:devices=[]
            for d in devices:
                name=d['name']
                if name.endswith('.monitor') or name.startswith('easyeffects_'):continue
                if any(x in (name+' '+d.get('description','')).lower() for x in ['logitech','pro_x','pro x']):found=True
                description=d.get('description',_('Аудиоустройство'))
                if any(x in (name+' '+description).lower() for x in ['logitech','pro_x','pro x']):description='Logitech G Pro X'
                elif 'HDMI' in description:description=_('Монитор или телевизор (HDMI)')
                elif 'Speaker' in description:description=_('Динамики ноутбука')
                elif 'Mic' in description:description=_('Встроенный микрофон')
                r=self.row(ag,title+': '+description,_('Уровень громкости, %'))
                spin=Gtk.SpinButton.new_with_range(0,100,1);spin.set_value(min(100,volume(d)));spin.set_valign(Gtk.Align.CENTER);r.add_suffix(spin)
                self.button(r,_('Громкость'),lambda *unused,s=spin,n=name,c=cmd:self.apply(['pactl','set-'+c+'-volume',n,str(s.get_value_as_int())+'%']))
                self.button(r,_('По умолчанию'),lambda *unused,n=name,c=cmd:self.apply(['pactl','set-default-'+c,n]))
                self.button(r,_('Вкл. микр.') if d.get('mute') and cmd=='source' else (_('Включить') if d.get('mute') else _('Заглушить')),lambda *unused,n=name,c=cmd,m=d.get('mute'):self.apply(['pactl','set-'+c+'-mute',n,'0' if m else '1']))
        if not found:self.row(ag,_('USB-карта G Pro X пока не обнаружена'),_('Общие аудиоустройства доступны выше. Подключи карту и обнови список.'))
        effects=self.group('audio',_('Обработка звука'),_('Собственные пресеты EasyEffects можно включать отсюда. Редактирование цепочки эффектов открывается в его редакторе.'))
        r=self.row(effects,_('Готовые эффекты сообщества'),_('Настройки для микрофона и наушников. Откроются в браузере.'))
        self.button(r,_('Найти готовые эффекты'),lambda *unused:self.launch(['xdg-open','https://github.com/wwmm/easyeffects/wiki/Community-Presets']))
        r=self.row(effects,_('Добавить скачанный эффект'),_('Выбери файл .json для микрофона или наушников. Затем выбери его в списке ниже.'))
        self.button(r,_('Импортировать эффект'),self.choose_preset)
        preset_dir=Path.home()/'.config/easyeffects'
        presets=sorted({p.stem for folder in ['input','output'] for p in (preset_dir/folder).glob('*.json')})
        if presets:self.choice(effects,_('Пресет'),presets,self.preferences.get('preset',presets[0]),lambda name:self.apply(['easyeffects','-l',name]))
        else:self.row(effects,_('Пресетов пока нет'),_('Создай эквалайзер или обработку микрофона в редакторе EasyEffects.'))
        r=self.row(effects,_('Эквалайзер и обработка микрофона'));self.button(r,_('Редактор эффектов'),lambda *unused:self.launch(['easyeffects']))
        r=self.row(effects,_('Звуковые эффекты'),_('Эквалайзер и фильтры для наушников и микрофона. Без эффектов звук продолжает работать.'));self.button(r,_('С эффектами'),lambda *unused:self.apply(['easyeffects','-b','2']));self.button(r,_('Без эффектов'),lambda *unused:self.apply(['easyeffects','-b','1']))
        try:headsets=json.loads(data.get('headset','{}')).get('devices',[])
        except ValueError:headsets=[]
        for h in headsets:
            r=self.row(ag,h.get('device',_('Гарнитура')),_('USB-карта подключена · можно настроить слышимость своего голоса') if h.get('product')=='PRO X' else ', '.join(h.get('capabilities_str',[])))
            if 'CAP_SIDETONE' in h.get('capabilities',[]):
                identifier=h.get('id_vendor','')+':'+h.get('id_product','')
                levels={_('Выключено'):'0',_('Очень тихо'):'16',_('Тихо'):'32',_('Средне'):'64',_('Громко'):'96',_('Максимально'):'128'}
                self.choice(ag,_('Слышимость своего голоса'),list(levels),next((k for k,v in levels.items() if v==self.preferences.get('sidetone')),_('Выключено')),lambda value,i=identifier,m=levels:self.apply(['headsetcontrol','-d',i,'-s',m[value]]),_('Выбери желаемый уровень и нажми «Применить». Показан последний сохранённый выбор; текущее значение устройство не сообщает.'))
    def mouse_controls(self,device,text):
        if hasattr(self,'mouse_extra') and self.mouse_extra.get_parent():self.mouse_extra.get_parent().remove(self.mouse_extra)
        g=self.group('mouse',_('Настройки мыши'));self.mouse_extra=g
        self.row(g,_('Мышь подключена'),_('Настройки прочитаны. Изменения сохраняются по кнопке «Применить».'))
        dpi=re.search(r'^\s*\d+: (\d+)dpi.*\(active\)',text,re.M)
        self.choice(g,_('Чувствительность DPI'),[200,400,600,800,1000,1200,1600,2400,3200,6400,12000],dpi[1] if dpi else 800,lambda v:self.apply(['ratbagctl',device,'dpi','set',v]))
        rate=re.search(r'Report Rate: (\d+)Hz',text)
        self.choice(g,_('Частота опроса, Гц'),[125,250,500,1000],rate[1] if rate else 1000,lambda v:self.apply(['ratbagctl',device,'rate','set',v]))
        names={'0':_('Левая кнопка'),'1':_('Правая кнопка'),'2':_('Нажатие колёсика'),
               '3':_('Боковая кнопка «Назад»'),'4':_('Боковая кнопка «Вперёд»'),'5':_('Кнопка переключения чувствительности')}
        actions={_('Левый щелчок'):['button','1'],_('Правый щелчок'):['button','2'],
                 _('Нажатие колёсика'):['button','3'],_('Назад'):['button','4'],_('Вперёд'):['button','5'],
                 _('Переключать чувствительность'):['special','resolution-cycle-up'],
                 _('Копировать'):['macro','+KEY_LEFTCTRL','KEY_C','-KEY_LEFTCTRL'],
                 _('Вставить'):['macro','+KEY_LEFTCTRL','KEY_V','-KEY_LEFTCTRL'],
                 _('Вырезать'):['macro','+KEY_LEFTCTRL','KEY_X','-KEY_LEFTCTRL'],
                 _('Отменить'):['macro','+KEY_LEFTCTRL','KEY_Z','-KEY_LEFTCTRL'],
                 _('Выделить всё'):['macro','+KEY_LEFTCTRL','KEY_A','-KEY_LEFTCTRL'],
                 **{(_(_('Клавиша F'))+str(i)):['key',f'KEY_F{i}'] for i in range(1,13)},
                 _('Отключить кнопку'):['disabled']}
        descriptions={'button 1':_('Левый щелчок'),'button 2':_('Правый щелчок'),'button 3':_('Нажатие колёсика'),
                      'button 4':_('Назад'),'button 5':_('Вперёд'),'resolution-cycle-up':_('Переключать чувствительность')}
        for index,action in re.findall(r"Button: (\d+) is mapped to '([^']+)'",text):
            current=descriptions.get(action,'')
            options=list(actions) if current else [_('Не изменять')]+list(actions)
            def set_action(value,i=index):
                if value==_('Не изменять'):return
                self.apply(['ratbagctl',device,'button',i,'action','set',*actions[value]])
            self.choice(g,names.get(index,_('Дополнительная кнопка')),options,current or _('Не изменять'),set_action,
                        _('Сейчас: ')+(current or _('Собственное назначение')))

if __name__=='__main__':Center().run([sys.argv[0]])
