import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from logi_center.core.devices.device_presentation import (dashboard_devices, device_category, image_key,
                                 group_presentations, model_name, presentation)
from logi_center.core.capabilities.model import Capability
from logi_center.core.devices.devices import Device, DeviceManager


class PresentationTests(unittest.TestCase):
    def setUp(self):
        from logi_center.i18n import set_language
        set_language("ru")

    def device(self, **kwargs):
        values = dict(id='x1', name='Unknown USB Mouse', kind='mouse', backend='linux-input',
                      connection='usb', connected=True)
        values.update(kwargs)
        return Device(**values)

    def test_internal_pointer_uses_transport_classification_and_friendly_name(self):
        device = self.device(name='MSNB0001:00 04F3:30AA Mouse', connection='internal')
        self.assertEqual(device_category(device), 'builtin')
        self.assertEqual(model_name(device), 'Встроенный указатель')
        self.assertEqual(image_key(device), 'pointer_generic')

    def test_i2c_pointer_is_internal_even_if_upstream_transport_field_is_misclassified(self):
        device = self.device(name='MSNB0001:00 04F3:30AA Mouse', connection='usb',
                             physical='/sys/devices/platform/i2c-3/i2c-ELAN/0018:04F3:30AA/input/input16')
        self.assertEqual(device_category(device), 'builtin')
        self.assertEqual(model_name(device), 'Встроенный указатель')
        self.assertEqual(image_key(device), 'pointer_generic')

    def test_exact_known_models_use_verified_names_and_generic_class_art(self):
        mouse = self.device(vid='3837', pid='1001')
        keyboard = self.device(id='k1', kind='keyboard', vid='41e4', pid='2116', name='USB Keyboard')
        self.assertEqual(model_name(mouse), 'MCHOSE K7 Ultra')
        self.assertEqual(model_name(keyboard), 'MCHOSE Ace68-II')
        self.assertEqual(image_key(mouse), 'mouse')
        self.assertEqual(image_key(keyboard), 'keyboard_65')

    def test_active_dashboard_excludes_disconnected_history_and_other_simulation_mode(self):
        active = self.device()
        disconnected = self.device(id='old', connected=False)
        simulated = self.device(id='sim', simulated=True)
        interface = self.device(id='interface', kind='interface')
        self.assertEqual(dashboard_devices([active, disconnected, simulated, interface]), [active])
        self.assertEqual(dashboard_devices([simulated], simulation=True), [simulated])

    def test_builtin_filter_does_not_remove_device_from_manager(self):
        built_in = self.device(id='internal', connection='internal')
        external = self.device(id='external')
        self.assertEqual(dashboard_devices([built_in, external], show_builtin=False), [external])
        self.assertEqual(len(DeviceManager.merge([built_in, external])), 2)

    def test_equal_vid_pid_never_merges_distinct_physical_units(self):
        one = self.device(id='one', vid='1234', pid='abcd', physical='/usb/one')
        two = self.device(id='two', vid='1234', pid='abcd', physical='/usb/two')
        self.assertEqual([d.id for d in DeviceManager.merge([one, two])], ['one', 'two'])

    def test_unknown_battery_is_not_zero_and_charging_requires_positive_evidence(self):
        device = self.device(capabilities=[Capability('battery_status', 'backend', True, True, False, False, None)])
        with tempfile.TemporaryDirectory() as temp:
            assets = Path(temp)
            (assets / 'mouse.svg').write_text('<svg/>')
            (assets / 'unknown.svg').write_text('<svg/>')
            card = presentation(device, assets)
        self.assertNotIn('0%', card['batteryText'])
        self.assertFalse(card['charging'])
        self.assertTrue(card['batteryAvailable'])
        self.assertEqual(card['batteryPercent'], -1)

    def test_connection_tag_does_not_repeat_device_category(self):
        mouse = self.device(connection='usb')
        internal = self.device(connection='internal', physical='/sys/devices/i2c-3/ELAN')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'mouse.svg').write_text('<svg/>')
            (root / 'pointer_generic.svg').write_text('<svg/>')
            (root / 'unknown.svg').write_text('<svg/>')
            self.assertEqual(presentation(mouse, root)['connectionTag'], 'USB')
            self.assertEqual(presentation(internal, root)['connectionTag'], 'I²C')

    def test_simulated_charge_and_charging_are_explicit_and_unknown_is_dotted(self):
        charging = self.device(simulated=True, connection='2.4g', capabilities=[
            Capability('battery_status', 'simulation', True, True, False, True, 64, 'simulation'),
            Capability('charging', 'simulation', True, True, False, True, True, 'simulation')])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'mouse.svg').write_text('<svg/>')
            (root / 'unknown.svg').write_text('<svg/>')
            card = presentation(charging, root)
        self.assertEqual(card['batteryPercent'], 64)
        self.assertEqual(card['connectionTag'], '2.4G')
        self.assertTrue(card['charging'])

    def test_cached_battery_is_not_presented_as_current_segment_value(self):
        cached = self.device(capabilities=[Capability('battery_status', 'test', True, True, False, True, 82, 'cache')])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'mouse.svg').write_text('<svg/>')
            (root / 'unknown.svg').write_text('<svg/>')
            card = presentation(cached, root)
        self.assertEqual(card['batteryPercent'], -1)
        self.assertIn('82%', card['batteryText'])
        self.assertIn('Сохранённое значение', card['batteryText'])

    def test_dashboard_sections_group_physical_types_and_keep_unknowns_visible(self):
        rows = [
            {'deviceId': 'm', 'kind': 'mouse', 'category': 'external'},
            {'deviceId': 'k', 'kind': 'keyboard', 'category': 'builtin'},
            {'deviceId': 'a', 'kind': 'audio', 'category': 'audio'},
            {'deviceId': 'x', 'kind': 'input', 'category': 'unknown'},
        ]
        groups = group_presentations(rows)
        self.assertEqual([row['deviceId'] for row in groups['external']], ['m'])
        self.assertEqual([row['deviceId'] for row in groups['builtin']], ['k'])
        self.assertEqual([row['deviceId'] for row in groups['audio']], ['a'])
        self.assertEqual([row['deviceId'] for row in groups['other']], ['x'])

    def test_simulation_names_follow_ui_language_and_are_not_mock_product_claims(self):
        from logi_center.i18n import set_language
        fixture = self.device(id='sim:simple-mouse', target='simple-mouse', simulated=True, name='Simple mouse')
        set_language('ru')
        self.assertEqual(model_name(fixture), 'Простая мышь · симуляция')
        set_language('en')
        self.assertEqual(model_name(fixture), 'Simple mouse · simulation')
        set_language('ru')

    def test_empty_capability_card_uses_plain_language(self):
        device = self.device(capabilities=[])
        with tempfile.TemporaryDirectory() as temp:
            assets = Path(temp)
            (assets / 'mouse.svg').write_text('<svg/>')
            (assets / 'unknown.svg').write_text('<svg/>')
            card = presentation(device, assets)
        self.assertEqual(card['settingsText'], 'Нет доступных настроек')
        self.assertEqual(card['availableSettings'], 0)

    def test_confirmed_touchpad_and_unclassified_pointer_have_distinct_labels(self):
        assets=Path(__file__).resolve().parents[2]/'assets/devices'
        device=self.device(connection='internal',physical='/i2c-3/pointer',vid='04f3',pid='30aa')
        unknown=presentation(device,assets)
        self.assertEqual(unknown['typeLabel'],'Тип не определён')
        self.assertEqual(unknown['artworkNote'],'Обобщённая графика')
        device.udev_properties={'ID_INPUT_TOUCHPAD':'1'}
        known=presentation(device,assets)
        self.assertEqual(known['typeLabel'],'Тачпад')
        self.assertEqual(known['artworkKey'],'touchpad')
        self.assertEqual(known['artworkNote'],'')

    def test_missing_asset_does_not_change_confirmed_physical_type(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root,'unknown.svg').write_text('<svg/>')
            device=self.device();device.udev_properties={'ID_INPUT_TOUCHPAD':'1'}
            row=presentation(device,root)
            self.assertEqual(row['typeLabel'],'Тачпад')
            self.assertEqual(row['artworkSource'],'fallback')

    def test_all_project_device_illustrations_are_well_formed_svg(self):
        assets = Path(__file__).resolve().parents[2] / 'assets' / 'devices'
        files = list(assets.glob('*.svg')) + list((assets.parent/'keyboards').glob('*.svg'))
        self.assertGreaterEqual(len(files), 10)
        for path in files:
            with self.subTest(path=path.name):
                ElementTree.parse(path)


if __name__ == '__main__':
    unittest.main()


class BatteryLayoutRules(unittest.TestCase):
    def test_segments_always_round_down(self):
        from logi_center.core.devices.device_presentation import battery_segments
        for value,expected in ((0,0),(1,0),(25,3),(46,5),(50,6),(99,11),(100,12)):
            self.assertEqual(battery_segments(value),expected)
        for value in (None,False,-1,101,float('nan')):self.assertEqual(battery_segments(value),0)

    def test_wired_no_battery_is_hidden_but_supported_usb_charging_is_retained(self):
        from logi_center.core.devices.device_presentation import battery_block_visible
        d=Device('wired','Keyboard','keyboard','linux-input',connection='usb')
        self.assertFalse(battery_block_visible(d))
        d.connection='bluetooth';self.assertTrue(battery_block_visible(d))
        d.capabilities=[Capability('battery_present','test',True,True,value=False,source='device')]
        self.assertFalse(battery_block_visible(d))
        d.connection='usb';d.capabilities=[Capability('battery_status','test',True,True,value=None,source='device')]
        self.assertTrue(battery_block_visible(d))

    def test_wired_pro_x_and_wireless_receiver_use_honest_labels(self):
        import json
        from unittest.mock import Mock
        from logi_center.adapters.external.headset_adapter import HeadsetAdapter
        from logi_center.core.devices.device_presentation import battery_block_visible, connection_label
        headset=HeadsetAdapter(Mock(return_value=json.dumps({'devices':[{
            'id_vendor':'0x046d','id_product':'0x0aaa',
            'capabilities':['CAP_BATTERY_STATUS'],
            'battery':{'status':'BATTERY_UNAVAILABLE','level':-1},
        }]}))).discover()[0]
        self.assertFalse(battery_block_visible(headset))
        headset.capabilities.append(Capability('battery_status','kernel-battery',True,True,value=50,source='kernel'))
        self.assertTrue(battery_block_visible(headset))
        self.assertEqual(connection_label(headset),'Аудио')
        mouse=Device('k7','MCHOSE K7 Ultra','mouse','mchose',vid='3837',pid='1001',connection='wireless')
        self.assertEqual(connection_label(mouse),'Беспроводное через USB-приёмник')
