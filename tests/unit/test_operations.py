import unittest
from logi_center.core.services.operations import Plan,Observation,State,perform,plan_for
from logi_center.core.services.execution import Fault,FaultCode,command
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
    def test_led_effect_timing_is_numeric_and_cache_only(self):
        runner=Mock(side_effect=['','LED: 0, depth: rgb, mode: cycle, duration: 8000, brightness: 255'])
        result=perform(plan_for(['ratbagctl','mouse','profile','0','led','0','set','duration','8000']),runner)
        self.assertEqual((result.state,result.requested,result.actual,result.source),(State.SENT,8000,8000,'backend_cache'))
    def test_cancel_before_command(self):
        event=Event();event.set();runner=Mock()
        self.assertEqual(perform(Plan(['writer']),runner,cancel=event).state,State.CANCELLED);runner.assert_not_called()
    def test_real_process_timeout_without_hardware(self):
        import sys
        with self.assertRaises(Fault) as context:command([sys.executable,'-c','import time;time.sleep(5)'],timeout=.1)
        self.assertEqual(context.exception.code,FaultCode.TIMEOUT)
    def test_key_and_disabled_readback_formats(self):
        from logi_center.core.services.operations import read_action
        self.assertEqual(read_action("Button: 2 is mapped to key 'KEY_F9'"),['key','KEY_F9'])
        self.assertEqual(read_action('Button: 2 is mapped to none'),['disabled'])
    def test_macro_tap_and_press_release_are_equivalent(self):
        from logi_center.core.services.operations import same
        self.assertTrue(same(['macro','KEY_C'],['macro','+KEY_C','-KEY_C']))

    def test_bypass_boolean_readback(self):
        runner=Mock(side_effect=['','false'])
        result=perform(plan_for(['easyeffects','-b','2']),runner)
        self.assertEqual(result.state,State.SENT)
        self.assertEqual(result.actual,False)
    def test_unrecognized_readback_is_not_confirmed(self):
        runner=Mock(side_effect=['','unexpected'])
        result=perform(plan_for(['easyeffects','-b','2']),runner)
        self.assertEqual(result.state,State.SENT)
        self.assertIsNotNone(result.fault)

    def test_access_and_unsupported_write_results_are_distinct(self):
        for code,state in [(FaultCode.PERMISSION,State.PERMISSION),(FaultCode.BACKEND_UNSUPPORTED,State.UNSUPPORTED)]:
            result=perform(Plan(['writer']),Mock(side_effect=Fault(code,'writer','test')))
            self.assertEqual(result.state,state)
    def test_local_observation_never_becomes_device_confirmation(self):
        result=perform(Plan(['writer'],1,lambda run:Observation(1,'local_saved_settings')),Mock())
        self.assertEqual(result.state,State.LOCAL)
