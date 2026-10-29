import unittest
from logi_center.core.services.audio_status import device_available,describe_availability


class AudioAvailability(unittest.TestCase):
    def test_hdmi_port_status_is_respected(self):
        self.assertFalse(device_available({'name':'hdmi','ports':[{'availability':'no'}]}))
        self.assertTrue(device_available({'name':'hdmi','ports':[{'availability':'yes'}]}))

    def test_suspend_is_available_not_disconnected(self):
        self.assertTrue(device_available({'state':'SUSPENDED'}))
        self.assertTrue(device_available({'state':'IDLE'}))

    def test_unknown_remains_unknown(self):
        self.assertIsNone(device_available({'name':'unknown'}))
        self.assertEqual(describe_availability({'name':'unknown'}),'unknown')

    def test_active_port_takes_precedence(self):
        device={'active_port':{'availability':'no'},'ports':[{'availability':'yes'}]}
        self.assertFalse(device_available(device))


if __name__=='__main__':unittest.main()
