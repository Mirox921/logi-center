import unittest,json,copy,tempfile
from pathlib import Path
from unittest.mock import patch
from logi_center.protocols.ace68_protocol import packet,response,decode_keys,changed_key,validate_key_value,state,KEY_INDICES
from logi_center.adapters.mchose.ace68_adapter import hardware,selector,Ace68Adapter
from logi_center.core.devices.devices import DeviceManager,Device
from logi_center.core.services.operations import perform,State
from logi_center.core.services.execution import Fault,FaultCode

class MemoryWire:
    def __init__(self,node=None):
        self.tables={3:bytearray(22),4:bytearray(56),5:bytearray(256),160:bytearray(4096)};self.tables[3][:2]=bytes([0x21,1]);self.tables[4][:6]=bytes([0,3,0,1,2,3]);self.writes=[];self.disconnected=False
        for p in range(4):
            self.tables[5][64*p+4]=1;self.tables[5][64*p+8:64*p+17]=bytes([6,75,2,0,0,0,10,20,30])
            for k in range(128):self.tables[160][p*1024+k*8:p*1024+k*8+8]=bytes([160,1,149,0,29,30,29,30])
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,command,offset,length):
        if self.disconnected:raise Fault(FaultCode.DISCONNECTED,'mchose-ace68','Disconnected')
        return bytes(self.tables[command][offset:offset+length])
    def request(self,command,offset,size,data=None):
        self.writes.append((command,offset,data));table=self.tables[{6:5,161:160,14:4}[command]];table[offset:offset+size]=bytes(data);return b''

ITEM={'node':'/dev/test-ace68','physical':'/sys/fake-keyboard','generation':'hid-instance','name':'Ace68-II','release':'0121'}

class PacketTests(unittest.TestCase):
    def test_request_wire_format_and_no_mouse_feature_ids(self):
        p=packet(3,0,56);self.assertEqual(len(p),65);self.assertEqual(p[:9],bytes([0,85,3,0,56,56,0,0,0]))
        for command in [14,161,0x57,0xff]:
            with self.assertRaises(ValueError):packet(command,0,8)
    def test_reply_checksum_short_info_and_unrelated_ack(self):
        raw=bytearray(64);raw[:2]=bytes([170,3]);raw[4]=22;raw[8:10]=bytes([33,1]);raw[3]=sum(raw[4:])&255
        self.assertEqual(len(response(raw,3,0,56)),22);self.assertIsNone(response(raw,4,0,56))
        raw[8]^=1
        with self.assertRaises(ValueError):response(raw,3,0,56)
    def test_empty_ack_only_for_writes(self):
        raw=bytearray(64);raw[:2]=bytes([170,6])
        self.assertEqual(response(raw,6,0,1,True),b'')
        with self.assertRaises(ValueError):response(raw,6,0,1)
    def test_physical_key_layout_unique(self):
        from logi_center.adapters.mchose.ace68_adapter import LAYOUT
        self.assertEqual(sum(map(len,LAYOUT)),68);self.assertEqual(len(set(KEY_INDICES)),68)

class KeyboardTests(unittest.TestCase):
    def setUp(self):self.wire=MemoryWire();self.candidate=patch('logi_center.adapters.mchose.ace68_adapter.candidates',return_value=[ITEM]);self.candidate.start();self.snapshots=patch('logi_center.core.services.drafts.atomic_json');self.save=self.snapshots.start()
    def tearDown(self):self.candidate.stop();self.snapshots.stop()
    def call(self,action,field=None,value=None):return hardware(action,selector(ITEM),field,value,transport=lambda node:self.wire)
    def test_real_schema_read_and_keyboard_separation(self):
        observed=self.call('read');self.assertEqual(observed['firmware_version'],'121');self.assertEqual(observed['polling_rate'],8000);self.assertEqual(observed['actuation']['50'],1.5);self.assertEqual(self.wire.writes,[])
    def test_profile_order_not_sorted_assumption(self):
        self.wire.tables[4][:6]=bytes([1,3,2,0,1,3]);self.assertEqual(self.call('read')['profiles'],0)
    def test_bad_base_never_autorepairs(self):
        self.wire.tables[4][2:6]=bytes([0,0,0,0])
        with self.assertRaises(ValueError):self.call('read')
        self.assertEqual(self.wire.writes,[])
    def test_unsupported_firmware_readable_not_writable(self):
        self.wire.tables[3][0]=0x22;self.assertEqual(self.call('read')['firmware_version'],'122')
        with self.assertRaises(Fault):self.call('set','brightness',75)
        self.assertEqual(self.wire.writes,[])
    def test_actuation_one_key_keeps_other_bytes_and_keys(self):
        before=bytes(self.wire.tables[160]);out=self.call('set','actuation',{'50':.3});after=bytes(self.wire.tables[160])
        self.assertEqual(out['actuation']['50'],.3);self.assertEqual(before[:400],after[:400]);self.assertEqual(before[408:],after[408:]);self.assertEqual(before[400:402],after[400:402]);self.assertEqual(before[404:408],after[404:408]);self.save.assert_called_once()
    def test_invalid_second_key_does_not_partially_apply(self):
        with self.assertRaises(ValueError):self.call('set','actuation',{'50':.3,'0':float('nan')})
        self.assertFalse(self.wire.writes);self.save.assert_not_called()
    def test_invalid_ranges_and_unknown_fields(self):
        for f,v in [('actuation',{'50':0}),('actuation',{'50':4}),('rt_press',{'50':.001}),('rapid_trigger',{'50':3}),('press_dead_zone',{'50':1}),('actuation',{'999':.3}),('calibration',1),('firmware',1),('factory_reset',True)]:
            with self.subTest(f=f,v=v),self.assertRaises((ValueError,Fault)):self.call('set',f,v)
        self.assertFalse(self.wire.writes)
    def test_rt_precision_dead_zone_and_reserved_bits(self):
        before=bytes(self.wire.tables[160]);out=self.call('set','rt_release',{'50':.2});self.assertEqual(out['rt_release']['50'],.2);self.assertEqual(out['release_dead_zone']['50'],.15)
        out=self.call('set','rapid_trigger',{'50':2});self.assertEqual(out['rapid_trigger']['50'],2)
        out=self.call('set','press_dead_zone',{'50':.25});self.assertEqual(out['press_dead_zone']['50'],.25)
    def test_profile_switch_only_edits_active_position(self):
        before=bytes(self.wire.tables[4]);self.call('set','profiles',2);self.assertEqual(bytes(self.wire.tables[4])[1:],before[1:])
        with self.assertRaises(ValueError):self.call('set','profiles',3)
    def test_rgb_changes_only_requested_fields(self):
        before=bytes(self.wire.tables[5]);out=self.call('set','brightness',50);self.assertEqual(out['brightness'],50)
        changed=[i for i,(a,b) in enumerate(zip(before,self.wire.tables[5])) if a!=b];self.assertEqual(changed,[9])
        self.wire.tables[5][12]=1
        self.call('set','lighting',[1,2,3]);self.assertEqual(self.call('read')['lighting'],[1,2,3]);self.assertEqual(self.wire.tables[5][12],1)
        self.call('set','lighting_palette','Single color');self.assertEqual(self.wire.tables[5][12],0)
    def test_stale_profile_blocks_write_before_snapshot(self):
        with self.assertRaises(Fault):self.call('set','profile/1/actuation',{'50':.31})
        self.assertFalse(self.wire.writes);self.save.assert_not_called()
    def test_scoped_plan_reads_selected_keys_and_detects_profile_conflict(self):
        from logi_center.adapters.mchose.ace68_adapter import setting_plan
        plan=setting_plan(selector(ITEM),'actuation',{'50':1.5},0)
        self.assertEqual(plan.command[4],'profile/0/actuation')
        self.assertEqual(plan.reader(lambda args:json.dumps(self.call('read'))).value,{'50':1.5})
        self.wire.tables[4][0]=1
        with self.assertRaises(ValueError):plan.reader(lambda args:json.dumps(self.call('read')))
    def test_wrong_selector_disconnected(self):
        with self.assertRaises(Fault):hardware('read','mouse-target',transport=lambda node:self.wire)
        self.assertFalse(self.wire.writes)
    def test_adapter_and_input_composites_merge(self):
        runner=lambda args:json.dumps(self.call('read'))
        input_adapter=type('Input',(),{'name':'linux-input','discover':lambda self:[Device('a','Ace68-II','keyboard','linux-input',physical=ITEM['physical']+'|input0',vid='41e4',pid='2116'),Device('b','Ace68-II','keyboard','linux-input',physical=ITEM['physical']+'|input2',vid='41e4',pid='2116')]})()
        manager=DeviceManager([input_adapter,Ace68Adapter(runner=runner)]);devices=manager.discover();self.assertEqual(len(devices),1);self.assertIn('mchose-ace68',devices[0].backends)
    def test_partial_key_result_keeps_other_observed_keys_and_guard(self):
        from logi_center.core.services.operations import Result
        runner=lambda args:json.dumps(self.call('read'))
        device=Ace68Adapter(runner=runner).discover()[0];manager=DeviceManager();manager.devices=[device]
        target=device.target;command=['logi-sdk','mchose-ace68','set',target,'profile/0/actuation','{"50":0.3}']
        manager.guard_command(command)
        manager.record_operation(command,Result(State.CONFIRMED,'mchose-ace68',{'50':.3},{'50':.3},'device'))
        cap=next(c for c in device.capabilities if c.name=='actuation')
        self.assertEqual(len(cap.value),68);self.assertEqual(cap.value['0'],1.5);self.assertEqual(cap.value['50'],.3)
        next(c for c in device.capabilities if c.name=='profiles').value=1
        with self.assertRaises(Fault):manager.guard_command(command)
    def test_reader_mismatch_and_disconnect(self):
        from logi_center.adapters.mchose.ace68_adapter import setting_plan
        result=perform(setting_plan(selector(ITEM),'brightness',50),lambda a:json.dumps(self.call('read')));self.assertEqual(result.state,State.MISMATCH)
        def unplug(a):raise Fault(FaultCode.DISCONNECTED,'mchose-ace68','offline')
        self.assertEqual(perform(setting_plan(selector(ITEM),'brightness',50),unplug).state,State.DISCONNECTED)

class BackupTests(unittest.TestCase):
    def test_cross_profile_requires_fresh_destination_preview(self):
        import logi_center.core.services.capability_backup as backup
        wire=MemoryWire()
        with patch('logi_center.adapters.mchose.ace68_adapter.candidates',return_value=[ITEM]):
            runner=lambda args:json.dumps(hardware('read',args[3],transport=lambda node:wire))
            device=Ace68Adapter(runner=runner).discover()[0]
            current=backup.capture(device,runner);desired=copy.deepcopy(current)
            desired['settings']['mchose-ace68:profiles']['value']=1
            desired['settings']['mchose-ace68:actuation']['value']['50']=.3
            desired['sha256']=backup.digest(desired)
            preview=backup.preview(desired,current,device)
            self.assertEqual([c.id for c in preview.changes],['mchose-ace68:profiles'])
            self.assertTrue(any('actuation' in s and 'reopen preview' in s for s in preview.skipped))
            self.assertFalse(wire.writes)
    def test_partial_restore_stops_and_retains_first_confirmed_key(self):
        import logi_center.core.services.capability_backup as backup
        wire=MemoryWire();writes=[]
        with patch('logi_center.adapters.mchose.ace68_adapter.candidates',return_value=[ITEM]),patch('logi_center.core.services.drafts.atomic_json'):
            def runner(args):
                if args[2]=='set':
                    writes.append(args)
                    if len(writes)==2:raise Fault(FaultCode.DISCONNECTED,'mchose-ace68','Unplugged')
                return json.dumps(hardware(args[2],args[3],args[4] if len(args)>4 else None,json.loads(args[5]) if len(args)>5 else None,transport=lambda node:wire))
            device=Ace68Adapter(runner=runner).discover()[0];current=backup.capture(device,runner);desired=copy.deepcopy(current)
            desired['settings']['mchose-ace68:actuation']['value'].update({'50':.3,'0':.4});desired['sha256']=backup.digest(desired)
            preview=backup.preview(desired,current,device)
            with tempfile.TemporaryDirectory() as root:report=backup.restore(preview,{c.id for c in preview.changes},device,runner,safety_root=root)
            self.assertTrue(report.stopped);self.assertEqual([r.state for label,r in report.results],[State.CONFIRMED,State.DISCONNECTED]);self.assertEqual(len(writes),2)
            self.assertEqual(state(wire)['actuation']['50'],.3);self.assertEqual(state(wire)['actuation']['0'],1.5)
    def test_selected_key_restore_and_device_type_separation(self):
        import logi_center.core.services.capability_backup as backup
        wire=MemoryWire()
        with patch('logi_center.adapters.mchose.ace68_adapter.candidates',return_value=[ITEM]),patch('logi_center.core.services.drafts.atomic_json'):
            def runner(args):return json.dumps(hardware(args[2],args[3],args[4] if len(args)>4 else None,json.loads(args[5]) if len(args)>5 else None,transport=lambda node:wire))
            device=Ace68Adapter(runner=runner).discover()[0]
            current=backup.capture(device,runner);desired=copy.deepcopy(current);desired['settings']['mchose-ace68:actuation']['value']['50']=.3;desired['sha256']=backup.digest(desired)
            preview=backup.preview(desired,current,device);self.assertEqual(len(preview.changes),1);self.assertIn('Esc',preview.changes[0].label)
            with tempfile.TemporaryDirectory() as root:
                report=backup.restore(preview,{preview.changes[0].id},device,runner,safety_root=root)
                self.assertFalse(report.stopped);self.assertEqual(report.results[0][1].state,State.CONFIRMED)
            mouse=copy.deepcopy(desired);mouse['device']['kind']='mouse';mouse['sha256']=backup.digest(mouse)
            with self.assertRaises(ValueError):backup.preview(mouse,current,device)

if __name__=='__main__':unittest.main()
