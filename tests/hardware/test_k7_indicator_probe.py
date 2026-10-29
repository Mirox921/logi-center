"""Read-only K7 probe: fake transport, no physical device access."""
import unittest
from scripts.k7_indicator_probe import snapshot


class FakeTransport:
    def __init__(self, connected):
        self.connected = connected
        self.commands = []

    def exchange(self, report, command):
        self.commands.append((report, command))
        if command == 0x1b:
            return bytes([1, 1, 0, 100, 0, 3, 1, 0, 0, 255, 0, 0, 255, 0, 0])
        if command == 0x06:
            if not self.connected:
                return bytes(19)
            identity = bytearray(19)
            identity[0:4] = bytes.fromhex('37385041')
            identity[8:11] = bytes([9, 38, 1])
            return identity
        if command == 0x67:
            body = bytearray(63)
            body[0] = 0
            body[2] = 0x30
            for i in range(6):
                body[4 + 2*i:6 + 2*i] = (400 + i*400).to_bytes(2, 'little')
            body[16] = 6
            return body
        raise AssertionError('Unexpected command')


class K7ProbeTests(unittest.TestCase):
    def test_disconnected_receiver_never_reads_config_or_writes(self):
        device = FakeTransport(False)
        result = snapshot(device)
        self.assertFalse(result['mouse_link'])
        self.assertIsNone(result['charging'])
        self.assertEqual(result['rgb_effect_id'], 1)
        self.assertEqual(device.commands, [(0x11, 0x06), (0x11, 0x1b)])

    def test_connected_mouse_reports_charge_and_dpi_separately_from_led(self):
        device = FakeTransport(True)
        result = snapshot(device)
        self.assertEqual((result['battery'], result['charging'], result['profile']), (38, True, 1))
        self.assertEqual((result['dpi'], result['dpi_stage']), (400, 1))
        self.assertNotIn('top_led_on', result)
        self.assertNotIn('bottom_led_on', result)
        self.assertEqual(device.commands, [(0x11, 0x06), (0x11, 0x1b), (0x12, 0x67)])
