import unittest
from unittest.mock import Mock
from solaar_adapter import probe,choice_plan
from operations import perform,State
class SolaarProbes(unittest.TestCase):
    def test_only_reported_choices_become_writable_and_verified(self):
        runner=Mock(return_value='# Backlight\n#   possible values: on/true/t/yes/y/1 or off/false\nbacklight = True')
        target,caps,faults=probe({'_NAME':'Other keyboard','_serial':'ABCD1234','backlight':'true'},runner)
        self.assertFalse(faults);self.assertTrue(caps[0].writable)
        result=perform(choice_plan(target,caps[0],'false'),Mock(side_effect=['','# Backlight\nbacklight = False']))
        self.assertEqual(result.state,State.CONFIRMED)
    def test_complex_settings_not_probed_and_unknown_values_read_only(self):
        runner=Mock(return_value='dpi = 800')
        _,caps,_=probe({'_serial':'ABCD1234','dpi':'800','rgb_zone':{'ID':1}},runner)
        runner.assert_called_once();self.assertFalse(caps[0].writable)

    def test_reset_setting_is_never_enabled_for_writes(self):
        runner=Mock(return_value='# Reset\n#   possible values: on/true/t/yes/y/1 or off/false\nfactory_reset = False')
        _,caps,_=probe({'_serial':'ABCD1234','factory_reset':'false'},runner)
        self.assertFalse(caps[0].writable)
