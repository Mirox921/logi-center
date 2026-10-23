import json,unittest
from unittest.mock import patch
from types import SimpleNamespace as NS
from execution import Fault,FaultCode
from operations import perform,State
from mchose_adapter import decode,RATES,MchoseAdapter,setting_plan,Transport


def config():
    body=bytearray(63);body[1]=body[2]=0x20;body[16]=6;body[18]=4;body[19]=30
    for i,dpi in enumerate([400,800,1600,3200,6400,12800]):body[4+i*2:6+i*2]=dpi.to_bytes(2,'little')
    return decode(body,{'mode':1,'battery':81,'vid':0x3837,'pid':0x1001})

class MchoseTests(unittest.TestCase):
    def test_rate_layout_not_generic_usb_table(self):
        self.assertEqual(RATES,[125,500,1000,2000,4000,8000]);self.assertEqual(config()['polling_rate'],1000)
    def test_empty_short_malformed_config(self):
        for body in [b'',bytes(63),bytes([255])*63]:
            with self.assertRaises(ValueError):decode(body,{'mode':0})
    def test_readback_states(self):
        for value,state in [(800,State.CONFIRMED),(400,State.MISMATCH)]:
            result=perform(setting_plan('/dev/hidraw-test','dpi',800),lambda args:json.dumps({'dpi':value}))
            self.assertEqual(result.state,state)
    def test_permission_device_kept_visible(self):
        item={'node':'/dev/hidraw-test','physical':'/sys/fake','vid':'3837','pid':'1001','name':'K7'}
        def denied(args):raise PermissionError()
        with patch('mchose_adapter.candidates',return_value=[item]):
            device=MchoseAdapter(denied).discover()[0]
        self.assertEqual(device.faults[0].code,FaultCode.PERMISSION);self.assertFalse(device.capabilities)
    def test_only_read_commands_retry(self):
        transport=Transport('fake');transport.fd=1
        with patch('mchose_adapter.fcntl.ioctl',return_value=0) as ioctl,patch('mchose_adapter.time.sleep'),patch.object(transport,'_drain'),patch.object(transport,'_wait_ready'):
            with self.assertRaises(Fault):transport.exchange(0x12,0x67)
        self.assertEqual(ioctl.call_count,6)
        self.assertTrue(all(call.args[2][1]==0x98 for call in ioctl.call_args_list[::2]))
    def test_notification_precedes_feature_read(self):
        transport=Transport('fake');transport.fd=1;events=[]
        def ioctl(fd,code,frame,mutate):
            if code&255==6:events.append('set');return 0
            events.append('get');frame[1]=0x06^255;frame[2]=123^255;return 3
        with patch.object(transport,'_drain'),patch.object(transport,'_wait_ready',side_effect=lambda cmd:events.append(('ready',cmd))),patch('mchose_adapter.fcntl.ioctl',side_effect=ioctl),patch('mchose_adapter.time.sleep'):
            self.assertEqual(transport.exchange(0x11,0x06),bytes([123]))
        self.assertEqual(events,['set',('ready',6),'get'])
    def test_ready_notification_filters_other_commands(self):
        transport=Transport('fake');transport.fd=1
        with patch('mchose_adapter.select.select',return_value=([1],[],[])),patch('mchose_adapter.os.read',side_effect=[bytes([0x13,0xE5^255,7^255]),bytes([0x13,0xE5^255,6^255])]) as read:
            transport._wait_ready(6)
        self.assertEqual(read.call_count,2)
    def test_receiver_logical_identity_is_narrowly_allowed(self):
        from mchose_adapter import hardware
        observed=config();observed['identity']['pid']=0x4150
        class T:
            def __init__(self,node):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self):return observed
        item={'node':'fake','physical':'fake','vid':'3837','pid':'1001'}
        with patch('mchose_adapter.candidates',return_value=[item]):
            self.assertEqual(hardware('read','fake',transport=T)['identity']['pid'],0x4150)
            observed['identity']['pid']=0x9999
            with self.assertRaises(ValueError):hardware('read','fake',transport=T)
    def test_invalid_value_never_writes(self):
        from mchose_adapter import hardware
        fake=NS(__enter__=lambda x:x)
        class T:
            def __init__(self,node):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self):return config()
            def exchange(self,*args,**kw):raise AssertionError('write')
        with patch('mchose_adapter.candidates',return_value=[{'node':'fake','physical':'fake','vid':'3837','pid':'1001'}]):
            with self.assertRaises(ValueError):hardware('set',__import__('devices').identity('fake'),'dpi',123,transport=T)

class OpenRGBTests(unittest.TestCase):
    def client(self):
        mode=NS(name='Static',id=0,flags=48,color_mode=1,colors=[],brightness=60,brightness_min=0,brightness_max=100)
        self.device=NS(name='Keyboard',metadata=NS(location='/private/path',serial='secret'),type=5,modes=[mode],active_mode=0,colors=[NS(red=1,green=2,blue=3)],zones=[])
        self.client_obj=NS(devices=[self.device],disconnect=lambda:None,update=lambda:None)
        return self.client_obj
    def test_discovery_does_not_claim_device_confirmation(self):
        from openrgb_adapter import hardware,OpenRGBAdapter
        data=hardware('discover',factory=lambda **kw:self.client())
        devices=OpenRGBAdapter(lambda args:json.dumps(data)).discover()
        self.assertTrue(devices[0].capabilities);self.assertTrue(all(not c.verifiable for c in devices[0].capabilities));self.assertEqual(devices[0].physical,'')
    def test_stale_and_duplicate_controllers_refused(self):
        from openrgb_adapter import hardware,key
        c=self.client()
        with self.assertRaises(Fault):hardware('set','gone','lighting_mode','Static',factory=lambda **kw:c)
        c.devices*=2
        with self.assertRaises(Fault):hardware('set',key(self.device),'lighting_mode','Static',factory=lambda **kw:c)
    def test_cache_readback_remains_unconfirmed(self):
        from openrgb_adapter import setting_plan
        result=perform(setting_plan('controller','brightness',60),lambda args:json.dumps({'brightness':60}))
        self.assertEqual(result.state,State.SENT)
    def test_missing_binding_is_missing_component(self):
        from diagnostics import fault_for
        self.assertEqual(fault_for(ModuleNotFoundError()).code,FaultCode.MISSING)



class RazerTests(unittest.TestCase):
    def device(self,serial='serial-one'):
        features={'dpi','poll_rate','supported_poll_rates','battery','brightness'}
        return NS(serial=serial,name='Razer test mouse',type='mouse',has=lambda k:k in features,capabilities={k:True for k in features},dpi=(800,1200),max_dpi=26000,poll_rate=1000,supported_poll_rates=[500,1000],brightness=70,battery_level=80)
    def test_read_write_independent_axes_and_cache(self):
        from openrazer_adapter import hardware,OpenRazerAdapter,setting_plan
        device=self.device();factory=lambda:NS(devices=[device])
        before=hardware('discover',factory=factory)
        cap=OpenRazerAdapter(lambda args:json.dumps(before)).discover()[0].capabilities[0]
        self.assertFalse(cap.verifiable)
        hardware('set',before[0]['target'],'dpi_x',1600,factory=factory)
        self.assertEqual(device.dpi,(1600,1200))
        result=perform(setting_plan(before[0]['target'],'dpi_x',1600),lambda args:json.dumps(hardware('read',before[0]['target'],factory=factory)))
        self.assertEqual(result.state,State.SENT)
    def test_model_limits_and_unknown_fields(self):
        from openrazer_adapter import hardware,describe
        d=self.device();target=describe(d)['target'];factory=lambda:NS(devices=[d])
        for field,value in [('dpi_x',99999),('polling_rate',8000),('firmware',1),('battery_status',5)]:
            with self.assertRaises((ValueError,Fault)):hardware('set',target,field,value,factory=factory)
    def test_two_identical_units_selected_by_identity(self):
        from openrazer_adapter import hardware,describe
        a=self.device();b=self.device('serial-two')
        hardware('set',describe(b)['target'],'dpi_x',1600,factory=lambda:NS(devices=[a,b]))
        self.assertEqual(a.dpi,(800,1200));self.assertEqual(b.dpi,(1600,1200))

class ManagerExpansionTests(unittest.TestCase):
    def test_rgb_single_owner_and_sdk_evidence(self):
        from devices import Device,Capability,DeviceManager
        from operations import Result
        a=Device('a','mouse','mouse','ratbagctl','target','/sys/exact',capabilities=[Capability('lighting','ratbagctl',True,True,True)])
        b=Device('b','mouse','mouse','openrgb','sdk','/sys/exact',capabilities=[Capability('lighting','openrgb',True,True,True)])
        manager=DeviceManager();manager.devices=manager.merge([a,b])
        with self.assertRaises(Fault):manager.route('a','lighting','ratbagctl')
        manager.record_operation(['logi-sdk','openrgb','set','sdk','lighting','[1,2,3]'],Result(State.SENT,'logi-sdk',[1,2,3],[1,2,3],'backend_cache'))
        self.assertEqual(manager.route('a','lighting','openrgb').last_operation['state'],State.SENT.value)
    def test_rivalcfg_duplicate_interfaces_disable_writes(self):
        from rivalcfg_adapter import inventory,RivalcfgAdapter
        profile={'endpoint':3,'name':'Rival fixture','settings':{'polling_rate':{'value_type':'choice','choices':{125:1,1000:2}},'factory_reset':{'value_type':'choice','choices':{1:1}}}}
        records=inventory({(0x1038,0x1824):profile},lambda *args:[{'path':b'/dev/hidraw90','interface_number':3},{'path':b'/dev/hidraw91','interface_number':3}])
        devices=RivalcfgAdapter(lambda args:json.dumps(records)).discover()
        self.assertEqual(len(devices),2);self.assertNotEqual(devices[0].id,devices[1].id)
        self.assertTrue(all(not c.writable and c.value is None for d in devices for c in d.capabilities))
        self.assertNotIn('factory_reset',records[0]['settings'])
    def test_ckb_read_only_and_no_serial_in_target(self):
        import tempfile
        from pathlib import Path
        from ckb_adapter import CkbAdapter
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/'ckb1';p.mkdir()
            for name,value in {'model':'Corsair fixture','features':'corsair rgb bind','productid':'1b55','serial':'private-serial'}.items():(p/name).write_text(value)
            d=CkbAdapter(root).discover()[0]
            self.assertNotIn('private-serial',d.id);self.assertFalse(any(c.writable for c in d.capabilities))

class CapabilityBackupTests(unittest.TestCase):
    def device(self):
        from devices import Device,Capability
        from mchose_adapter import setting_plan
        caps=[]
        for field in ['dpi','debounce']:
            c=Capability(field,'mchose',True,True,True,True,800 if field=='dpi' else 4,'device',minimum=1,maximum=26000)
            c.plan=lambda value,f=field:setting_plan('target',f,value);caps.append(c)
        return Device('test','K7 fixture','mouse','mchose','target',vid='3837',pid='1001',capabilities=caps)
    def test_integrity_incompatible_and_preview(self):
        import capability_backup as backup
        d=self.device();current=backup.capture(d,lambda args:json.dumps({'dpi':800,'debounce':4}));desired=backup.capture(d,lambda args:json.dumps({'dpi':1600,'debounce':8}))
        preview=backup.preview(desired,current,d);self.assertEqual(len(preview.changes),2)
        desired['settings']['mchose:dpi']['value']=999
        with self.assertRaises(ValueError):backup.validate(desired)
        desired['sha256']=backup.digest(desired);desired['device']['model']='different';desired['sha256']=backup.digest(desired)
        with self.assertRaises(ValueError):backup.preview(desired,current,d)
    def test_partial_restore_stops_and_preserves_safety(self):
        import tempfile,capability_backup as backup
        from pathlib import Path
        d=self.device();live={'dpi':800,'debounce':4};writes=[]
        def runner(args):
            if args[2]=='set':
                writes.append(args[4])
                if args[4]=='debounce':raise Fault(FaultCode.DISCONNECTED,'mchose','Unplugged')
                live[args[4]]=json.loads(args[5])
            return json.dumps(live)
        current=backup.capture(d,runner);desired=backup.capture(d,lambda args:json.dumps({'dpi':1600,'debounce':8}))
        preview=backup.preview(desired,current,d)
        with tempfile.TemporaryDirectory() as root:
            report=backup.restore(preview,{c.id for c in preview.changes},d,runner,safety_root=root)
            self.assertTrue(report.stopped);self.assertTrue(Path(report.safety_copy).exists());self.assertEqual(report.results[0][1].state,State.CONFIRMED)
        self.assertEqual(live['dpi'],1600);self.assertEqual(writes,['dpi','debounce'])
    def test_stale_preview_does_not_write(self):
        import capability_backup as backup
        d=self.device();current=backup.capture(d,lambda a:json.dumps({'dpi':800,'debounce':4}));desired=backup.capture(d,lambda a:json.dumps({'dpi':1600,'debounce':4}));preview=backup.preview(desired,current,d)
        def runner(args):
            self.assertEqual(args[2],'read');return json.dumps({'dpi':1200,'debounce':4})
        with self.assertRaises(ValueError):backup.restore(preview,{'mchose:dpi'},d,runner)


class RegressionGuards(unittest.TestCase):
    def test_openrgb_active_mode_is_index_not_hardware_id(self):
        from openrgb_adapter import describe
        fixture=OpenRGBTests();fixture.client();fixture.device.modes[0].id=42
        self.assertEqual(describe(fixture.device)['lighting_mode'],'Static')
    def test_old_mchose_connection_cannot_write_to_reused_node(self):
        from mchose_adapter import selector,hardware
        old={'node':'/dev/hidraw5','physical':'/sys/usb1','generation':'hid-A'}
        new={**old,'generation':'hid-B'}
        self.assertNotEqual(selector(old),selector(new))
        with patch('mchose_adapter.candidates',return_value=[new]):
            with self.assertRaises(Fault) as raised:hardware('set',selector(old),'dpi',800)
        self.assertEqual(raised.exception.code,FaultCode.DISCONNECTED)
    def test_legacy_backup_rgb_command_cannot_bypass_owner(self):
        from devices import Device,Capability,DeviceManager
        manager=DeviceManager();device=Device('id','mouse','mouse','ratbagctl','mouse-target',capabilities=[Capability('lighting','openrgb',True,True,True)])
        manager.devices=[device]
        with self.assertRaises(Fault):manager.guard_command(['ratbagctl','mouse-target','profile','0','led','0','set','color','ff0000'])
    def test_missing_sdk_does_not_break_input_discovery(self):
        from devices import DeviceManager,Device
        from openrgb_adapter import OpenRGBAdapter
        def missing(args):raise Fault(FaultCode.MISSING,'openrgb','No binding')
        plain=NS(name='input',discover=lambda:[Device('plain','Plain keyboard','keyboard','input')])
        manager=DeviceManager([OpenRGBAdapter(missing),plain]);self.assertEqual(len(manager.discover()),1);self.assertEqual(manager.faults[0].code,FaultCode.MISSING)


class NewWriteValidation(unittest.TestCase):
    def test_openrgb_modes_brightness_and_zone_color(self):
        from openrgb_adapter import hardware,key
        fixture=OpenRGBTests();client=fixture.client();device=fixture.device;changes=[]
        def set_mode(value,save=False):
            self.assertFalse(save);changes.append(('mode',value))
        zone=NS(name='Left',leds=[1],colors=[NS(red=1,green=2,blue=3)],set_color=lambda c:changes.append(('zone',(c.red,c.green,c.blue))))
        device.zones=[zone];device.set_mode=set_mode;target=key(device)
        def factory(**kw):
            self.assertEqual(kw['address'],'127.0.0.1');return client
        hardware('set',target,'brightness',80,factory=factory)
        self.assertEqual(device.modes[0].brightness,80)
        from openrgb_adapter import describe
        field=describe(device)['zones'][0]['setting']
        import sys,types
        module=types.ModuleType('openrgb.utils');module.RGBColor=lambda r,g,b:NS(red=r,green=g,blue=b)
        with patch.dict(sys.modules,{'openrgb.utils':module}):hardware('set',target,field,[100,50,25],factory=factory)
        self.assertIn(('zone',(100,50,25)),changes)
        with self.assertRaises(ValueError):hardware('set',target,'brightness',200,factory=factory)
    def test_mchose_read_modify_write_preserves_unknown_bytes(self):
        from mchose_adapter import hardware
        import copy
        before=config();before['raw'][30]=173;current=copy.deepcopy(before);writes=[]
        class Transport:
            def __init__(self,node):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self):return copy.deepcopy(current)
            def exchange(self,report,command,payload,**kw):
                writes.append((report,command,payload));current['raw']=list(payload);current['dpi']=1600
        item={'node':'fake','physical':'fake','vid':'3837','pid':'1001'}
        with patch('mchose_adapter.candidates',return_value=[item]),patch('mchose_adapter.atomic_json') as snapshot,patch('mchose_adapter.time.sleep'):
            result=hardware('set',__import__('devices').identity('fake'),'dpi',1600,transport=Transport)
        self.assertEqual(len(writes),1);self.assertEqual(writes[0][0:2],(0x12,0x57));self.assertEqual(result['raw'][30],173);snapshot.assert_called_once()
    def test_mchose_refuses_collateral_change(self):
        from mchose_adapter import hardware
        import copy
        current=config()
        class Transport:
            def __init__(self,node):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self):return copy.deepcopy(current)
            def exchange(self,*args,**kw):current['raw'][30]=123
        item={'node':'fake','physical':'fake','vid':'3837','pid':'1001'}
        with patch('mchose_adapter.candidates',return_value=[item]),patch('mchose_adapter.atomic_json'),patch('mchose_adapter.time.sleep'):
            with self.assertRaises(Fault):hardware('set',__import__('devices').identity('fake'),'debounce',8,transport=Transport)


class PhysicalAssociationTests(unittest.TestCase):
    def test_exact_usb_parent_single_input_function_merges(self):
        from devices import Device,DeviceManager
        a=Device('input','Mouse','mouse','linux-input',physical='/sys/usb/a|input0')
        b=Device('mchose','Mouse','mouse','mchose','current-hid-instance','/sys/usb/a')
        c=Device('keyboard','Composite keyboard','keyboard','linux-input',physical='/sys/usb/a|input1')
        records=[a,b,c];DeviceManager.link_physical(records)
        merged=DeviceManager.merge(records)
        self.assertEqual(len(merged),2);self.assertIn('mchose',merged[0].backends)
    def test_two_receiver_mouse_slots_remain_separate(self):
        from devices import Device,DeviceManager
        a=Device('input1','Mouse','mouse','linux-input',physical='/sys/usb/a|slot1')
        b=Device('input2','Mouse','mouse','linux-input',physical='/sys/usb/a|slot2')
        c=Device('provider','Mouse','mouse','mchose','selector','/sys/usb/a')
        records=[a,b,c];DeviceManager.link_physical(records)
        self.assertEqual(len(DeviceManager.merge(records)),3)

if __name__=='__main__':unittest.main()
