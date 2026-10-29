import unittest
from unittest.mock import patch
from datetime import datetime,timezone,timedelta
from logi_center.core.devices.devices import Device, DeviceManager
from logi_center.core.capabilities.model import Capability
from logi_center.core.services.execution import Fault,FaultCode
from logi_center.adapters.mchose.mchose_adapter import MchoseAdapter
from logi_center.adapters.eweadn.eweadn_adapter import EweadnAdapter
from logi_center.core.devices.device_status import battery_text,battery_icon,status_text,user_fault_summary
from logi_center.i18n import set_language

class Categories(unittest.TestCase):
    def manager(self,*devices):
        m=DeviceManager();m.devices=list(devices);return m
    def test_all_vendor_mice_share_one_category(self):
        mice=[Device(str(i),name,'mouse',backend) for i,(name,backend) in enumerate([('K7 Ultra','mchose'),('G502','ratbagctl'),('Basilisk','openrazer'),('Rival','rivalcfg'),('USB Mouse','linux-input')])]
        m=self.manager(*mice,Device('ace','Ace68-II','keyboard','mchose-ace68'))
        self.assertEqual(m.active('mouse'),mice);self.assertEqual(len(m.active('keyboard')),1)
    def test_history_disconnected_and_simulation_are_not_active(self):
        m=self.manager(Device('old','G515','keyboard','solaar-local'),Device('off','Mouse','mouse','mchose',connected=False),Device('sim','Mouse','mouse','simulation',simulated=True))
        self.assertEqual(m.active('mouse'),[]);self.assertEqual(m.active('keyboard'),[]);self.assertEqual(len(m.active('mouse',simulation=True)),1)
    def test_permission_error_with_live_kernel_record_is_not_disconnect(self):
        d=Device('k','K7','mouse','mchose',connected=None,capabilities=[Capability('standard_input','linux-input',source='kernel')],faults=[Fault(FaultCode.PERMISSION,'mchose','denied')])
        m=self.manager(d);self.assertEqual(m.active('mouse'),[d])
    def test_unknown_backend_without_presence_is_diagnostic_only(self):
        self.assertFalse(self.manager(Device('a','Mouse','mouse','provider',connected=None)).active('mouse'))
    def test_different_types_on_same_usb_parent_never_merge(self):
        records=[Device('m','Composite mouse','mouse','linux-input',physical='/usb/1'),Device('k','Composite keyboard','keyboard','linux-input',physical='/usb/1')]
        self.assertEqual(len(DeviceManager.merge(records)),2)
    def test_k7_auxiliary_keyboard_is_not_physical_keyboard(self):
        mouse=Device('m','K7','mouse','mchose',physical='/usb/1',vid='3837',pid='1001')
        auxiliary=Device('a','K7 Keyboard','keyboard','linux-input',physical='/usb/1|input1',vid='3837',pid='1001')
        ace=Device('ace','Ace68-II','keyboard','mchose-ace68',physical='/usb/2',vid='41e4',pid='2116')
        MchoseAdapter().associate([mouse,auxiliary,ace]);self.assertEqual(self.manager(mouse,auxiliary,ace).active('keyboard'),[ace])
    def test_mouse_vendor_keyboard_collection_is_hidden_only_for_exact_usb_sibling(self):
        mouse=Device('m','Gaming Mouse 8K EWEADN S9','mouse','linux-input',physical='/usb/1|input0',vid='3344',pid='5566')
        auxiliary=Device('aux','Gaming Mouse 8K EWEADN S9 Keyboard','keyboard','linux-input',physical='/usb/1|input1',vid='3344',pid='5566')
        separate=Device('real','Gaming Mouse 8K EWEADN S9 Keyboard','keyboard','linux-input',physical='/usb/2|input1',vid='3344',pid='5566')
        merged=DeviceManager.merge([mouse,auxiliary,separate])
        self.assertEqual(auxiliary.kind,'interface');self.assertEqual(separate.kind,'keyboard')
        self.assertEqual([d.id for d in self.manager(*merged).active('keyboard')],['real'])
    def test_shared_usb_parent_without_matching_model_does_not_hide_keyboard(self):
        mouse=Device('m','Gaming Mouse','mouse','linux-input',physical='/usb/1|input0',vid='3344',pid='5566')
        keyboard=Device('k','Compact Keyboard','keyboard','linux-input',physical='/usb/1|input1',vid='3344',pid='5566')
        merged=DeviceManager.merge([mouse,keyboard])
        self.assertEqual(next(d for d in merged if d.id=='k').kind,'keyboard')
    def test_eweadn_archive_ids_join_exact_linux_mouse_without_duplicate(self):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            usb=Path(root)/'1-2';usb.mkdir()
            (usb/'idVendor').write_text('372e');(usb/'idProduct').write_text('1026')
            (usb/'product').write_text('Gaming Mouse 8K EWEADN S9')
            vendor=EweadnAdapter(root).discover()[0]
            event=Device('input','Gaming Mouse 8K EWEADN S9','mouse','linux-input',physical=str(usb.resolve())+'|usb-1-2/input0',vid='372e',pid='1026')
            records=[event,vendor];DeviceManager.link_physical(records);merged=DeviceManager.merge(records)
        self.assertEqual(len(merged),1);self.assertEqual(merged[0].kind,'mouse')
        self.assertIn('eweadn',merged[0].backends);self.assertTrue(all(not c.writable for c in merged[0].capabilities))
    def test_user_facing_status_does_not_expose_backend_names(self):
        text=status_text(Device('m','MCHOSE','mouse','linux-input',connection='usb',connected=True,backends=['linux-input','mchose']))
        self.assertNotIn('linux-input',text);self.assertNotIn('mchose',text);self.assertIn('USB',text)
    def test_primary_fault_summary_hides_protocol_details(self):
        set_language('en');self.addCleanup(set_language,'ru')
        text=user_fault_summary(Fault(FaultCode.CONFIG,'mchose','Empty identity reply; profile recovery is never automatic'))
        self.assertEqual(text,'Could not read device settings')
        self.assertNotIn('mchose',text);self.assertNotIn('profile recovery',text)
    def test_other_receiver_keyboard_is_not_suppressed(self):
        keyboard=Device('k','Keyboard','keyboard','linux-input',physical='/usb/1|input1',vid='046d',pid='1234')
        MchoseAdapter().associate([keyboard]);self.assertEqual(keyboard.kind,'keyboard')
    def test_authoritative_receiver_disconnect_overrides_input_interface(self):
        records=[Device('input','K7','mouse','linux-input',physical='/usb/1'),Device('mouse','K7','mouse','mchose',physical='/usb/1',connected=False)]
        merged=DeviceManager.merge(records);self.assertFalse(merged[0].connected);self.assertFalse(self.manager(*merged).active('mouse'))
    def test_disconnect_disables_route_reconnect_restores(self):
        d=Device('m','K7','mouse','mchose',capabilities=[Capability('dpi','mchose',True,writable=True)])
        m=self.manager(d);d.connected=False
        with self.assertRaises(Fault):m.route('m','dpi')
        d.connected=True;self.assertIsNotNone(m.route('m','dpi'))
    def test_two_equal_models_remain_separate_and_backends_merge(self):
        records=[Device('a','Same','mouse','linux-input',physical='/usb/1'),Device('b','Same','mouse','mchose',physical='/usb/1'),Device('c','Same','mouse','linux-input',physical='/usb/2')]
        m=self.manager(*DeviceManager.merge(records));self.assertEqual(len(m.active('mouse')),2)
    def test_kernel_battery_links_only_one_exact_parent(self):
        from logi_center.adapters.external.linux_input import KernelBatteryAdapter
        battery=Device('b','Battery','battery','kernel-battery',physical='/usb/1',connected=None)
        mouse=Device('m','Mouse','mouse','linux-input',physical='/usb/1|input0')
        KernelBatteryAdapter().associate([battery,mouse]);self.assertEqual((battery.physical,battery.kind),(mouse.physical,'mouse'))
        battery=Device('b','Battery','battery','kernel-battery',physical='/usb/1',connected=None)
        other=Device('k','Keyboard','keyboard','linux-input',physical='/usb/1|input1')
        KernelBatteryAdapter().associate([battery,mouse,other]);self.assertEqual(battery.kind,'battery')
    def test_ace_mouse_interface_is_not_a_physical_mouse(self):
        from logi_center.adapters.mchose.ace68_adapter import Ace68Adapter
        ace=Device('k','Ace68-II','keyboard','mchose-ace68',physical='/usb/1',vid='41e4',pid='2116')
        auxiliary=Device('m','Ace68 Mouse','mouse','linux-input',physical='/usb/1|input2',vid='41e4',pid='2116')
        Ace68Adapter().associate([ace,auxiliary]);self.assertEqual(auxiliary.kind,'interface');self.assertFalse(self.manager(ace,auxiliary).active('mouse'))
    def test_unknown_keyboard_gets_no_fictional_capabilities(self):
        d=Device('k','Unknown','keyboard','linux-input',capabilities=[Capability('standard_input','linux-input',True,True,source='kernel')])
        self.assertEqual(self.manager(d).active('keyboard'),[d]);self.assertFalse(any(c.writable for c in d.capabilities))

class Battery(unittest.TestCase):
    def setUp(self):set_language('ru')
    def device(self,value=None,source='device'):
        return Device('m','K7','mouse','mchose',capabilities=[Capability('battery_status','mchose',True,True,value=value,source=source)])
    def test_percent_and_zero_are_real_values(self):
        self.assertEqual(battery_text(self.device(54)),'54%');self.assertEqual(battery_text(self.device(0)),'0%')
    def test_none_is_not_zero(self):self.assertEqual(battery_text(self.device()),'Заряд: нет данных')
    def test_approximate_level_is_not_invented_percent(self):self.assertEqual(battery_text(self.device('low')),'low')
    def test_charge_status(self):
        d=self.device(54);d.capabilities.append(Capability('charging','mchose',True,True,value=True,source='device'));self.assertIn('заряжается',battery_text(d));self.assertEqual(battery_icon(d),'battery-good-charging-symbolic')
    def test_charging_icon_requires_positive_backend_state(self):
        self.assertEqual(battery_icon(self.device(54)),'battery-good-symbolic')
        self.assertEqual(battery_icon(self.device()),'battery-missing-symbolic')
        d=self.device(54);d.connected=False;self.assertEqual(battery_icon(d),'network-offline-symbolic')
    def test_permission_denied_does_not_display_old_value_as_live(self):
        d=self.device(54);d.faults=[Fault(FaultCode.PERMISSION,'mchose','denied')];self.assertEqual(battery_text(d),'Нет доступа к заряду')
    def test_cached_and_stale_are_labeled(self):
        self.assertIn('Сохранённое значение',battery_text(self.device(54,'local')))
        d=self.device(54);d.capabilities[0].observed_at=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat();self.assertIn('Последнее значение: 54% · Устарело',battery_text(d))
    def test_offline_and_failed_read_are_not_live(self):
        d=self.device(54);d.connected=False;self.assertEqual(battery_text(d),'Не в сети')
        d.connected=True;d.faults=[Fault(FaultCode.CONNECTION,'mchose','failed')];self.assertIn('Последнее чтение не удалось',battery_text(d))

if __name__=='__main__':unittest.main()
