"""G515 receiver/cable/auxiliary input scenarios, without opening hardware."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from logi_center.adapters.external.linux_input import InputAdapter,KernelBatteryAdapter
from logi_center.adapters.logitech.saved_solaar import SavedSolaarAdapter
from logi_center.adapters.logitech.solaar_write import battery_metadata
from logi_center.core.devices.devices import Device,DeviceManager
from logi_center.core.services.battery_service import collect,apply


class G515Transport(TestCase):
    def input_node(self,root,index,parent,hid,name,serial='',mouse=False):
        usb=root/parent;usb.mkdir(exist_ok=True)
        (usb/'idVendor').write_text('046d')
        (usb/'idProduct').write_text('c547' if parent.startswith('receiver') else 'c999')
        device=usb/hid;device.mkdir(exist_ok=True)
        (device/'uevent').write_text('HID_ID=0003:0000046D:000040B4')
        node=device/('input'+str(index));(node/'capabilities').mkdir(parents=True)
        (node/'id').mkdir();(node/'id/bustype').write_text('0003')
        (node/'name').write_text(name);(node/'uniq').write_text(serial)
        (node/'phys').write_text('usb/input'+str(index))
        bits=(1<<272) if mouse else (1<<14)|(1<<30)|(1<<57)
        (node/'capabilities/key').write_text(hex(bits)[2:])
        event=root/'class'/('event'+str(index));event.mkdir(parents=True)
        (event/'device').symlink_to(node)

    def test_receiver_wire_and_auxiliary_pointer_keep_one_keyboard_and_correct_transport(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.input_node(root,1,'receiver','slot1','G515 LS TKL','abcd1234')
            wireless=InputAdapter(root/'class').discover()[0]
            self.assertEqual(wireless.connection,'wireless')
            self.input_node(root,2,'cable','hid1','Logitech G515 LS TKL','abcd1234')
            self.input_node(root,3,'cable','hid2','Logitech G515 LS TKL Mouse',mouse=True)
            records=InputAdapter(root/'class').discover()
            keyboards=[d for d in records if d.kind=='keyboard']
            self.assertEqual(len(keyboards),1);self.assertEqual(keyboards[0].connection,'usb')
            self.assertEqual(keyboards[0].id,wireless.id)
            self.assertEqual(keyboards[0].pid,'c999')
            self.assertFalse(any(d.kind=='mouse' for d in records))
            self.assertEqual(len(keyboards[0].private_identity['usb_parents']),2)

    def test_identical_receiver_slots_and_unrelated_same_name_do_not_merge(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.input_node(root,1,'receiver','slot1','G515 LS TKL','abcd1234')
            self.input_node(root,2,'receiver','slot2','G515 LS TKL','ffff1234')
            self.input_node(root,3,'cable','hid1','Logitech G515 LS TKL','beef1234')
            self.input_node(root,4,'other','hid2','Logitech G515 LS TKL Mouse',mouse=True)
            devices=InputAdapter(root/'class').discover()
            self.assertEqual(sum(d.kind=='keyboard' for d in devices),3)
            self.assertEqual(sum(d.kind=='mouse' for d in devices),1)

    def test_multiple_evdev_collections_of_one_keyboard_hid_are_one_device(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            for index in (1,2):self.input_node(root,index,'cable','hid1','Logitech G515 LS TKL')
            self.assertEqual(len(InputAdapter(root/'class').discover()),1)

    def test_saved_serial_unit_alias_reconciles_paths_before_battery_association(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.input_node(root,1,'receiver','slot1','G515 LS TKL','abcd1234')
            self.input_node(root,2,'cable','hid1','Logitech G515 LS TKL','deaf5678')
            config=root/'solaar.yaml'
            config.write_text('- _NAME: G515 LS TKL\n  _serial: ABCD1234\n  _unitId: DEAF5678\n')
            battery=Device('power','Battery','battery','kernel-battery',physical=str(root/'cable'))
            adapter=SimpleNamespace(name='test',discover=lambda:[battery])
            manager=DeviceManager([InputAdapter(root/'class'),KernelBatteryAdapter(root/'absent'),
                adapter,SavedSolaarAdapter(config)])
            manager.discover()
            keyboards=manager.active('keyboard')
            self.assertEqual(len(keyboards),1)
            self.assertEqual(keyboards[0].connection,'usb')
            self.assertEqual(keyboards[0].backend,'linux-input')
            self.assertEqual(keyboards[0].name,'Logitech G515 LS TKL')
            self.assertEqual(keyboards[0].targets['solaar-local'],['abcd1234'])
            self.assertIn('kernel-battery',keyboards[0].backends)

    def test_unknown_kernel_status_is_not_false(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);usb=root/'usb';usb.mkdir()
            supply=root/'supply';supply.mkdir();(supply/'device').symlink_to(usb)
            (supply/'uevent').write_text('POWER_SUPPLY_SCOPE=Device\nPOWER_SUPPLY_CAPACITY=97\nPOWER_SUPPLY_STATUS=Unknown\n')
            device=KernelBatteryAdapter(root).discover()[0]
            charging=next(c for c in device.capabilities if c.name=='charging')
            self.assertIsNone(charging.value);self.assertFalse(charging.readable)

    def test_battery_getter_is_read_only_and_does_not_guess_from_full_or_missing_status(self):
        device=SimpleNamespace(online=True,features={100})
        getter=Mock();templates=SimpleNamespace(_F=SimpleNamespace(UNIFIED_BATTERY=100),
            _hidpp20=SimpleNamespace(get_battery_unified=getter))
        for name,expected in [('RECHARGING',True),('DISCHARGING',False),('FULL',False),(None,None)]:
            getter.return_value=(100,SimpleNamespace(level=97,status=SimpleNamespace(name=name)))
            self.assertEqual(battery_metadata(SimpleNamespace(_device=device),templates),
                             {'battery_status':97,'charging':expected})
        self.assertEqual(getter.call_count,4)

    def test_live_battery_refresh_updates_exact_keyboard_without_affecting_rgb_errors(self):
        from logi_center.core.services.execution import Fault,FaultCode
        from logi_center.core.services.battery_presentation import battery_display
        class Empty:
            def discover(self):return []
            def associate(self,records):pass
        d=Device('kbd','G515 LS TKL','keyboard','linux-input',vid='046d',
            private_identity={'solaar_serial':'abcd1234'},faults=[Fault(FaultCode.CONNECTION,'solaar','RGB error')])
        runner=Mock(return_value='#   logi-center-battery: {"battery_status":97,"charging":true}\n')
        outcome=collect([d],runner,kernel_factory=Empty)
        self.assertEqual(runner.call_args.args[0],['solaar','config','abcd1234','brightness_control'])
        self.assertEqual(apply([d],outcome),(False,True))
        self.assertTrue(battery_display(d)['charging']);self.assertEqual(len(d.faults),1)
        d.private_identity['solaar_serial']='changed1234'
        d.capabilities=[];apply([d],outcome)
        self.assertEqual(d.capabilities,[])

    def test_two_unknown_g515_units_do_not_use_name_selector(self):
        class Empty:
            def discover(self):return []
            def associate(self,records):pass
        devices=[Device(str(i),'G515 LS TKL','keyboard','linux-input',vid='046d') for i in (1,2)]
        runner=Mock();collect(devices,runner,kernel_factory=Empty);runner.assert_not_called()

    def test_battery_failure_does_not_add_or_clear_rgb_faults(self):
        from logi_center.core.services.execution import Fault,FaultCode
        class Empty:
            def discover(self):return []
            def associate(self,records):pass
        d=Device('kbd','G515 LS TKL','keyboard','linux-input',vid='046d')
        runner=Mock(side_effect=Fault(FaultCode.CONNECTION,'solaar','Getter failed'))
        outcome=collect([d],runner,kernel_factory=Empty)
        self.assertEqual(apply([d],outcome),(True,False))
        self.assertEqual([f.component for f in d.faults],['solaar-battery'])

    def test_kernel_battery_refresh_uses_cable_supply_and_rejects_receiver_stale_status(self):
        from logi_center.core.capabilities import Capability
        current=Device('kbd','G515 LS TKL','keyboard','linux-input',physical='unit:private',
            private_identity={'usb_parents':['/private/receiver','/private/cable'],
                              'active_usb_parent':'/private/cable'})
        old=Device('old','Battery','battery','kernel-battery',physical='/private/receiver')
        fresh=Device('fresh','Battery','battery','kernel-battery',physical='/private/cable',
            capabilities=[Capability('charging','kernel-battery',True,True,value=True,source='kernel')])
        KernelBatteryAdapter().associate([current,old,fresh])
        self.assertEqual(fresh.physical,current.physical)
        self.assertNotEqual(old.physical,current.physical)
        self.assertEqual(apply([current],([],[old,fresh],None,None)),(False,True))
        self.assertTrue(current.capabilities[0].value)

    def test_input_evidence_preserves_identity_relationships_without_private_values(self):
        from scripts.g515_read_diagnostics import input_evidence
        d=Device('private-id','G515 LS TKL','keyboard','linux-input',vid='046d',pid='c547',
            connection='wireless',private_identity={'solaar_serial':'abcd1234',
                'usb_parent':'/private/receiver','hid_parent':'/private/hid'})
        factory=lambda:SimpleNamespace(discover=lambda:[d])
        empty=lambda:SimpleNamespace(discover=lambda:[])
        report=input_evidence(factory,empty)
        self.assertEqual(report['devices'][0]['paired_identity'],1)
        text=json.dumps(report)
        for value in ('private','abcd1234','G515'):self.assertNotIn(value,text)

    def test_simulated_keyboard_never_starts_real_solaar_status_read(self):
        class Empty:
            def discover(self):return []
            def associate(self,records):pass
        d=Device('sim','G515 LS TKL','keyboard','linux-input',vid='046d',simulated=True)
        runner=Mock();collect([d],runner,kernel_factory=Empty);runner.assert_not_called()

    def test_solaar_selector_matches_unit_id_and_prefers_same_unit_cable(self):
        from logi_center.adapters.logitech.solaar_write import match_unit_devices,enable_unit_selector
        receiver=SimpleNamespace(name='G515 LS TKL',serial='abcd1234',unitId='deaf5678',receiver=object())
        cable=SimpleNamespace(name='Logitech G515 LS TKL',serial='deaf5678',unitId='deaf5678',receiver=None)
        other=SimpleNamespace(name='G515 LS TKL',serial='aaaa1234',unitId='bbbb1234',receiver=object())
        self.assertEqual(match_unit_devices([receiver,other,cable],'DEAF5678'),[cable,receiver])
        original=Mock(return_value=iter([receiver,cable,other]));cli=SimpleNamespace(_find_device=original)
        enable_unit_selector(cli)
        self.assertEqual(list(cli._find_device([], 'DEAF5678')),[cable,receiver])
        original.assert_called_once_with([],'')
        self.assertEqual(match_unit_devices([other],'deaf5678'),[])

    def test_solaar_selector_rejects_ambiguous_pairing_serial_and_placeholder_units(self):
        from logi_center.adapters.logitech.solaar_write import match_unit_devices
        first=SimpleNamespace(name='G515 LS TKL',serial='abcd1234',unitId='deaf5678',receiver=object())
        second=SimpleNamespace(name='G515 LS TKL',serial='abcd1234',unitId='beef5678',receiver=None)
        with self.assertRaises(RuntimeError):match_unit_devices([first,second],'abcd1234')
        first.unitId=second.unitId='00000000'
        with self.assertRaises(RuntimeError):match_unit_devices([first,second],'abcd1234')
