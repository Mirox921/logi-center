import json
import unittest
from devices import Capability,Device
from execution import Fault,FaultCode
from battery_service import collect,apply


class NoKernel:
    def discover(self):return []
    def associate(self,rows):pass


class BatteryServiceTests(unittest.TestCase):
    def mouse(self,identifier='one',target='target'):
        return Device(identifier,'Same model','mouse','mchose',target,capabilities=[
            Capability('battery_status','mchose',True,True,value=70,source='device'),
            Capability('charging','mchose',True,True,value=False,source='device')])

    def test_reads_only_registered_backend_and_applies_to_exact_identity(self):
        a,b=self.mouse(),self.mouse('two','other')
        calls=[]
        def runner(args):calls.append(args);return json.dumps({'battery_status':64,'charging':True})
        outcome=collect([a],runner,kernel_factory=NoKernel)
        self.assertEqual(calls,[['logi-sdk','mchose','battery','target']])
        failed,changed=apply([a,b],outcome)
        self.assertFalse(failed);self.assertTrue(changed)
        self.assertEqual(a.capabilities[0].value,64);self.assertEqual(b.capabilities[0].value,70)
        self.assertTrue(a.capabilities[1].value)

    def test_mouse_connection_mode_updates_only_on_matching_live_read(self):
        device=self.mouse();device.connection='wireless'
        outcome=collect([device],lambda args:json.dumps({'battery_status':70,'charging':False,'identity':{'mode':0}}),kernel_factory=NoKernel)
        self.assertEqual(apply([device],outcome),(False,True))
        self.assertEqual(device.connection,'usb')
        outcome=collect([device],lambda args:json.dumps({'battery_status':70,'charging':False,'identity':{'mode':1}}),kernel_factory=NoKernel)
        self.assertEqual(apply([device],outcome),(False,True))
        self.assertEqual(device.connection,'wireless')
        outcome=collect([device],lambda args:json.dumps({'battery_status':70,'charging':False,'identity':{'mode':9}}),kernel_factory=NoKernel)
        self.assertEqual(apply([device],outcome),(False,False))
        self.assertEqual(device.connection,'wireless')

    def test_invalid_backend_response_is_a_read_error_not_a_gui_exception(self):
        device=self.mouse()
        for raw in ('[]','false','invalid-json'):
            outcome=collect([device],lambda args:raw,kernel_factory=NoKernel)
            self.assertTrue(apply([device],outcome)[0])
            self.assertEqual(device.capabilities[0].value,70)

    def test_rebound_target_drops_late_read(self):
        d=self.mouse();outcome=collect([d],lambda args:'{"battery_status":50}',kernel_factory=NoKernel)
        d.targets={'mchose':['new-instance']}
        apply([d],outcome)
        self.assertEqual(d.capabilities[0].value,70)

    def test_read_error_does_not_erase_old_value_or_turn_it_into_zero(self):
        d=self.mouse()
        def denied(args):raise Fault(FaultCode.PERMISSION,'mchose','Denied')
        outcome=collect([d],denied,kernel_factory=NoKernel)
        failed,changed=apply([d],outcome)
        self.assertTrue(failed);self.assertFalse(changed)
        self.assertEqual(d.capabilities[0].value,70)
        from battery_presentation import battery_display
        self.assertEqual(battery_display(d)['batteryState'],'denied')
        self.assertEqual(battery_display(d)['batteryPercent'],-1)

    def test_openrazer_cache_is_not_promoted_to_hardware_truth(self):
        d=Device('razer','Razer','mouse','openrazer','r',capabilities=[Capability('battery_status','openrazer',True,True,value=20,source='backend_cache')])
        outcome=collect([d],lambda args:'{"settings":{"battery_status":{"value":40}}}',kernel_factory=NoKernel)
        apply([d],outcome)
        self.assertEqual(d.capabilities[0].value,40)
        self.assertEqual(d.capabilities[0].source,'backend_cache')

    def test_kernel_discovery_enriches_only_exact_single_physical_peer(self):
        a,b=self.mouse(),self.mouse('two','other');a.physical='/port/a';b.physical='/port/b'
        kernel=Device('k','Battery','mouse','kernel-battery',physical='/port/a',capabilities=[Capability('battery_status','kernel-battery',True,True,value=85,source='kernel')])
        apply([a,b],([], [kernel], None, None))
        self.assertEqual(a.capabilities[-1].value,85)
        self.assertEqual(len(b.capabilities),2)

    def test_merged_headset_uses_unique_registered_selector_not_model_name(self):
        device=Device('pulse:merged','Headset','audio','pactl','sink',targets={'pactl':['sink'],'headsetcontrol':['known-selector']})
        observed=Device('headset:known-selector:0','Headset','audio','headsetcontrol','known-selector',capabilities=[Capability('battery_status','headsetcontrol',True,True,value=77,source='device')])
        apply([device],([],[],[observed],None))
        self.assertEqual(device.capabilities[0].value,77)
        duplicate=Device('headset:known-selector:1','Headset','audio','headsetcontrol','known-selector',capabilities=observed.capabilities)
        device.capabilities=[]
        apply([device],([],[],[observed,duplicate],None))
        self.assertEqual(device.capabilities,[])
