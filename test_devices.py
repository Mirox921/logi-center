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
        adapter=SimulationAdapter();self.assertEqual(len(adapter.discover()),8)
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
        cap=HeadsetAdapter(runner).discover()[0].capabilities[0]
        self.assertIsNone(cap.value);self.assertFalse(cap.readable)

    def test_kernel_bitmask_preserves_word_boundaries(self):
        from devices import parse_key_mask
        self.assertEqual(parse_key_mask('10000 0 0 0 0',64),1<<272)
        self.assertEqual(parse_key_mask('1 0',32),1<<32)
