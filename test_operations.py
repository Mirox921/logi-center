import unittest
from operations import Plan,Observation,State,perform,plan_for
from execution import Fault,FaultCode,command
from threading import Event
from unittest.mock import Mock

class Verification(unittest.TestCase):
    def test_confirmed_device(self):
        r=perform(Plan(['writer'],20,lambda run:Observation(20,'device')),Mock(return_value=''))
        self.assertEqual(r.state,State.CONFIRMED)
    def test_cache_is_never_hardware_confirmation(self):
        r=perform(Plan(['writer'],'ffffff',lambda run:Observation('ffffff','backend_cache')),Mock())
        self.assertEqual(r.state,State.SENT)
    def test_mismatch(self):
        r=perform(Plan(['writer'],20,lambda run:Observation(10,'device')),Mock())
        self.assertEqual((r.state,r.requested,r.actual),(State.MISMATCH,20,10))
    def test_no_readback(self):self.assertEqual(perform(Plan(['writer']),Mock()).state,State.SENT)
    def test_disconnect_during_read(self):
        def read(run):raise Fault(FaultCode.DISCONNECTED,'device','offline')
        self.assertEqual(perform(Plan(['writer'],1,read),Mock()).state,State.DISCONNECTED)
    def test_missing_backend(self):
        r=perform(Plan(['writer']),Mock(side_effect=Fault(FaultCode.MISSING,'writer','missing')))
        self.assertEqual(r.state,State.ERROR)
    def test_audio_volume_tolerance(self):
        runner=Mock(side_effect=['','[{"index":1,"name":"mic","volume":{"mono":{"value_percent":"49%"}}}]'])
        self.assertEqual(perform(plan_for(['pactl','set-source-volume','mic','50%']),runner).state,State.CONFIRMED)
    def test_led_cached_color_mismatch(self):
        runner=Mock(side_effect=['','LED: 0, depth: rgb, mode: on, color: ffdc00'])
        r=perform(plan_for(['ratbagctl','mouse','profile','3','led','0','set','color','ffffff']),runner)
        self.assertEqual(r.state,State.MISMATCH)
    def test_cancel_before_command(self):
        event=Event();event.set();runner=Mock()
        self.assertEqual(perform(Plan(['writer']),runner,cancel=event).state,State.CANCELLED);runner.assert_not_called()
    def test_real_process_timeout_without_hardware(self):
        import sys
        with self.assertRaises(Fault) as context:command([sys.executable,'-c','import time;time.sleep(5)'],timeout=.1)
        self.assertEqual(context.exception.code,FaultCode.TIMEOUT)
