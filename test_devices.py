import unittest
from unittest.mock import Mock
from devices import Device,Capability,DeviceManager,mouse_capabilities,HeadsetAdapter
from simulation import SimulationAdapter
from operations import State
from execution import Fault
class Devices(unittest.TestCase):
    def test_same_model_different_physical_paths_stay_separate(self):
        records=[Device('a','Same model','mouse','hid',physical='/usb/1'),Device('b','Same model','mouse','ratbag',physical='/usb/2')]
        self.assertEqual(len(DeviceManager.merge(records)),2)
    def test_same_exact_identity_merges_capabilities(self):
        records=[Device('a','Unit','audio','pactl',physical='/usb/1',capabilities=[Capability('volume','pactl')]),Device('b','Unit','audio','headsetcontrol',physical='/usb/1',capabilities=[Capability('sidetone','headsetcontrol')])]
        merged=DeviceManager.merge(records);self.assertEqual(len(merged),1);self.assertEqual(len(merged[0].capabilities),2)
    def test_ambiguous_records_without_physical_id_not_merged(self):
        self.assertEqual(len(DeviceManager.merge([Device('a','Mouse','mouse','a'),Device('b','Mouse','mouse','b')])),2)
    def test_conflicting_backend_requires_explicit_selection(self):
        manager=DeviceManager();manager.devices=[Device('a','Unit','mouse','one',capabilities=[Capability('dpi',b,True,writable=True) for b in ['one','two']])]
        with self.assertRaises(Fault):manager.route('a','dpi')
        self.assertEqual(manager.route('a','dpi','two').backend,'two')
    def test_unknown_mouse_capabilities_are_not_assumed(self):
        self.assertEqual(mouse_capabilities({'profiles':[]}),[])
    def test_simulated_data_never_becomes_hardware_confirmation(self):
        adapter=SimulationAdapter();self.assertEqual(len(adapter.discover()),15)
        self.assertEqual(adapter.apply('gaming-mouse','dpi',1600).state,State.SENT)
        self.assertEqual(adapter.apply('disconnect','dpi',1600).state,State.DISCONNECTED)
        self.assertEqual(adapter.apply('partial','dpi',1600).state,State.UNSUPPORTED)
    def test_headset_numeric_unknown_capability_is_ignored(self):
        adapter=HeadsetAdapter(Mock(return_value='{"devices":[{"capabilities":[1,"CAP_SIDETONE"]}]}'))
        self.assertEqual(len(adapter.discover()[0].capabilities),1)
    def test_unique_kernel_identity_links_headset_audio_endpoint(self):
        records=[Device('pulse','Sound','audio','pactl',physical='/usb/1',vid='046d',pid='0aaa'),Device('headset','Sound','audio','headsetcontrol',vid='046d',pid='0aaa')]
        DeviceManager.link_physical(records)
        self.assertEqual(len(DeviceManager.merge(records)),1)
    def test_two_identical_units_cannot_be_linked_by_vid_pid(self):
        records=[Device('one','Same','mouse','linux-input',physical='/usb/1',vid='046d',pid='1234'),Device('two','Same','mouse','linux-input',physical='/usb/2',vid='046d',pid='1234'),Device('r','Same','mouse','ratbagctl',vid='046d',pid='1234')]
        DeviceManager.link_physical(records);self.assertEqual(len(DeviceManager.merge(records)),3)
    def test_lazy_mouse_discovery_uses_only_one_inventory_command(self):
        from devices import RatbagAdapter
        runner=Mock(return_value='mouse: Generic vendor mouse')
        devices=RatbagAdapter(runner).discover();self.assertEqual(len(devices),1);runner.assert_called_once_with(['ratbagctl','list'])

    def test_unique_ratbag_model_resolves_only_unique_kernel_unit(self):
        from devices import RatbagAdapter
        runner=Mock(return_value='mouse: Logitech G502 HERO Gaming Mouse')
        lookup=Mock(return_value={'Logitech G502 HERO Gaming Mouse':('046d','c08b')})
        ratbag=RatbagAdapter(runner,model_lookup=lookup).discover()[0]
        input_mouse=Device('input','Logitech G502 HERO','mouse','linux-input',physical='/usb/1',vid='046d',pid='c08b',connection='usb')
        records=[input_mouse,ratbag]
        DeviceManager.link_physical(records)
        merged=DeviceManager.merge(records)
        self.assertEqual(len(merged),1)
        self.assertEqual(merged[0].backends,['linux-input','ratbagctl'])
        self.assertEqual(merged[0].connection,'usb')
        runner.assert_called_once_with(['ratbagctl','list'])

    def test_ratbag_duplicate_names_and_kernel_units_stay_distinct(self):
        from devices import RatbagAdapter
        lookup=lambda:{'Same Mouse':('046d','c08b')}
        ratbag=RatbagAdapter(Mock(return_value='one: Same Mouse\ntwo: Same Mouse'),model_lookup=lookup).discover()
        self.assertTrue(all(not d.vid for d in ratbag))
        records=[Device('one','Same Mouse','mouse','linux-input',physical='/usb/1',vid='046d',pid='c08b'),Device('two','Same Mouse','mouse','linux-input',physical='/usb/2',vid='046d',pid='c08b'),*ratbag]
        DeviceManager.link_physical(records)
        self.assertEqual(len(DeviceManager.merge(records)),4)

    def test_ratbag_metadata_failure_keeps_separate_records(self):
        from devices import RatbagAdapter
        def fail():raise RuntimeError('daemon unavailable')
        device=RatbagAdapter(Mock(return_value='mouse: Same Mouse'),model_lookup=fail).discover()[0]
        self.assertEqual((device.vid,device.pid),('',''))

    def test_merged_record_retains_each_backend_selector(self):
        a=Device('a','Sound','audio','pactl','sink-name',physical='/usb/1')
        b=Device('b','Sound','audio','headsetcontrol','046d:0aaa',physical='/usb/1')
        device=DeviceManager.merge([a,b])[0]
        self.assertEqual(device.targets['headsetcontrol'],['046d:0aaa'])
        self.assertEqual(device.targets['pactl'],['sink-name'])
    def test_operation_evidence_keeps_server_and_device_distinct(self):
        from operations import Result
        manager=DeviceManager();cap=Capability('dpi','ratbagctl',True,writable=True)
        manager.devices=[Device('m','Mouse','mouse','ratbagctl','m',capabilities=[cap])]
        manager.record_operation(['ratbagctl','m','profile','0','resolution','0','dpi','set','1600'],Result(State.SENT,'ratbagctl',1600,1600,'backend_cache'))
        self.assertNotIn('command_confirmed',cap.evidence)
        self.assertEqual(cap.last_operation['state'],'sent_unverified')

    def test_missing_audio_fields_do_not_become_invented_controls(self):
        from devices import PulseAdapter
        runner=Mock(return_value='[{"name":"audio","index":1}]')
        self.assertTrue(all(not d.capabilities for d in PulseAdapter(runner).discover()))
    def test_headset_unavailable_battery_is_not_a_negative_percentage(self):
        runner=Mock(return_value='{"devices":[{"id_vendor":"0x046d","id_product":"0x0aaa","capabilities":["CAP_BATTERY_STATUS"],"battery":{"status":"BATTERY_UNAVAILABLE","level":-1}}]}')
        device=HeadsetAdapter(runner).discover()[0]
        marker=next(c for c in device.capabilities if c.name=='battery_present')
        self.assertFalse(marker.value);self.assertEqual(marker.source,'model_spec')
        self.assertFalse(any(c.name in ('battery_status','charging') for c in device.capabilities))

    def test_unknown_wireless_headset_does_not_inherit_wired_exception(self):
        runner=Mock(return_value='{"devices":[{"id_vendor":"0x046d","id_product":"0x0aba","capabilities":["CAP_BATTERY_STATUS"],"battery":{"status":"BATTERY_UNAVAILABLE","level":-1}}]}')
        device=HeadsetAdapter(runner).discover()[0]
        self.assertIsNone(next(c for c in device.capabilities if c.name=='battery_status').value)
        self.assertFalse(any(c.name=='battery_present' for c in device.capabilities))

    def test_headset_charging_is_reported_independently_of_percentage(self):
        runner=Mock(return_value='{"devices":[{"id_vendor":"0x046d","id_product":"0x0aaa","capabilities":["CAP_BATTERY_STATUS"],"battery":{"status":"BATTERY_CHARGING","level":-1}}]}')
        device=HeadsetAdapter(runner).discover()[0]
        self.assertIsNone(next(c for c in device.capabilities if c.name=='battery_status').value)
        charging=next(c for c in device.capabilities if c.name=='charging')
        self.assertTrue(charging.readable);self.assertTrue(charging.value)

    def test_kernel_bitmask_preserves_word_boundaries(self):
        from devices import parse_key_mask
        self.assertEqual(parse_key_mask('10000 0 0 0 0',64),1<<272)
        self.assertEqual(parse_key_mask('1 0',32),1<<32)

    def test_ratbag_selector_collision_never_merges_or_enables_writes(self):
        from devices import RatbagAdapter
        devices=RatbagAdapter(Mock(return_value='same: Mouse one\nsame: Mouse two')).discover()
        self.assertEqual(len(devices),2);self.assertNotEqual(devices[0].id,devices[1].id)
        self.assertTrue(all(d.faults and not d.capabilities for d in devices))

    def test_receiver_child_slots_stay_distinct(self):
        import tempfile
        from pathlib import Path
        from devices import InputAdapter
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);usb=root/'usb';usb.mkdir();(usb/'idVendor').write_text('046d');(usb/'idProduct').write_text('c52b')
            for index in [1,2]:
                node=usb/('slot'+str(index));(node/'capabilities').mkdir(parents=True)
                (node/'name').write_text('Identical keyboard');(node/'phys').write_text('usb-1/input2:'+str(index))
                (node/'capabilities/key').write_text(hex((1<<14)|(1<<30)|(1<<57))[2:])
                event=root/'class'/('event'+str(index));event.mkdir(parents=True);(event/'device').symlink_to(node)
            self.assertEqual(len(InputAdapter(root/'class').discover()),2)

    def test_i2c_and_i8042_input_ids_are_not_misreported_as_usb(self):
        import tempfile
        from pathlib import Path
        from devices import InputAdapter
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);records=[]
            for index,bus,name in [(1,'0018','MSNB0001:00 04F3:30AA Mouse'),(2,'0011','AT Translated Set 2 keyboard')]:
                node=root/'devices'/('device'+str(index));(node/'capabilities').mkdir(parents=True);(node/'id').mkdir()
                (node/'name').write_text(name);(node/'phys').write_text('');(node/'id'/'bustype').write_text(bus)
                (node/'id'/'vendor').write_text('04f3');(node/'id'/'product').write_text('30aa')
                (node/'capabilities'/'key').write_text(hex((1<<14)|(1<<30)|(1<<57) if 'keyboard' in name else (1<<272))[2:])
                event=root/'class'/('event'+str(index));event.mkdir(parents=True);(event/'device').symlink_to(node)
            devices=InputAdapter(root/'class').discover()
            self.assertEqual({d.name:d.connection for d in devices},{'MSNB0001:00 04F3:30AA Mouse':'internal','AT Translated Set 2 keyboard':'internal'})

    def test_name_search_is_case_insensitive_and_normalizes_whitespace(self):
        from devices import matches_name
        self.assertTrue(matches_name('Logitech  G502 HERO',' logitech g502 '))
        self.assertTrue(matches_name('Клавиатура','КЛАВ'))
        self.assertTrue(matches_name('Any device','   '))
        self.assertFalse(matches_name('Logitech G305','G502'))
