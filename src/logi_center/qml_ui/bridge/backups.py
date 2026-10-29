"""Thin QML presentation of the two unchanged backup services."""
from dataclasses import dataclass
from pathlib import Path
import json
import tempfile

from PySide6.QtCore import QObject, Signal, Slot, Property, QUrl, QByteArray
from logi_center.core.discovery.discovery import Epoch
from logi_center.core.services.execution import Fault, FaultCode, CURRENT_CANCEL
from .models import CapabilityListModel


class BackupFieldModel(CapabilityListModel):
    selectionChanged = Signal()

    def roleNames(self): return {self.CapabilityRole: QByteArray(b'field')}

    @Slot(str, bool)
    def select(self, identifier, enabled):
        if self.parent().busy: return
        index = self._by_id.get(identifier)
        if index is None: return
        self._rows[index] = dict(self._rows[index], selected=bool(enabled))
        self.dataChanged.emit(self.index(index), self.index(index), [self.CapabilityRole])
        self.selectionChanged.emit()

    def selected(self): return {row['id'] for row in self._rows if row.get('selected')}


@dataclass(frozen=True)
class Binding:
    key: str
    name: str
    mode: str
    kind: str
    target: str
    fingerprint: tuple
    device: object = None
    restore_allowed: bool = True


def identity(device):
    # Private in-memory guard, never a public report or filename.
    return (device.id, device.physical, device.vid, device.pid, device.connection,
            tuple(sorted((key, tuple(value)) for key, value in device.targets.items())))


class BackupController(QObject):
    changed = Signal()
    completedRestore = Signal()
    _ready = Signal(str, object, object)

    def __init__(self, owner, pool, simulation=False, transport=None):
        super().__init__(owner)
        self.owner = owner
        self.pool = pool
        self.fields = BackupFieldModel(self)
        self.fields.selectionChanged.connect(self.changed)
        self.epoch = Epoch()
        self.simulation = simulation
        if simulation and transport is None:
            from .backup_simulation import BackupSimulation
            transport = BackupSimulation()
        self.transport = transport
        self._temporary = tempfile.TemporaryDirectory(prefix='logi-backup-simulation-') if simulation else None
        self._bindings = {}; self._key = ''; self._preview = None
        self._busy = False; self._valid = False; self._message = ''; self._skipped = []
        self._closed = False; self._manager = None; self._job = None
        self._safety_path = ''
        self._cancelled = False
        self._selection_drafts = {}; self._preview_scope = None
        self._ready.connect(self._accept)

    def tr(self, text): return self.owner.tr(text)

    @Property('QVariantList', notify=changed)
    def targets(self):
        return [{'key': b.key, 'name': b.name + (' · ' + self.tr('Возможности устройства') if b.mode == 'provider' else ' · ' + self.tr('Стандартная копия'))}
                for b in self._bindings.values()]

    @Property(str, notify=changed)
    def selectedKey(self): return self._key

    @Property(bool, notify=changed)
    def targetAvailable(self): return self._key in self._bindings

    @Property(str, notify=changed)
    def targetNote(self):
        binding = self._bindings.get(self._key)
        return self.tr('Для восстановления требуется подтверждённое подключение устройства.') if binding and not binding.restore_allowed else ''

    @Property(str, notify=changed)
    def safetyPath(self): return self._safety_path

    @Property(bool, notify=changed)
    def reportAvailable(self): return bool(self._safety_path)

    @Property('QVariant', constant=True)
    def fieldModel(self): return self.fields

    @Property(bool, notify=changed)
    def busy(self): return self._busy

    @Property(bool, notify=changed)
    def canRestore(self):
        binding = self._bindings.get(self._key)
        return bool(binding and binding.restore_allowed and self._valid and not self._busy and self.fields.selected())

    @Property(str, notify=changed)
    def message(self):
        parts = self._message if isinstance(self._message, list) else [self._message]
        return ' '.join(self.tr(part) for part in parts if part)

    @Property('QVariantList', notify=changed)
    def skipped(self): return self._skipped

    @Property(int, notify=changed)
    def selectedCount(self): return len(self.fields.selected())

    def sync(self, manager, keyboard_online=None):
        import logi_center.core.services.capability_backup as provider
        if self._closed: return
        if self.simulation: manager = self.transport.manager
        self._manager = manager
        bindings = {}
        active = [d for d in manager.devices if d.connected is True and d.simulated == self.simulation]
        for device in active:
            fingerprint = identity(device)
            if any(c.readable and c.backend in provider.PROVIDERS for c in device.capabilities):
                key = device.id + ':provider'
                bindings[key] = Binding(key, device.name, 'provider', device.kind, '', fingerprint, device)
            ratbag = device.targets.get('ratbagctl', [])
            if len(ratbag) == 1 and sum(ratbag[0] in d.targets.get('ratbagctl', []) for d in active) == 1:
                key = device.id + ':legacy'
                bindings[key] = Binding(key, device.name, 'legacy', 'mouse', ratbag[0], fingerprint, device)
            if device.kind == 'keyboard' and 'G515' in device.name and any(
                    c.backend == 'solaar' for c in device.capabilities):
                key = device.id + ':legacy'
                bindings[key] = Binding(key, device.name, 'legacy', 'keyboard', 'G515', fingerprint, device)
        saved = [d for d in manager.devices if d.backend == 'solaar-local' and 'G515' in d.name]
        if saved and not any(b.kind == 'keyboard' and b.mode == 'legacy' for b in bindings.values()):
            # This is an explicitly local configuration, never an active device.
            # The same existing ROOT-ping/write guard used by GTK remains in force.
            live = [d for d in active if d.kind == 'keyboard' and 'G515' in d.name]
            fingerprint = (tuple(d.id for d in saved), keyboard_online,
                           tuple(identity(d) for d in live))
            bindings['local-g515'] = Binding('local-g515', self.tr('Локальные настройки G515'),
                'legacy', 'keyboard', 'G515', fingerprint,
                restore_allowed=keyboard_online is True and len(live) <= 1)
        audio = [d for d in active if 'pulse' in d.targets or 'pactl' in d.targets]
        if audio:
            bindings['local-audio'] = Binding('local-audio', self.tr('Настройки звукового сервера'),
                'legacy', 'audio', 'local-audio', tuple(sorted(identity(d) for d in audio)))
        old = self._bindings.get(self._key)
        new = bindings.get(self._key)
        if old and (not new or old.fingerprint != new.fingerprint): self.invalidate()
        self._bindings = bindings
        if not self._key and bindings: self._key = next(iter(bindings))
        self.changed.emit()

    def invalidate(self):
        self.epoch.invalidate(); self._valid = False
        if self._preview: self._message = 'Подключение изменилось. Открой предпросмотр заново.'
        self.changed.emit()

    @Slot(str)
    def selectTarget(self, key):
        if self._busy or key == self._key: return
        self._stash_selection()
        self.epoch.invalidate(); self._key = key if key in self._bindings else ''
        self._preview = None; self._valid = False; self._skipped = []; self._message = ''
        self._safety_path = ''
        self.fields.update([]); self.changed.emit()

    def _stash_selection(self):
        if self._preview_scope is not None:
            choices = self._selection_drafts.setdefault(self._preview_scope, {})
            choices.update({row['id']:row['selected'] for row in self.fields._rows})

    def _path(self, value):
        url = QUrl(str(value))
        if url.scheme() and not url.isLocalFile(): raise ValueError('Local files only')
        return Path(url.toLocalFile() if url.isLocalFile() else str(value))

    def _submit(self, action, work):
        if self._closed or self._busy: return
        if any(getattr(getattr(self.owner,name,None),'busy',False) is True for name in ('_editor','_audio')):
            self._message='Дождись завершения текущей операции.';self.changed.emit();return
        binding = self._bindings.get(self._key)
        if binding is None:
            self._message = 'Устройство сейчас недоступно'; self.changed.emit(); return
        token = self.epoch.token()
        self._cancelled = False
        self._busy = True; self._message = 'Выполняется…'; self.changed.emit()
        def run():
            context = CURRENT_CANCEL.set(token)
            try:
                def guarded(args, **kwargs):
                    if token.is_set(): raise Fault(FaultCode.CANCELLED, 'backup', 'Device binding changed')
                    self._manager.guard_command(args)
                    if self.simulation: return self.transport.run(args, **kwargs)
                    from logi_center.adapters.external.backend import run as real_run
                    return real_run(args, **kwargs)
                return work(binding, guarded, token)
            finally: CURRENT_CANCEL.reset(context)
        future = self._job = self.pool.submit(run)
        def done(f):
            if self._closed: return
            try: value, error = f.result(), None
            except Exception as failure: value, error = None, failure
            try: self._ready.emit(action, (value, token), error)
            except RuntimeError: pass  # Qt owner already gone during shutdown.
        future.add_done_callback(done)

    @staticmethod
    def _capture(binding, runner):
        if binding.mode == 'provider':
            from logi_center.core.services.capability_backup import capture
            return capture(binding.device, runner)
        from logi_center.core.services.backups import snapshot
        return snapshot(binding.kind, binding.target, runner)

    @Slot(str)
    def exportFile(self, path):
        def save(binding, runner, token):
            doc = self._capture(binding, runner)
            if token.is_set(): raise ValueError('Device changed')
            if binding.mode == 'provider':
                from logi_center.core.services.capability_backup import write
            else:
                from logi_center.core.services.backups import write_backup as write
            write(doc, self._path(path))
        self._submit('export', save)

    @Slot(str)
    def inspectFile(self, path):
        if self._busy: return
        self._stash_selection()
        self._safety_path = ''
        self._valid = False; self._preview = None; self.fields.update([])
        def inspect(binding, runner, token):
            if binding.mode == 'provider':
                from logi_center.core.services.capability_backup import read, preview
            else:
                from logi_center.core.services.backups import read_backup as read, preview
            document = read(self._path(path))  # checksum/model validation stays in services
            current = self._capture(binding, runner)
            result = preview(document, current, binding.device if binding.mode == 'provider' else binding.target)
            if token.is_set(): raise ValueError('Device changed')
            return result
        self._submit('preview', inspect)

    @Slot()
    def cancel(self):
        if not self._busy: return
        self._cancelled = True; self.epoch.invalidate(); self._valid = False
        self._message = 'Операция отменяется…'; self.changed.emit()

    @Slot()
    def restoreSelected(self):
        if not self.canRestore or self._preview is None: return
        selected = self.fields.selected(); preview = self._preview
        self._submitted = set(selected)
        self._valid = False
        def restore(binding, runner, token):
            if binding.mode == 'provider':
                from logi_center.core.services.capability_backup import restore as service
                target = binding.device
                kwargs = {}
            else:
                from logi_center.core.services.backups import restore as service
                target = binding.target
                kwargs = {'cancel': token}
            if self._temporary: kwargs['safety_root'] = Path(self._temporary.name) / 'before-restore'
            return service(preview, selected, target, runner=runner, **kwargs)
        self._submit('restore', restore)

    def _source(self, value):
        return self.tr({'device':'Чтение с устройства', 'backend_cache':'Кэш демона',
            'local_saved_settings':'Локальные настройки', 'audio_server':'Звуковой сервер'}.get(value, 'Источник неизвестен'))

    def _label(self, change):
        from .bridge import CAPABILITY_LABELS
        label = change.label.split(' → ')[0]
        if ':' in label and '#' not in label:
            name = label.split(':', 1)[-1]
            return self.tr(CAPABILITY_LABELS.get(name, name))
        if change.args[:1] == ['pactl']:
            direction = 'Микрофон' if 'source' in change.args[1] else 'Выход'
            collection = 'sources' if direction == 'Микрофон' else 'sinks'
            nodes = self._preview.current['settings'].get(collection, []) if self._preview else []
            ordinal = next((i + 1 for i,d in enumerate(nodes) if d['name'] == change.args[2]), 1)
            devices = self._manager.devices if self._manager else []
            device = next((d for d in devices if change.args[2] in d.targets.get('pactl',[]) or change.args[2] in d.targets.get('pulse',[])), None)
            from logi_center.core.devices.device_presentation import model_name
            name = ' · ' + model_name(device) if device else ''
            field = 'Без звука' if change.args[1].endswith('mute') else 'Громкость'
            return self.tr(direction) + ' ' + str(ordinal) + name + ' · ' + self.tr(field)
        head, sep, tail = label.rpartition(' · ')
        if sep and tail in CAPABILITY_LABELS:
            return head + sep + self.tr(CAPABILITY_LABELS[tail])
        import re
        label = re.sub(r'^Profile (\d+)', lambda m:self.tr('Профиль')+' '+m[1], label)
        for text,key in (('polling rate','Частота опроса'),('button','Кнопка'),('lighting','Подсветка'),('DPI stage','Ступень DPI')):
            label = label.replace(text,self.tr(key))
        return label

    @Slot(str, object, object)
    def _accept(self, action, outcome, error):
        if self._closed: return
        self._busy = False
        value, token = outcome
        if error:
            text = str(error).lower()
            key = 'Контрольная сумма или формат копии неверны' if 'checksum' in text or 'integrity' in text else (
                'Копия не соответствует модели устройства' if 'model' in text or 'descriptor' in text else (
                'Состояние изменилось. Открой предпросмотр заново.' if 'changed' in text or token.is_set() else
                'Операция не выполнена. Проверь файл, подключение и доступ к устройству.'))
            self._message = key
            if self._cancelled: self._message = 'Операция отменена; результат требует проверки'
        elif action == 'preview' and not token.is_set():
            self._preview = value; self._valid = True; self._skipped = list(value.skipped)
            self._preview_scope = (self._key, value.backup['sha256'])
            choices = self._selection_drafts.get(self._preview_scope)
            rows = []
            for change in value.changes:
                setting = change.id.partition('#')[0]
                old = value.current.get('settings', {}).get(setting, {})
                new = value.backup.get('settings', {}).get(setting, {})
                rows.append({'id':change.id, 'label':self._label(change), 'selected':choices.get(change.id,False) if choices is not None else True,
                    'current':json.dumps(change.current, ensure_ascii=False),
                    'desired':json.dumps(change.desired, ensure_ascii=False),
                    'currentSource':self._source(old.get('source', value.current['source']) if isinstance(old,dict) else value.current['source']),
                    'backupSource':self._source(new.get('source', value.backup['source']) if isinstance(new,dict) else value.backup['source']),
                    'result':'', 'resultKey':'', 'rawLabel':change.label, 'currentSourceKey':old.get('source', value.current['source']) if isinstance(old,dict) else value.current['source'], 'backupSourceKey':new.get('source', value.backup['source']) if isinstance(new,dict) else value.backup['source']})
            self.fields.update(rows)
            self._message = 'Выбери поля и нажми «Восстановить выбранное».' if rows else 'Изменений нет'
        elif action == 'restore':
            from logi_center.core.services.operations import State
            labels = {State.CONFIRMED:'Подтверждено чтением', State.SENT:'Отправлено, не подтверждено',
                      State.LOCAL:'Сохранено локально', State.MISMATCH:'Значение не совпало',
                      State.PERMISSION:'Нет доступа к устройству', State.UNSUPPORTED:'Не поддерживается устройством',
                      State.DISCONNECTED:'Устройство отключено; результат требует проверки', State.CANCELLED:'Операция отменена; результат требует проверки'}
            # Results correspond to service-generated changes, never file commands.
            submitted = [c for c in self._preview.changes if c.id in self._submitted]
            result_map = {change.id:result for change,(label,result) in zip(submitted,value.results)
                          if change.label == label}
            rows = [dict(row) for row in self.fields._rows]
            for row in rows:
                change = next(c for c in self._preview.changes if c.id == row['id'])
                result = result_map.get(change.id)
                if result is not None: row['resultKey'] = labels.get(result.state, 'Ошибка применения')
                elif row['id'] in self._submitted: row['resultKey'] = 'Не выполнено'
                row['result'] = self.tr(row['resultKey'])
                row['actual'] = json.dumps(result.actual,ensure_ascii=False) if result is not None and result.actual is not None else ''
                row['resultSourceKey'] = result.source if result is not None else 'unavailable'
                row['resultSource'] = self._source(row['resultSourceKey'])
            self.fields.update(rows); self._skipped = list(value.skipped)
            self._safety_path = value.safety_copy
            self._message = ['Восстановление остановлено. Проверь результаты по полям.' if value.stopped else 'Операция завершена. Проверь подтверждение каждого поля.', 'Защитная копия сохранена приватно.']
            if self._cancelled: self._message[0] = 'Операция отменена; результат требует проверки'
            if self.simulation: self._message.insert(0, 'Симуляция: аппаратные настройки не изменены.')
            self.completedRestore.emit()
        elif action == 'export': self._message = 'Копия сохранена'
        else: self._message = 'Подключение изменилось. Открой предпросмотр заново.'
        self.changed.emit()

    def retranslate(self):
        if self._preview:
            changes = {change.id:change for change in self._preview.changes}
            rows = [dict(row) for row in self.fields._rows]
            for row in rows:
                row['label'] = self._label(changes[row['id']])
                row['currentSource'] = self._source(row['currentSourceKey'])
                row['backupSource'] = self._source(row['backupSourceKey'])
                row['result'] = self.tr(row.get('resultKey', ''))
                row['resultSource'] = self._source(row.get('resultSourceKey', 'unavailable'))
            self.fields.update(rows)
        self.changed.emit()

    def shutdown(self):
        self._closed = True; self.epoch.invalidate()
        if self._temporary:
            temporary = self._temporary
            if self._job and not self._job.done(): self._job.add_done_callback(lambda unused: temporary.cleanup())
            else: temporary.cleanup()
