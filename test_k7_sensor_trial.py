import copy
import unittest
from scripts.k7_sensor_trial import trial
from test_k7_settings import NativeTransport


class K7SensorTrial(unittest.TestCase):
    def test_toggle_and_restore_only_requested_flag(self):
        for field,bit in [('motion_sync',16),('ripple',4),('angle_snap',8)]:
            native=NativeTransport();original=bytes(native.raw);writes=[]
            def write(state,key,value):
                self.assertEqual(key,field);writes.append(value)
                native.raw[17]=(native.raw[17]&~bit)|(bit if value else 0)
            result=trial(field,native.read,write)
            self.assertTrue(result['restored']);self.assertEqual(len(writes),2)
            self.assertEqual(bytes(native.raw),original)

    def test_ignored_write_is_not_success_or_retried(self):
        native=NativeTransport();writes=[]
        with self.assertRaisesRegex(RuntimeError,'did not read back'):
            trial('motion_sync',native.read,lambda state,key,value:writes.append(value))
        self.assertEqual(len(writes),1)

    def test_failed_response_can_restore_only_after_fresh_evidence(self):
        native=NativeTransport();original=bytes(native.raw);writes=[]
        def write(state,key,value):
            writes.append(value);native.raw[17]=(native.raw[17]&~16)|(16 if value else 0)
            if len(writes)==1:raise OSError('Setting response failed')
        with self.assertRaises(OSError):trial('motion_sync',native.read,write)
        self.assertEqual(bytes(native.raw),original);self.assertEqual(len(writes),2)

    def test_collateral_or_profile_change_blocks_recovery_writes(self):
        for offset in (0,17,44):
            native=NativeTransport();writes=[]
            def write(state,key,value):writes.append(value);native.raw[offset]^=1
            with self.assertRaisesRegex(RuntimeError,'Unexpected configuration'):
                trial('motion_sync',native.read,write)
            self.assertEqual(len(writes),1)
