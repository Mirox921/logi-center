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

    def test_unplug_does_not_reuse_model_name_as_presence(self):
        from discovery import MousePresence
        state=MousePresence();state.update([('mouse','Logitech G502 HERO')])
        self.assertIs(state.connected,True)
        state.invalidate();self.assertIsNone(state.connected)
        state.update([])
        self.assertEqual(state.name,'Logitech G502 HERO');self.assertIs(state.connected,False)
        state.update([('mouse-new','Logitech G502 HERO')]);self.assertIs(state.connected,True)
    def test_backend_failure_does_not_claim_connection_or_unplug(self):
        from discovery import MousePresence
        state=MousePresence('G502',True);state.update([],error=True)
        self.assertIsNone(state.connected)
