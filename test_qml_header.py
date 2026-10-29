"""Presentation-only header regression tests; no display or hardware required."""
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

try:
    from PySide6.QtCore import QCoreApplication, QProcess
    from qml_ui.bridge.bridge import DeviceBridge
    QT = True
except ImportError:
    QT = False


@unittest.skipUnless(QT, 'Optional PySide6 unavailable')
class HeaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        with patch.object(DeviceBridge, 'refresh'):
            self.bridge = DeviceBridge(simulation=True)
        self.addCleanup(self.bridge.shutdown)

    def test_counts_follow_visible_inventory_and_timestamp_follows_success(self):
        from scripts.illustration_dashboard import fixture_snapshot
        self.assertEqual(self.bridge.updatedAt, '')
        self.bridge._accept_snapshot(fixture_snapshot(True), None)
        counts = self.bridge.inventoryCounts
        stamp = self.bridge.updatedAt
        self.assertEqual(counts['external'], 4)
        self.assertEqual(counts['builtin'], 2)
        self.assertRegex(stamp, r'^\d\d:\d\d$')
        self.bridge.setSearch('nothing matches')
        self.bridge.setShowBuiltin(False)
        self.assertEqual(self.bridge.devices.count, 0)
        self.assertEqual(sum(self.bridge.inventoryCounts.values()),0)
        self.bridge._accept_snapshot(None, ValueError('test'))
        self.assertEqual(self.bridge.updatedAt, stamp)
        self.assertEqual(sum(self.bridge.inventoryCounts.values()),0)

    def test_shared_counts_match_every_visible_section_for_each_filter(self):
        from scripts.illustration_dashboard import fixture_snapshot
        self.bridge._accept_snapshot(fixture_snapshot(True),None)
        for category in ('all','mouse','keyboard','audio'):
            for show in (False,True):
                for query in ('','mchose','no match'):
                    self.bridge.setCategory(category);self.bridge.setShowBuiltin(show);self.bridge.setSearch(query)
                    counts=self.bridge.inventoryCounts
                    models={'external':self.bridge.externalDevices,'builtin':self.bridge.builtinDevices,
                            'audio':self.bridge.audioDevices,'other':self.bridge.otherDevices}
                    self.assertEqual(counts,{k:v.count for k,v in models.items()})
                    self.assertEqual(sum(counts.values()),self.bridge.devices.count)
                    if category=='all':self.assertEqual(self.bridge.categoryCounts['all'],self.bridge.devices.count)
                    if not show:self.assertEqual(counts['builtin'],0)

    def test_native_backup_entry_needs_no_second_gui_process(self):
        from qml_ui.bridge.backups import BackupController
        with patch('PySide6.QtCore.QProcess.startDetached',side_effect=AssertionError('External GUI launch')):
            controller=self.bridge.backups
            self.assertIsInstance(controller,BackupController)
            controller.sync(controller.transport.manager)
            self.assertTrue(controller.targetAvailable)
            self.assertTrue(controller.targets)
        self.assertFalse(hasattr(self.bridge,'openGtkBackups'))

    def test_native_backup_page_exposes_import_export_and_restore(self):
        page=(Path(__file__).resolve().parent/'qml_ui/qml/BackupsPage.qml').read_text()
        for action in ('exportFile','inspectFile','restoreSelected'):
            self.assertIn('controller.'+action,page)
        self.assertNotIn('Gtk',page)

    def test_header_strings_have_english_translations(self):
        from i18n import EN
        for text in ('%1 внешних · %2 встроенных · обновлено %3', 'Инструменты',
                     'Настройки', 'Резервные копии', 'Диагностика', 'О программе',
                     'Настройки этой сессии. Аппаратные параметры не изменяются.'):
            self.assertIn(text, EN)
            self.assertNotEqual(text, EN[text])

    def test_category_counts_follow_search_and_builtin_filter_without_discovery(self):
        from scripts.illustration_dashboard import fixture_snapshot
        self.bridge._accept_snapshot(fixture_snapshot(True), None)
        with patch.object(self.bridge,'refresh') as discovery:
            self.bridge.setSearch('  MCHOSE   K7  ')
            self.assertEqual(self.bridge.searchQuery,'  MCHOSE   K7  ')
            self.assertEqual(self.bridge.categoryCounts['all'],1)
            self.assertEqual(self.bridge.categoryCounts['mouse'],1)
            self.bridge.setCategory('keyboard')
            self.assertEqual(self.bridge.devices.count,0)
            self.bridge.setSearch('');self.bridge.setShowBuiltin(False)
            self.assertEqual(self.bridge.devices.count,1)
            self.assertEqual(self.bridge.inventoryCounts['builtin'],0)
            self.assertEqual(self.bridge.builtinFilterCount,1)
            discovery.assert_not_called()

    def test_simulation_does_not_load_probe_or_save_user_preferences(self):
        with patch('qml_ui.bridge.preferences.save_preferences') as save, \
             patch('qml_ui.bridge.preferences.system_reduced_motion') as probe, \
             patch('qml_ui.bridge.preferences.load_preferences') as load, \
             patch.object(DeviceBridge,'refresh'):
            isolated=DeviceBridge(simulation=True)
            try:
                isolated.setShowBuiltin(False)
                isolated.setLanguage('en')
                isolated.setReducedMotion(True)
                self.assertTrue(isolated.reducedMotion)
                load.assert_not_called();save.assert_not_called();probe.assert_not_called()
            finally:isolated.shutdown()

    def test_battery_refresh_uses_immediate_event_and_bounded_mchose_poll(self):
        from devices import Capability
        from scripts.illustration_dashboard import fixture_snapshot
        bridge=self.bridge
        bridge.simulation=False  # The instance has no live monitor or hardware runner.
        try:
            bridge._accept_snapshot(fixture_snapshot(True),None)
            self.assertTrue(bridge._battery_timer.isActive())
            self.assertLessEqual(bridge._battery_timer.remainingTime(),100)
            bridge._battery_timer.stop()
            mouse=bridge._manager.devices[0]
            mouse.capabilities.append(Capability('battery_status','mchose',True,True,value=46,source='device'))
            bridge._accept_battery(([],[],None,None),bridge._battery_epoch.token(),None)
            self.assertTrue(bridge._battery_timer.isActive())
            self.assertLessEqual(bridge._battery_timer.remainingTime(),3500)
            self.assertGreater(bridge._battery_timer.remainingTime(),2000)
            bridge._battery_timer.stop()
            bridge._busy=True
            bridge._poll_battery()
            self.assertLessEqual(bridge._battery_timer.remainingTime(),1500)
        finally:
            bridge._battery_timer.stop()
            bridge.simulation=True


if __name__ == '__main__':
    unittest.main()
