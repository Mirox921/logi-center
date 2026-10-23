import unittest
from backend import mouse_list, solaar_settings, volume
class Adapters(unittest.TestCase):
    def test_list(self):
        self.assertEqual(mouse_list('thundering-gerbil:   Logitech G305\n'),[('thundering-gerbil','Logitech G305')])
    def test_settings(self):
        text='# LED Control\n# Description\n#   possible values: on/true/t/yes/y/1 or off/false\nrgb_control = False\n\n# Sleep Timeout\n#   possible values: one of [ Disabled, 2 Minutes, 5 Minutes ], or higher/lower\nrgb_sleep_timeout = 5 Minutes\n'
        result=solaar_settings(text)
        self.assertEqual(result[0]['key'],'rgb_control')
        self.assertEqual(result[0]['choices'],['true','false'])
        self.assertEqual(result[1]['choices'],['Disabled','2 Minutes','5 Minutes'])
        self.assertEqual(result[1]['label'],'Sleep Timeout')
    def test_volume(self):
        self.assertEqual(volume({'volume':{'front-left':{'value_percent':'75%'}}}),75)
if __name__=='__main__':unittest.main()

class Batteries(unittest.TestCase):
    def test_coarse_level_is_not_percent(self):
        from backend import battery_label
        text,_=battery_label(dict(online=True,percent=None,level='Full',status='Discharging'))
        self.assertEqual(text,'Высокий заряд')
        self.assertNotIn('%',text)
    def test_disconnected_discards_old_percentage(self):
        from backend import battery_label
        text,_=battery_label(dict(online=False,percent=99,level='Full',status='Discharging'))
        self.assertNotIn('99',text)
    def test_sysfs_filter_and_read(self):
        from backend import wireless_batteries
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as root:
            device=Path(root)/'hidpp_battery_1';device.mkdir()
            (device/'uevent').write_text('POWER_SUPPLY_SCOPE=Device\nPOWER_SUPPLY_MANUFACTURER=Logitech\nPOWER_SUPPLY_MODEL_NAME=G515 LS TKL\nPOWER_SUPPLY_CAPACITY=99\nPOWER_SUPPLY_ONLINE=1\n')
            found=wireless_batteries(root)
            self.assertEqual(found[0]['percent'],99)
            self.assertTrue(found[0]['online'])

class Persistence(unittest.TestCase):
    def test_preferences_roundtrip_and_corrupt_file(self):
        from backend import load_preferences,save_preferences
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'preferences.json'
            expected={'light_effect':1,'light_color':'0xffffff','sidetone':'32','preset':'Голос'}
            save_preferences(expected,path)
            self.assertEqual(load_preferences(path),expected)
            path.write_text('{broken')
            self.assertEqual(load_preferences(path),{})
    def test_solaar_tagged_color_loads_without_object_construction(self):
        from backend import saved_keyboard
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'config.yaml'
            path.write_text('- 1.1.20\n- _NAME: G515 LS TKL\n  rgb_zone_1: !LEDEffectSetting {ID: 1, color: 0xffffff}\n  rgb_idle_timeout: 0\n')
            data=saved_keyboard(path)
            self.assertEqual(data['rgb_zone_1']['color'],'0xffffff')
            self.assertEqual(data['rgb_idle_timeout'],'0')

class PresetImport(unittest.TestCase):
    def test_import_and_collision_preserves_original(self):
        from backend import import_preset
        from pathlib import Path
        import tempfile,json
        with tempfile.TemporaryDirectory() as root:
            source=Path(root)/'Voice.json';source.write_text(json.dumps({'input':{'plugins_order':[]}}))
            destination=Path(root)/'presets'
            self.assertEqual(import_preset(source,destination),('Voice',['input']))
            self.assertEqual(import_preset(source,destination),('Voice (2)',['input']))
            self.assertTrue((destination/'input/Voice.json').exists())
    def test_reject_unrelated_json(self):
        from backend import import_preset
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            source=Path(root)/'other.json';source.write_text('{"other":{}}')
            with self.assertRaises(ValueError):import_preset(source,Path(root)/'presets')

class KeyboardConnection(unittest.TestCase):
    def test_ping_only_and_close_even_when_offline(self):
        from backend import keyboard_online
        from pathlib import Path
        from unittest.mock import Mock
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            node=Path(root)/'hidraw8/device';node.mkdir(parents=True)
            (node/'uevent').write_text('HID_NAME=Logitech G515 LS TKL\nHID_PHYS=usb/input2:1\n')
            transport=Mock();transport.open_path.return_value=42;transport.ping.return_value=None
            self.assertIs(keyboard_online(root,transport),False)
            transport.ping.assert_called_once_with(42,1,long_message=True)
            transport.close.assert_called_once_with(42)
            self.assertEqual([x[0] for x in transport.method_calls],['open_path','ping','close'])
    def test_unplugged_is_not_connected(self):
        from backend import keyboard_online
        import tempfile
        with tempfile.TemporaryDirectory() as root:self.assertIs(keyboard_online(root),False)
