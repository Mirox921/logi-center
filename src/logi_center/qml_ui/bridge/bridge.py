from concurrent.futures import ThreadPoolExecutor
from logi_center.resources import assets_dir as resource_assets
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer

from logi_center.core.devices.device_presentation import dashboard_devices, group_presentations, presentation, dashboard_inventory
from .models import DeviceListModel, CapabilityListModel


CAPABILITY_LABELS = {
    'battery_status': 'Аккумулятор', 'charging': 'Зарядка', 'dpi': 'DPI',
    'dpi_x': 'DPI по горизонтали', 'dpi_y': 'DPI по вертикали',
    'polling_rate': 'Частота опроса', 'buttons': 'Кнопки', 'macros': 'Макросы',
    'lighting': 'Подсветка', 'lighting_mode': 'Эффект подсветки', 'brightness': 'Яркость',
    'profiles': 'Профили', 'actuation': 'Точка срабатывания', 'rapid_trigger': 'Rapid Trigger',
    'volume': 'Уровень громкости', 'microphone_mute': 'Микрофон',
    'standard_input': 'Устройство ввода',
    'debounce': 'Задержка кнопок', 'sleep': 'Энергосбережение', 'stage': 'Ступень DPI',
    'dpi_stages': 'Ступени DPI', 'motion_sync': 'Motion Sync',
    'lighting_speed': 'Скорость эффекта', 'lighting_palette': 'Палитра подсветки',
    'rt_press': 'Чувствительность нажатия RT', 'rt_release': 'Чувствительность отпускания RT',
    'press_dead_zone': 'Мёртвая зона нажатия', 'release_dead_zone': 'Мёртвая зона отпускания',
    'brightness_control': 'Яркость', 'rgb_control': 'Подсветка',
    'rgb_idle_timeout': 'Отключение подсветки при бездействии', 'rgb_sleep_timeout': 'Задержка перехода в сон',
    'rgb_zone_1': 'Эффект подсветки',
}


class DeviceBridge(QObject):
    devicesChanged = Signal()
    selectedDeviceChanged = Signal()
    languageChanged = Signal()
    busyChanged = Signal()
    errorChanged = Signal()
    inventoryChanged = Signal()
    preferencesChanged = Signal()
    _motionReady = Signal(bool)
    _preferencesSaved = Signal(object)
    _batteryReady = Signal(object,object,object)
    _snapshotReady = Signal(object, object)
    _artworkReady = Signal(str, object, object)
    artworkPreviewReady = Signal(str, str, str)
    _hardwareEvent = Signal(str)

    def __init__(self, simulation=False, parent=None, assets_dir=None, persist_ui=True):
        super().__init__(parent)
        self.simulation = bool(simulation)
        self.devices = DeviceListModel(self)
        self.externalDevices = DeviceListModel(self)
        self.builtinDevices = DeviceListModel(self)
        self.audioDevices = DeviceListModel(self)
        self.otherDevices = DeviceListModel(self)
        self.capabilities = CapabilityListModel(self)
        self._selected_id = ''
        self._selected = None
        self._manager = None
        self._updated_at = ''
        from .preferences import load_preferences, DEFAULTS
        preferences = dict(DEFAULTS) if self.simulation else load_preferences()
        self._language = preferences['language']
        self._ui_scale=preferences['ui_scale'];self._initial_ui_scale=self._ui_scale
        from logi_center.i18n import set_language
        set_language(self._language)
        self._persist_ui = bool(persist_ui and not self.simulation)
        self._user_reduced_motion = preferences['reduced_motion']
        import os
        self._system_reduced_motion = os.environ.get('LOGI_CENTER_REDUCED_MOTION') == '1'
        self._preferences_error = ''
        self._busy = False
        self._error = ''
        self._refresh_pending = False
        self._closed = False
        self._show_builtin = preferences['show_builtin']
        from logi_center.core.discovery.discovery import Epoch
        self._battery_epoch = Epoch()
        self._battery_busy = False
        self._battery_timer = QTimer(self)
        self._battery_timer.setSingleShot(True)
        self._battery_timer.timeout.connect(self._poll_battery)
        self._batteryReady.connect(self._accept_battery)
        self._all_presentations = []
        self._selected_presentation = {}
        self._search = ''
        self._search_text = ''
        self._category = 'all'
        self._assets = Path(assets_dir) if assets_dir else resource_assets() / 'devices'
        from logi_center.core.devices.device_artwork import DeviceArtworkProvider
        self._art_temporary = None
        self._art_futures = set()
        if self.simulation:
            import tempfile
            self._art_temporary = tempfile.TemporaryDirectory(prefix='logi-art-simulation-')
            self._artwork = DeviceArtworkProvider(self._assets,
                data_dir=Path(self._art_temporary.name)/'images',
                preferences_file=Path(self._art_temporary.name)/'preferences.json')
        else:
            self._artwork = DeviceArtworkProvider(self._assets)
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='logi-discovery')
        self._preferences_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='logi-ui-preferences')
        self._motionReady.connect(self._accept_motion)
        self._preferencesSaved.connect(self._accept_preferences_save)
        if not self.simulation:
            from .preferences import system_reduced_motion
            future = self._preferences_pool.submit(system_reduced_motion)
            future.add_done_callback(lambda f:self._motionReady.emit(bool(f.result())) if not self._closed and not f.cancelled() else None)
        from .backups import BackupController
        self._backups = BackupController(self, self._pool, self.simulation)
        self._backups.completedRestore.connect(self.refresh)
        from .editor import EditorController
        self._editor = EditorController(self, self._pool, self.simulation)
        from .audio import AudioController
        self._audio = AudioController(self, self._pool, self.simulation)
        from .diagnostics import DiagnosticController
        self._diagnostics=DiagnosticController(self,self._pool)
        from logi_center.core.services.simulation import SimulationAdapter
        self._simulation_adapter = SimulationAdapter() if self.simulation else None
        self._snapshotReady.connect(self._accept_snapshot)
        self._artworkReady.connect(self._accept_artwork)
        self._hardwareEvent.connect(self._queue_hardware_refresh)
        self._event_timer = QTimer(self)
        self._event_timer.setSingleShot(True)
        self._event_timer.setInterval(180)
        self._event_timer.timeout.connect(self.refresh)
        self._monitor = None
        if not self.simulation:
            from logi_center.core.discovery.discovery import DeviceMonitor
            self._monitor = DeviceMonitor(lambda reason: self._hardwareEvent.emit(str(reason)))
            self._monitor.start()
        self.refresh()

    @Property(bool, notify=busyChanged)
    def busy(self): return self._busy

    @Property(bool, constant=True)
    def simulationMode(self): return self.simulation

    @Property(str, notify=errorChanged)
    def error(self): return self._error

    @Property(str, notify=selectedDeviceChanged)
    def selectedDeviceId(self): return self._selected_id

    @Property('QVariant', notify=selectedDeviceChanged)
    def selectedDevice(self):
        if not self._selected_id:
            return {}
        return next((row for row in self._all_presentations if row['deviceId'] == self._selected_id),
                    self._selected_presentation)

    @Property('QVariant', notify=languageChanged)
    def deviceModel(self): return self.devices

    @Property('QVariant', notify=devicesChanged)
    def externalDeviceModel(self): return self.externalDevices

    @Property('QVariant', notify=devicesChanged)
    def builtinDeviceModel(self): return self.builtinDevices

    @Property('QVariant', notify=devicesChanged)
    def audioDeviceModel(self): return self.audioDevices

    @Property('QVariant', notify=devicesChanged)
    def otherDeviceModel(self): return self.otherDevices

    @Property('QVariant', notify=selectedDeviceChanged)
    def capabilityModel(self): return self.capabilities

    @Property(str, notify=languageChanged)
    def language(self): return self._language

    @Property(bool, notify=devicesChanged)
    def showBuiltin(self): return self._show_builtin

    def _inventory(self):
        return dashboard_inventory(self._all_presentations,self._search,self._show_builtin,self._category)

    @Property('QVariantMap', notify=devicesChanged)
    def inventoryCounts(self):return self._inventory()['sections']

    @Property(int, notify=devicesChanged)
    def builtinFilterCount(self):return self._inventory()['builtin_available']

    @Property(str, notify=inventoryChanged)
    def updatedAt(self): return self._updated_at

    @Property(QObject, constant=True)
    def backups(self): return self._backups

    @Property('QVariant', constant=True)
    def editor(self): return self._editor

    @Property(QObject, constant=True)
    def audio(self): return self._audio

    @Property(QObject, constant=True)
    def diagnosticController(self): return self._diagnostics

    @Slot(str)
    def launchTool(self,name):
        commands={'easyeffects':['easyeffects'],'solaar':['solaar','--window=show'],'piper':['piper'],
                  'presets':['xdg-open','https://github.com/wwmm/easyeffects/wiki/Community-Presets']}
        if name not in commands or self.simulation:return
        def launch():
            import subprocess
            subprocess.Popen(commands[name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        future=self._preferences_pool.submit(launch)
        def complete(f):
            if f.exception() and not self._closed:self._preferencesSaved.emit(f.exception())
        future.add_done_callback(complete)

    @Property(str, notify=devicesChanged)
    def searchQuery(self): return self._search_text

    @Property(str, notify=devicesChanged)
    def categoryFilter(self): return self._category

    @Property('QVariantMap', notify=devicesChanged)
    def categoryCounts(self):
        return self._inventory()['tabs']

    @Property(bool, constant=True)
    def persistUi(self): return self._persist_ui

    @Property(bool, notify=preferencesChanged)
    def reducedMotion(self): return self._user_reduced_motion or self._system_reduced_motion

    @Property(bool, notify=preferencesChanged)
    def systemReducedMotion(self): return self._system_reduced_motion

    @Property(str, notify=preferencesChanged)
    def preferencesError(self): return self._preferences_error

    @Property(int,notify=preferencesChanged)
    def uiScale(self):return self._ui_scale

    @Property(bool,notify=preferencesChanged)
    def scaleRestartRequired(self):return self._ui_scale!=self._initial_ui_scale

    @Slot(int)
    def setUiScale(self,value):
        from .preferences import UI_SCALES
        if type(value) is not int or value not in UI_SCALES or value==self._ui_scale:return
        self._ui_scale=value;self.preferencesChanged.emit();self._save_preferences()

    @Slot(bool)
    def setReducedMotion(self, enabled):
        self._user_reduced_motion = bool(enabled)
        self.preferencesChanged.emit()
        self._save_preferences()

    @Slot(bool)
    def _accept_motion(self, reduced):
        if self._closed: return
        self._system_reduced_motion = reduced
        self.preferencesChanged.emit()

    def _save_preferences(self):
        if not self._persist_ui or self._closed: return
        from .preferences import save_preferences
        data = {'language':self._language, 'show_builtin':self._show_builtin, 'reduced_motion':self._user_reduced_motion,'ui_scale':self._ui_scale}
        future = self._preferences_pool.submit(save_preferences, data)
        def done(f):
            if self._closed: return
            try: self._preferencesSaved.emit(f.exception())
            except RuntimeError: pass
        future.add_done_callback(done)

    @Slot(object)
    def _accept_preferences_save(self, error):
        if self._closed: return
        self._preferences_error = self.tr('Не удалось сохранить настройки интерфейса.') if error else ''
        self.preferencesChanged.emit()

    @Slot()
    def refresh(self):
        if self._closed:
            return
        if self._busy:
            self._refresh_pending = True
            return
        if self._editor.busy or self._audio.busy or self._backups.busy:
            self._refresh_pending=True;self._event_timer.start(300);return
        self._battery_epoch.invalidate()
        self._refresh_pending = False
        self._busy = True
        self.busyChanged.emit()
        from logi_center.core.discovery.device_service import collect_device_snapshot
        future = self._pool.submit(collect_device_snapshot, self.simulation, self._simulation_adapter)
        future.add_done_callback(lambda f: self._snapshotReady.emit(f.result() if not f.exception() else None,
                                                                     f.exception()))

    @Slot(str)
    def _queue_hardware_refresh(self, reason):
        if reason == 'devices':
            self._backups.invalidate()
            self._editor.invalidate()
            self._audio.invalidate()
            self._diagnostics.invalidate()
            self._battery_epoch.invalidate()
        if reason == 'battery' and not self.simulation:
            self._battery_timer.start(0)
        elif reason in ('devices','audio-state'):
            self._event_timer.start()

    @Slot()
    def _poll_battery(self):
        if self._closed or self.simulation:return
        if self._busy or self._battery_busy or self._backups.busy or self._editor.busy or not self._manager:
            self._battery_timer.start(1000);return
        from logi_center.core.services.battery_service import collect
        from logi_center.core.services.execution import CURRENT_CANCEL
        devices=[*self._manager.active('mouse'),*self._manager.active('keyboard'),*self._manager.active('audio')]
        token=self._battery_epoch.token();self._battery_busy=True
        def read():
            context=CURRENT_CANCEL.set(token)
            try:return collect(devices)
            finally:CURRENT_CANCEL.reset(context)
        future=self._pool.submit(read)
        def done(f):
            if self._closed or f.cancelled():return
            try:value,error=f.result(),None
            except Exception as failed:value,error=None,failed
            try:self._batteryReady.emit(value,token,error)
            except RuntimeError:pass
        future.add_done_callback(done)

    @Slot(object,object,object)
    def _accept_battery(self,outcome,token,error):
        if self._closed:return
        self._battery_busy=False
        if token.is_set():return
        failed,changed=True,False
        if self._manager:
            if not error:
                from logi_center.core.services.battery_service import apply
                failed,changed=apply(self._manager.devices,outcome)
            devices=dashboard_devices(self._current_devices(),self.simulation,True)
            self._all_presentations=[presentation(d,self._assets,self._artwork) for d in devices]
            self._rebuild_rows()
            if self._selected_id:
                current=next((row for row in self._all_presentations if row['deviceId']==self._selected_id),None)
                if current:self._selected_presentation=dict(current)
                self._set_capabilities(self._selected)
                self.selectedDeviceChanged.emit()
                self._editor.telemetryUpdated()
        if not self.simulation:
            mchose_live=bool(self._manager and any(d.connected is not False and
                any(c.name=='battery_status' and c.backend=='mchose' for c in d.capabilities)
                for d in self._manager.devices))
            self._battery_timer.start(30000 if failed else 3000 if changed or mchose_live else 8000)

    @Slot(bool)
    def setShowBuiltin(self, enabled):
        self._show_builtin = bool(enabled)
        self._rebuild_rows()
        self._save_preferences()

    @Slot(str)
    def setSearch(self, value):
        self._search_text = str(value)
        self._search = ' '.join(self._search_text.casefold().split())
        self._rebuild_rows()

    @Slot(str)
    def setCategory(self, value):
        self._category = str(value or 'all')
        self._rebuild_rows()

    @Slot(str)
    def selectDevice(self, device_id):
        device_id = str(device_id)
        if device_id == self._selected_id:
            # Returning to an already selected editor must re-read a profile
            # switched with the mouse's physical profile button.
            if self._selected and 'ratbagctl' in self._selected.backends:
                self._editor.reload()
            return
        self._selected_id = device_id
        device = self._find_device(device_id)
        self._selected = device
        self._selected_presentation = next((dict(row) for row in self._all_presentations
                                            if row['deviceId'] == device_id), {})
        self._set_capabilities(device)
        self._editor.bind(self._manager,device)
        if device and device.kind=='audio':
            for kind,rows in (('sink',self._audio.outputs),('source',self._audio.inputs)):
                target=next((r['name'] for r in rows if r['name'] in device.targets.get('pactl',[])),None)
                if target:self._audio.selectEndpoint(kind,target)
        self.selectedDeviceChanged.emit()

    @Slot()
    def clearSelection(self):
        self.selectDevice('')

    @Slot(str, str)
    def setUserArtwork(self, device_id, source):
        device = self._find_device(str(device_id))
        if device is None or device.connected is False:
            self._error = self.tr('Устройство сейчас недоступно')
            self.errorChanged.emit()
            return
        source = str(source or '')
        if source.startswith('file://'):
            from PySide6.QtCore import QUrl
            source = QUrl(source).toLocalFile()
        future = self._pool.submit(self._store_user_artwork, device, source)
        self._art_futures.add(future)
        future.add_done_callback(self._art_futures.discard)
        future.add_done_callback(lambda f: self._artworkReady.emit(
            str(device_id), f.result() if not f.exception() else None, f.exception()) if not self._closed and not f.cancelled() else None)

    @Slot(str, str)
    def previewUserArtwork(self, device_id, source):
        """Validate and decode a user image off-thread before showing a preview."""
        from PySide6.QtCore import QUrl
        device = self._find_device(str(device_id))
        local = QUrl(str(source or '')).toLocalFile() if str(source).startswith('file:') else str(source or '')
        if device is None or device.connected is not True:
            self.artworkPreviewReady.emit(str(device_id), '', self.tr('Устройство сейчас недоступно'))
            return
        future = self._pool.submit(self._validate_artwork_preview, local)
        self._art_futures.add(future)
        future.add_done_callback(self._art_futures.discard)
        future.add_done_callback(lambda f: self.artworkPreviewReady.emit(
            str(device_id), str(f.result() or '') if not f.exception() else '',
            str(f.exception()) if f.exception() else '') if not self._closed and not f.cancelled() else None)

    def _validate_artwork_preview(self, source):
        from PySide6.QtGui import QImageReader
        from logi_center.core.devices.device_artwork import validate_artwork_file
        valid, reason = validate_artwork_file(source)
        if not valid:
            raise ValueError(reason)
        reader = QImageReader(str(source))
        reader.setAutoTransform(True)
        size = reader.size()
        if not size.isValid() or size.width() * size.height() > 48_000_000:
            raise ValueError('Artwork dimensions are invalid or too large.')
        image = reader.read()
        if image.isNull():
            raise ValueError(reader.errorString() or 'The image could not be decoded.')
        from pathlib import Path
        return Path(source).resolve().as_uri()

    @Slot(str)
    def clearUserArtwork(self, device_id):
        device = self._find_device(str(device_id))
        if device is None:
            return
        try:
            self._artwork.clear_user_artwork(device)
            self._refresh_artwork_row(device)
            self._error = ''
        except (OSError, ValueError):
            self._error = self.tr('Не удалось восстановить стандартное изображение')
        self.errorChanged.emit()

    @Slot(str, str)
    def setUserName(self, device_id, name):
        device = self._find_device(str(device_id))
        if device is None or device.connected is False:
            self._error = self.tr('Устройство сейчас недоступно')
        else:
            try:
                self._artwork.set_user_name(device, str(name))
                self._refresh_artwork_row(device)
                self._error = ''
            except (OSError, ValueError):
                self._error = self.tr('Не удалось сохранить имя устройства')
        self.errorChanged.emit()

    def _store_user_artwork(self, device, source):
        from PySide6.QtGui import QImageReader

        def decode(path):
            reader = QImageReader(str(path))
            reader.setAutoTransform(True)
            size = reader.size()
            if not size.isValid() or size.width() * size.height() > 48_000_000:
                return False
            image = reader.read()
            return not image.isNull()

        return self._artwork.set_user_artwork(device, source, decoder=decode)

    @Slot(str, object, object)
    def _accept_artwork(self, device_id, stored_path, error):
        device = self._find_device(device_id)
        if error or device is None:
            self._error = self.tr('Не удалось использовать это изображение')
        else:
            self._refresh_artwork_row(device)
            self._error = ''
        self.errorChanged.emit()

    def _refresh_artwork_row(self, device):
        updated = presentation(device, self._assets, self._artwork)
        active=bool(dashboard_devices([device],self.simulation,True))
        exists=any(row['deviceId']==device.id for row in self._all_presentations)
        self._all_presentations = [updated if row['deviceId'] == device.id else row
                                   for row in self._all_presentations if row['deviceId']!=device.id or active]
        if active and not exists:self._all_presentations.append(updated)
        self._rebuild_rows()
        if self._selected_id == device.id:
            self._selected_presentation = dict(updated)
            self._set_capabilities(device)
            self.selectedDeviceChanged.emit()
        self._diagnostics.sync()
        self.devicesChanged.emit()

    @Slot(str,str)
    def rejectArtwork(self,device_id,source):
        from PySide6.QtCore import QUrl
        device=self._find_device(device_id)
        if device is None or self._closed:return
        path=Path(QUrl(source).toLocalFile())
        # Ignore a late error from a superseded request or another device.
        if path.resolve()!=self._artwork.resolve(device).path.resolve():return
        self._artwork.reject_decoding(path)
        self._refresh_artwork_row(device)

    @Slot(str)
    def setLanguage(self, language):
        language = language if language in ('ru', 'en') else 'en'
        if language == self._language:
            return
        self._language = language
        self._save_preferences()
        from logi_center.i18n import set_language
        set_language(language)
        # Presentation text comes from the same shared translator; rebuild rows.
        current = dashboard_devices(self._current_devices(), self.simulation, True)
        self._all_presentations = [presentation(d, self._assets, self._artwork) for d in current]
        self._rebuild_rows()
        self.inventoryChanged.emit()
        self._set_capabilities(self._selected)
        self._editor._render()
        self._audio.changed.emit()
        self.selectedDeviceChanged.emit()
        self.languageChanged.emit()
        self._backups.retranslate()
        if self._manager:
            self._backups.sync(self._manager, getattr(self, '_keyboard_online', None))

    @Property(str,constant=True)
    def appVersion(self):
        from logi_center.version import VERSION
        return VERSION

    @Slot(str, result=str)
    def tr(self, text):
        from logi_center.i18n import tr
        return tr(text)

    @Slot(result='QVariant')
    def diagnostics(self):
        if not self._manager:
            return []
        rows = []
        for fault in self._manager.faults:
            rows.append({'title': fault.component, 'message': fault.message})
        return rows

    @Property('QVariant', notify=devicesChanged)
    def backendSummary(self):
        seen = {}
        if self._manager:
            for device in self._manager.devices:
                for backend in device.backends:
                    seen.setdefault(backend, set()).add(device.id)
        return [{'name': name, 'devices': len(ids)} for name, ids in sorted(seen.items())]

    def _current_devices(self):
        return self._manager.devices if self._manager else []

    def _find_device(self, device_id):
        return next((d for d in self._current_devices() if d.id == device_id), None)

    def _set_capabilities(self, device):
        rows = []
        for cap in (device.capabilities if device else []):
            value = cap.value
            if cap.name == 'standard_input' and value in ('mouse', 'keyboard'):
                value = self.tr('Мышь' if value == 'mouse' else 'Клавиатура')
            rows.append({'id': cap.backend + ':' + cap.name,
                         'name': self.tr(CAPABILITY_LABELS.get(cap.name, cap.label or cap.name)),
                         'available': cap.supported is True,
                         'readable': bool(cap.readable), 'writable': bool(cap.writable),
                         'value': str(value) if value is not None else '',
                         'status': self.tr('Доступно') if cap.supported is True else self.tr('Неизвестно'),
                         'detail': self.tr('Доступны только настройки, предоставленные обнаруженными backend.')})
        self.capabilities.update(rows)

    @Slot(object, object)
    def _accept_snapshot(self, data, error):
        self._busy = False
        self.busyChanged.emit()
        if error:
            self._error = self.tr('Не удалось обновить список устройств')
            self.errorChanged.emit()
            if self._refresh_pending:
                self._event_timer.start()
            if not self.simulation:self._battery_timer.start(30000)
            return
        self._error = ''
        self.errorChanged.emit()
        self._manager = data.get('manager') if data else None
        self._keyboard_online = data.get('keyboard_online') if data else None
        self._audio.sync(data or {})
        self._diagnostics.sync()
        if self._manager:
            self._backups.sync(self._manager, self._keyboard_online)
        raw = dashboard_devices(self._current_devices(), self.simulation, True)
        self._all_presentations = [presentation(d, self._assets, self._artwork) for d in raw]
        self._updated_at = datetime.now().strftime('%H:%M')
        self.inventoryChanged.emit()
        self._rebuild_rows()
        # Keep selected ID across updates. If it disappeared, retain detail as disconnected view.
        if self._selected_id:
            self._selected = self._find_device(self._selected_id)
            current = next((row for row in self._all_presentations if row['deviceId'] == self._selected_id), None)
            if current:
                self._selected_presentation = dict(current)
            elif self._selected_presentation:
                self._selected_presentation = dict(self._selected_presentation)
                self._selected_presentation.update({'connected': False, 'status': self.tr('Отключено'),
                    'batteryPercent':-1,'batteryLabel':self.tr('Не в сети'),'batteryText':self.tr('Не в сети'),
                    'batteryState':'disconnected','charging':False,'chargingKnown':False})
            self._set_capabilities(self._selected)
            self._editor.bind(self._manager,self._selected)
            self.selectedDeviceChanged.emit()
        self.devicesChanged.emit()
        if self._refresh_pending:
            self._event_timer.start()
        # Fresh inventory may already contain a changed charging state. Read
        # the narrow telemetry report immediately after the snapshot arrives.
        if not self.simulation and not self._refresh_pending:self._battery_timer.start(0)

    def _rebuild_rows(self):
        from collections import Counter
        counts=Counter(row['name'].casefold() for row in self._all_presentations)
        rows = [dict(row,showSource=counts[row['name'].casefold()]>1) for row in self._all_presentations]
        inventory=dashboard_inventory(rows,self._search,self._show_builtin,self._category)
        self.devices.update(inventory['rows'])
        groups=inventory['groups']
        self.externalDevices.update(groups['external'])
        self.builtinDevices.update(groups['builtin'])
        self.audioDevices.update(groups['audio'])
        self.otherDevices.update(groups['other'])
        self.devicesChanged.emit()

    @Slot()
    def shutdown(self):
        if self._closed:
            return
        self._closed = True
        self._editor.shutdown()
        self._audio.shutdown()
        self._diagnostics.shutdown()
        self._backups.shutdown()
        self._battery_epoch.invalidate();self._battery_timer.stop()
        self._event_timer.stop()
        if self._monitor:
            self._monitor.stop()
        self._pool.shutdown(wait=False, cancel_futures=True)
        if self._art_temporary:
            temporary=self._art_temporary
            active=next((f for f in list(self._art_futures) if f.running()),None)
            if active:active.add_done_callback(lambda unused:temporary.cleanup())
            else:temporary.cleanup()
        self._preferences_pool.shutdown(wait=False)
