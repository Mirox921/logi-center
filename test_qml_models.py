import unittest

try:
    from qml_ui.bridge.models import DeviceListModel
    from PySide6.QtCore import Qt
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


@unittest.skipUnless(QT_AVAILABLE, 'PySide6 is optional and unavailable in this environment')
class QmlModelTests(unittest.TestCase):
    def test_device_rows_update_by_stable_id_without_reset(self):
        from PySide6.QtCore import QCoreApplication
        app = QCoreApplication.instance() or QCoreApplication([])
        model = DeviceListModel()
        model.update([{'deviceId': 'usb:1', 'name': 'Mouse', 'batteryText': '50%'}])
        persistent = model.index(0, 0)
        model.update([{'deviceId': 'usb:1', 'name': 'Mouse', 'batteryText': '51%'}])
        self.assertEqual(model.rowCount(), 1)
        self.assertTrue(persistent.isValid())
        self.assertEqual(model.data(model.index(0, 0), model.ObjectRole)['batteryText'], '51%')
        model.update([])
        self.assertEqual(model.rowCount(), 0)
        del app


if __name__ == '__main__':
    unittest.main()
