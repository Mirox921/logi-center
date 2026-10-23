import unittest
from discovery import Epoch,DeviceMonitor
from execution import CURRENT_CANCEL,command,Fault,FaultCode

class Discovery(unittest.TestCase):
    def test_rapid_reconnect_invalidates_old_work_only(self):
        epoch=Epoch();first=epoch.token();epoch.invalidate();second=epoch.token();epoch.invalidate()
        self.assertTrue(first.is_set());self.assertTrue(second.is_set());self.assertFalse(epoch.token().is_set())
        self.assertEqual(epoch.generation,2)
    def test_context_cancels_commands_without_launch(self):
        import sys
        epoch=Epoch();token=epoch.token();epoch.invalidate();context=CURRENT_CANCEL.set(token)
        try:
            with self.assertRaises(Fault) as error:command([sys.executable,'-c','raise RuntimeError()'])
            self.assertEqual(error.exception.code,FaultCode.CANCELLED)
        finally:CURRENT_CANCEL.reset(context)
    def test_stopping_unused_monitor_is_safe(self):
        monitor=DeviceMonitor(lambda reason:None);monitor.stop();monitor.stop()
        self.assertTrue(monitor.stop_event.is_set())
    def test_udev_callback_uses_current_single_device_signature(self):
        from unittest.mock import Mock
        callback=Mock();monitor=DeviceMonitor(callback)
        monitor._udev_event(Mock(subsystem='hidraw',action='remove'))
        callback.assert_called_once_with('devices')
        monitor.stop();monitor._udev_event(Mock(subsystem='hidraw',action='add'))
        self.assertEqual(callback.call_count,1)
