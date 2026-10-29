"""RGB trial tests use an in-memory transport; no hardware writes."""
import unittest
from unittest.mock import patch
from scripts.k7_rgb_trial import main, trial


class FakeTransport:
    def __init__(self, original):
        self.record = bytes(original)
        self.writes = []
        self.fail_readback = False

    def exchange(self, report, command, args=b'', reply=True):
        if (report, command) == (0x11, 0x2b):
            self.writes.append(bytes(args))
            if not self.fail_readback or len(self.writes) > 1:
                self.record = bytes(args)
            return None
        if (report, command) == (0x11, 0x1b):
            return self.record
        raise AssertionError('Unexpected HID command')


class K7RgbTrialTests(unittest.TestCase):
    def setUp(self):
        self.original = bytes([1, 1, 0, 100, 0, 3, 1, 0, 0, 255, 0, 0, 255, 0, 0])

    def test_static_trial_reads_back_and_restores_original_record(self):
        device = FakeTransport(self.original)
        observed = []
        trial(device, self.original, pause=lambda seconds:observed.append((seconds,device.record)), settle=lambda _:None)
        self.assertEqual(len(device.writes), 2)
        self.assertEqual(device.writes[0][1], 6)
        self.assertEqual(device.writes[0][8:11], b'\xff\x00\x00')
        self.assertEqual(observed[0][1], device.writes[0])
        self.assertEqual(device.record, self.original)

    def test_mismatched_readback_still_restores_without_retry(self):
        device = FakeTransport(self.original)
        device.fail_readback = True
        with self.assertRaisesRegex(RuntimeError, 'readback differed'):
            trial(device, self.original, pause=lambda _:None, settle=lambda _:None)
        self.assertEqual(device.writes, [device.writes[0], self.original])
        self.assertEqual(device.record, self.original)

    def test_incomplete_snapshot_never_writes(self):
        device = FakeTransport(self.original)
        with self.assertRaises(ValueError):
            trial(device, self.original[:-1])
        self.assertEqual(device.writes, [])

    def test_wrong_logical_mouse_identity_stops_before_rgb_write(self):
        class WrongMouse(FakeTransport):
            def __enter__(self):return self
            def __exit__(self, *unused):return None
            def read(self):return {'identity':{'vid':0x3837,'pid':0x9999}}
        device = WrongMouse(self.original)
        item = {'vid':'3837','pid':'1001','name':'MCHOSE K7 Ultra','node':'fake','physical':'fake'}
        with patch('scripts.k7_rgb_trial.candidates', return_value=[item]), \
             patch('scripts.k7_rgb_trial.Transport', return_value=device):
            with self.assertRaisesRegex(RuntimeError, 'identity mismatch'):
                main(['--confirm','K7-STATIC-RED-RESTORE'])
        self.assertEqual(device.writes, [])
