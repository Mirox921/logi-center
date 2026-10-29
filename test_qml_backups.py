"""QML backup facade tests execute unchanged services through memory-only I/O."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

try:
    from PySide6.QtCore import QCoreApplication
    from qml_ui.bridge.bridge import DeviceBridge
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'Optional PySide6 unavailable')
class BackupBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        from i18n import set_language
        set_language('ru')
        self.forbidden = patch('backend.run', side_effect=AssertionError('Real I/O forbidden'))
        self.hardware = self.forbidden.start()
        self.addCleanup(self.forbidden.stop)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        with patch.object(DeviceBridge, 'refresh'):
            self.owner = DeviceBridge(simulation=True)
        self.addCleanup(self.owner.shutdown)
        self.controller = self.owner.backups
        self.mock = self.controller.transport
        self.controller.sync(self.mock.manager)
        self.assertFalse(self.mock.writes)

    def wait(self):
        deadline = time.monotonic() + 6
        while self.controller.busy and time.monotonic() < deadline:
            self.app.processEvents(); time.sleep(.005)
        self.assertFalse(self.controller.busy)
        self.hardware.assert_not_called()

    def provider_file(self, values=None):
        import capability_backup as service
        path = Path(self.temporary.name) / 'provider.json'
        doc = service.capture(self.mock.devices[0], lambda _args: json.dumps(values or {'dpi':1600,'debounce':8}))
        service.write(doc, path)
        return path

    def preview(self, values=None):
        path = self.provider_file(values)
        self.controller.inspectFile(path.as_uri()); self.wait()
        self.assertTrue(self.controller.canRestore, self.controller.message)
        return path

    def test_preview_is_read_only_and_selective_restore_has_private_safety(self):
        self.preview()
        self.assertEqual(self.mock.writes, [])
        self.assertEqual(self.controller.fields.count, 2)
        self.controller.fields.select('mchose:debounce', False)
        self.controller.restoreSelected(); self.wait()
        self.assertEqual(self.mock.writes, ['dpi'])
        self.assertEqual(self.mock.values, {'dpi':1600,'debounce':4})
        snapshot = next((Path(self.controller._temporary.name)/'before-restore').glob('*.json'))
        self.assertEqual(snapshot.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(snapshot.read_text())['settings']['mchose:dpi']['value'], 800)
        row = self.controller.fields._rows[0]
        self.assertEqual(row['resultKey'], 'Подтверждено чтением')
        self.assertIn('Симуляция', self.controller.message)
        self.assertFalse(self.controller.canRestore)

    def test_checksum_rejected_before_device_read_or_write(self):
        path = self.provider_file()
        doc = json.loads(path.read_text()); doc['settings']['mchose:dpi']['value'] = 1800
        path.write_text(json.dumps(doc))
        with patch.object(self.mock, 'run', wraps=self.mock.run) as runner:
            self.controller.inspectFile(str(path)); self.wait()
            runner.assert_not_called()
        self.assertIn('Контрольная сумма', self.controller.message)
        self.assertFalse(self.controller.canRestore)

    def test_wrong_model_rejected(self):
        from backups import digest
        path = self.provider_file(); doc=json.loads(path.read_text())
        doc['device']['model'] = 'Another model'; doc['sha256']=digest(doc);path.write_text(json.dumps(doc))
        self.controller.inspectFile(str(path)); self.wait()
        self.assertIn('модели', self.controller.message)
        self.assertFalse(self.controller.canRestore); self.assertEqual(self.mock.writes, [])

    def test_changed_state_before_restore_rejects_without_mutation(self):
        self.preview(); self.mock.values['dpi'] = 1200
        self.controller.restoreSelected(); self.wait()
        self.assertEqual(self.mock.writes, [])
        self.assertIn('Состояние изменилось', self.controller.message)
        self.assertFalse((Path(self.controller._temporary.name)/'before-restore').exists())

    def test_partial_failure_and_unperformed_fields_are_reported(self):
        self.preview(); self.mock.fail_field = 'debounce'
        self.controller.restoreSelected(); self.wait()
        self.assertEqual(self.mock.values, {'dpi':1600,'debounce':4})
        self.assertIn('остановлено', self.controller.message)
        self.assertIn('Устройство отключено', self.controller.fields._rows[1]['result'])

    def test_failed_readback_remains_unconfirmed(self):
        self.preview({'dpi':1600,'debounce':4}); self.mock.unverified = True
        self.controller.restoreSelected(); self.wait()
        self.assertEqual(self.mock.values['dpi'], 1600)
        self.assertEqual(self.controller.fields._rows[0]['resultKey'], 'Отправлено, не подтверждено')

    def test_disconnect_rebind_requires_new_preview_preserves_selection(self):
        self.preview(); self.controller.fields.select('mchose:debounce', False)
        original_selected = self.controller.fields.selected()
        self.controller.invalidate()
        self.controller.sync(self.mock.manager)
        self.assertFalse(self.controller.canRestore)
        self.assertEqual(self.controller.fields.selected(), original_selected)
        self.controller.restoreSelected(); self.assertEqual(self.mock.writes, [])
        self.preview(); self.assertTrue(self.controller.canRestore)

    def test_generation_guard_between_commands_prevents_next_write(self):
        self.preview()
        original_run = self.mock.run
        def cancel_after_first(args, **kwargs):
            result = original_run(args, **kwargs)
            if args[2] == 'set': self.controller.epoch.invalidate()
            return result
        with patch.object(self.mock, 'run', side_effect=cancel_after_first):
            self.controller.restoreSelected(); self.wait()
        self.assertEqual(self.mock.writes, ['dpi'])
        self.assertEqual(self.controller.fields._rows[1]['resultKey'], 'Не выполнено')

    def test_identity_change_invalidates_preview_without_merging_identical_models(self):
        from copy import deepcopy
        self.preview()
        second = deepcopy(self.mock.devices[0]); second.id += '-2'; second.target = 'other'
        second.physical='different-port'; second.targets={'mchose':['other']}
        self.mock.manager.devices.append(second)
        self.controller.sync(self.mock.manager)
        self.assertEqual(len(self.controller.targets), 3)
        self.mock.devices[0].physical='new-instance'
        self.controller.sync(self.mock.manager)
        self.assertFalse(self.controller.canRestore)

    def test_export_uses_unchanged_provider_format_and_private_file(self):
        import capability_backup as service
        path = Path(self.temporary.name)/'export.json'
        self.controller.exportFile(str(path)); self.wait()
        doc = service.read(path)
        self.assertEqual(doc['format'], service.FORMAT)
        self.assertEqual(doc['settings']['mchose:dpi']['source'], 'device')
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.mock.writes, [])

    def test_legacy_format_and_cache_result_are_not_promoted_to_hardware(self):
        import backups as service
        self.controller.selectTarget('sim:backup-legacy:legacy')
        doc = service.snapshot('mouse','sim-ratbag',self.mock.run)
        doc['settings']['profiles'][0]['resolutions'][0]['dpi']=1600
        doc['sha256']=service.digest(doc)
        path=Path(self.temporary.name)/'legacy.json';service.write_backup(doc,path)
        self.controller.inspectFile(str(path));self.wait()
        self.assertTrue(self.controller.canRestore,self.controller.message)
        self.assertEqual(self.controller.fields._rows[0]['currentSource'], 'Кэш демона')
        self.controller.restoreSelected();self.wait()
        self.assertEqual(self.mock.legacy_dpi,1600)
        self.assertEqual(self.controller.fields._rows[0]['resultKey'],'Отправлено, не подтверждено')

    def test_retranslation_keeps_fields_and_selection(self):
        self.preview(); self.controller.fields.select('mchose:debounce', False)
        selected=self.controller.fields.selected()
        self.owner.setLanguage('en')
        self.assertEqual(self.controller.fields.selected(),selected)
        self.assertEqual(self.controller.fields._rows[0]['currentSource'], 'Device read')
        self.assertIn('Choose fields',self.controller.message)

    def test_network_urls_are_not_read(self):
        self.controller.inspectFile('https://invalid.example/backup.json');self.wait()
        self.assertFalse(self.controller.canRestore);self.assertEqual(self.mock.writes,[])

    def test_cached_keyboard_can_be_exported_and_previewed_but_not_restored_offline(self):
        import backups as service
        from devices import Device, DeviceManager
        manager = DeviceManager()
        manager.devices = [Device('saved-keyboard', 'Logitech G515', 'keyboard',
                                  'solaar-local', connected=None)]
        self.controller.simulation = False
        self.controller.sync(manager, keyboard_online=False)
        self.controller.selectTarget('local-g515')
        data = {'_modelId':'MOCK', 'brightness_control':10}
        destination = Path(self.temporary.name)/'local.json'
        with patch('backend.saved_keyboard', return_value=data):
            self.controller.exportFile(str(destination)); self.wait()
            wanted = service.seal('keyboard','G515:MOCK',{'brightness_control':60},'local_saved_settings')
            service.write_backup(wanted,destination)
            self.controller.inspectFile(str(destination));self.wait()
        self.assertEqual(self.controller.fields.count,1)
        self.assertEqual(self.controller.fields._rows[0]['currentSource'],'Локальные настройки')
        self.assertFalse(self.controller.canRestore)
        self.assertIn('подключение',self.controller.targetNote)

    def test_battery_update_keeps_preview_rows_and_selected_fields(self):
        self.preview(); self.controller.fields.select('mchose:debounce',False)
        resets=[]; self.controller.fields.modelReset.connect(lambda:resets.append(True))
        selected=self.controller.fields.selected()
        self.mock.devices[0].capabilities[0].observed_at='2030-01-01T00:00:00+00:00'
        self.controller.sync(self.mock.manager)
        self.assertEqual(self.controller.fields.selected(),selected)
        self.assertTrue(self.controller.canRestore)
        self.assertEqual(resets,[])

    def test_audio_facade_uses_server_values_and_names_distinct_routes(self):
        import backups as service
        from devices import Device, DeviceManager
        manager=DeviceManager()
        manager.devices=[Device('audio:one','USB Headset','audio','pactl','fixture-sink')]
        self.controller.simulation=False;self.controller.sync(manager)
        self.controller.selectTarget('local-audio')
        volume=[30]
        def server(args, **kwargs):
            if args[:4]==['pactl','-f','json','list']:
                return json.dumps([{'name':'fixture-sink','volume':{'mono':{'value_percent':str(volume[0])+'%'}},'mute':False}]) if args[-1]=='sinks' else '[]'
            if args[:2]==['pactl','set-sink-volume']:
                volume[0]=int(args[-1].rstrip('%'));return ''
            raise AssertionError('Unexpected audio request')
        wanted=service.seal('audio','local-audio-devices',{'sinks':[{'name':'fixture-sink','volume':[60],'mute':False}],'sources':[]},'audio_server')
        path=Path(self.temporary.name)/'audio.json';service.write_backup(wanted,path)
        with patch('backend.run',side_effect=server):
            self.controller.inspectFile(str(path));self.wait()
            self.assertTrue(self.controller.canRestore,self.controller.message)
            self.assertEqual(self.controller.fields._rows[0]['currentSource'],'Звуковой сервер')
            self.assertIn('Выход 1',self.controller.fields._rows[0]['label'])
            self.controller.restoreSelected();self.wait()
        self.assertEqual(volume,[60])
        self.assertEqual(self.controller.fields._rows[0]['resultKey'],'Подтверждено чтением')
        self.assertEqual(self.controller.fields._rows[0]['resultSource'],'Звуковой сервер')

    def test_cancel_before_write_preserves_settings(self):
        self.preview()
        original=self.mock.run
        def cancel_on_capture(args, **kwargs):
            value=original(args, **kwargs)
            self.controller.cancel()
            return value
        with patch.object(self.mock,'run',side_effect=cancel_on_capture):
            self.controller.restoreSelected();self.wait()
        self.assertEqual(self.mock.writes,[])
        self.assertFalse(self.controller.canRestore)
        self.assertIn('отмен',self.controller.message)

    def test_same_backup_repreview_after_reconnect_preserves_field_choices(self):
        path=self.preview()
        self.controller.fields.select('mchose:debounce',False)
        self.controller.invalidate();self.controller.sync(self.mock.manager)
        self.controller.inspectFile(str(path));self.wait()
        self.assertEqual(self.controller.fields.selected(),{'mchose:dpi'})
