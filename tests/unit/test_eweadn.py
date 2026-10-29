"""Native S9 mock frames; no USB/HID writes or user settings access."""
import copy,json,struct,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from logi_center.protocols.eweadn_protocol import packet,response,decode,prepare,MODELS,RATES
from logi_center.adapters.eweadn.eweadn_adapter import hardware,fingerprint,setting_plan,capabilities,selector
from logi_center.core.services.operations import perform,State
from logi_center.core.services.execution import Fault

ITEM={'node':'/simulation/eweadn','vid':'372e','pid':'1026','physical':'/simulation/usb','generation':'/simulation/usb/interface','descriptor':'fixture'}
TARGET=selector(ITEM)


class Wire:
    def __init__(self):
        self.pages={128:bytearray(struct.pack('<H',0x0110)+(9895604650000).to_bytes(6,'big')),
            129:bytearray([76,0x30,4,0x20,0x30,0x75,16]),64:bytearray([0x20,0x05,0x16,1,3,0x2a,0,0,1,0]),
            65:bytearray(57),0:bytearray([1,1,0,0,1,2,0,0,1,3,0,0,1,4,0,0,1,5,0,0])}
        for i,value in enumerate((800,1600,2400,3200,6400,26000,800,1600)):
            struct.pack_into('<H',self.pages[65],1+i*2,value//50-1)
            self.pages[65][17+i*3:20+i*3]=bytes([(255 if i%3==0 else 0),(255 if i%3==1 else 0),(255 if i%3==2 else 0)])
        self.commands=[];self.profile_change=False;self.corrupt=False
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read_page(self,page):return bytes(self.pages[page])
    def state(self):return decode(self.pages,'wireless')
    def send(self,main,sub,data=b'',**kwargs):
        self.commands.append((main,sub,bytes(data)))
        if main==53:self.pages[64][sub]=data[0]
        elif main==48:self.pages[0][sub:sub+4]=data
        elif main==58:
            index=(data[0]>>4)-1
            self.pages[64][2]=(data[0]&15)|((index+1)<<4)
            self.pages[65][1+index*2:3+index*2]=data[1:3]
            self.pages[65][17+index*3:20+index*3]=data[3:6]
            if data[6]&128:self.pages[65][41+index*2:43+index*2]=data[7:9]
        elif (main,sub)==(6,255):return
        else:raise AssertionError('Unexpected setter')
        if self.profile_change:self.pages[64][9]=1;self.pages[129][1]=0x31
        if self.corrupt:self.pages[64][7]^=1


class Codec(unittest.TestCase):
    def test_frame_checksum_and_response_match_size_page_encapsulation(self):
        p=packet(79,67,encap=2)
        self.assertEqual(len(p),64);self.assertEqual(p[:7],bytes([3,sum(p[2:])&255,0x50,0,2,79,67]))
        raw=bytes([3,0x50,0,3,2,67,9,8,7])+bytes(55)
        self.assertEqual(response(raw,67,2),bytes([9,8,7]))
        for wrong in [(66,2),(67,0)]:
            with self.assertRaises(ValueError):response(raw,*wrong)
        with self.assertRaises(ValueError):response(bytes([3,0x50,2,0,0,0])+bytes(58),0)

    def test_split_read_collects_real_payloads_not_zero_padding(self):
        from logi_center.adapters.eweadn.eweadn_adapter import Transport
        chunks=[];sent=[]
        class ReadWire(Transport):
            def send(self,main,sub,data=b'',encap=0):
                sent.append((main,sub,encap));payload=bytes(range(encap*10,min(57,(encap+1)*10)))
                chunks.append(bytes([3,0x50,0,len(payload),encap,sub])+payload+bytes(64-6-len(payload)))
            def get(self):return chunks.pop(0)
        with patch('logi_center.adapters.eweadn.eweadn_adapter.time.sleep'):
            self.assertEqual(ReadWire('unused').read_page(65),bytes(range(57)))
        self.assertEqual(sent,[(79,65+i,i) for i in range(6)])

    def test_real_model_is_required_not_shared_pid(self):
        wire=Wire();state=wire.state();self.assertEqual(state['model_id'],'s9ultra')
        self.assertEqual(state['sensor_config']['polling_rate'],4000)
        self.assertEqual(state['dpi_config']['x5'],26000)
        wire.pages[128][2:]=b'\x01'*6
        with self.assertRaises(ValueError):wire.state()
        wire=Wire();wire.pages[64][9]=1
        with self.assertRaises(ValueError):wire.state()

    def test_flags_read_modify_write_preserves_unknown_and_glass_bits(self):
        state=Wire().state();flags=state['pages']['64'][5]
        commands,pages=prepare(state,'sensor_config',{'motion_sync':False,'performance_mode':2,'ripple':True})
        self.assertEqual(commands,[(53,5,bytes([(flags&~0xf4)|0x90]))])
        self.assertEqual(pages['64'][5]&0x0b,flags&0x0b)
        self.assertEqual(pages['0'],state['pages']['0']);self.assertEqual(pages['65'],state['pages']['65'])

    def test_polling_uses_native_codes_and_preserves_other_connection_bits(self):
        state=Wire().state();state['pages']['64'][1]=0xa5
        commands,pages=prepare(state,'sensor_config',{'polling_rate':2000})
        self.assertEqual(commands,[(53,1,b'\xa6')])
        self.assertEqual(pages['64'][1]&0xf8,0xa0)
        state['connection']='usb';commands,_=prepare(state,'sensor_config',{'polling_rate':8000})
        self.assertEqual(commands,[(53,1,b'\xc5')])
        for value in (True,1234,16000):
            with self.assertRaises(ValueError):prepare(state,'sensor_config',{'polling_rate':value})

    def test_sleep_uses_official_thirty_second_levels_not_archive_minutes(self):
        state=Wire().state();self.assertEqual(state['sensor_config']['sleep'],30)
        commands,pages=prepare(state,'sensor_config',{'sleep':60})
        self.assertEqual(commands,[(53,8,b'\x02')]);self.assertEqual(pages['64'][8],2)
        for value in (1,31,3030):
            with self.assertRaises(ValueError):prepare(state,'sensor_config',{'sleep':value})

    def test_dpi_colors_count_and_active_stage_restored_last(self):
        state=Wire().state();commands,pages=prepare(state,'dpi_config',{'x2':1200,'y2':1200,'color2':[1,2,3]})
        self.assertEqual(commands[0],(58,0,bytes([0x36,23,0,1,2,3,0,0,0])))
        self.assertEqual(commands[-1][2][0],0x16)
        self.assertEqual(pages['64'][2],0x16)
        commands,pages=prepare(state,'dpi_config',{'active':3})
        self.assertEqual(len(commands),1);self.assertEqual(commands[0][2][0],0x46)
        self.assertEqual(pages['64'][2],0x46)
        for changes in ({'x1':1234},{'count':0},{'active':7},{'color0':[256,0,0]}):
            with self.assertRaises(ValueError):prepare(state,'dpi_config',changes)
        with self.assertRaises(ValueError):prepare(state,'dpi_config',{'count':4,'x5':800})

    def test_buttons_preserve_left_click_and_block_unverified_slots(self):
        state=Wire().state()
        with self.assertRaises(ValueError):prepare(state,'button_bindings',{'0':[1,2,0,0]})
        commands,_=prepare(state,'button_bindings',{'2':[2,6,0,0]})
        self.assertEqual(commands,[(48,8,bytes([2,6,0,0]))])
        state['writable_buttons']=[0,1,2]
        with self.assertRaises(ValueError):prepare(state,'button_bindings',{'3':[1,5,0,0]})
        with self.assertRaises(ValueError):prepare(state,'button_bindings',{'2':[6,1,1,0]})


class Hardware(unittest.TestCase):
    def invoke(self,wire,action='read',field=None,changes=None):
        state=wire.state();payload={'changes':changes,'profile':state['profiles'],'fingerprint':fingerprint(state)} if changes else None
        with patch('logi_center.adapters.eweadn.eweadn_adapter.candidates',return_value=[ITEM]),patch('logi_center.adapters.eweadn.eweadn_adapter.time.sleep'),patch('logi_center.core.services.drafts.atomic_json'):
            return hardware(action,TARGET,field,payload,transport=lambda _:wire)
    def test_reads_only_and_configuration_set_readback(self):
        wire=Wire();self.invoke(wire);self.assertEqual(wire.commands,[])
        actual=self.invoke(wire,'set','sensor_config',{'debounce':7,'motion_sync':False})
        self.assertEqual(actual['sensor_config']['debounce'],7);self.assertFalse(actual['sensor_config']['motion_sync'])
        self.assertEqual(wire.commands,[(53,4,b'\x07'),(53,5,b'\x0a')])
    def test_left_click_is_established_and_verified_before_removing_original(self):
        wire=Wire();original=wire.send
        def ignore_new_left(main,sub,data=b''):
            if (main,sub)==(48,16):wire.commands.append((main,sub,data));return
            original(main,sub,data)
        wire.send=ignore_new_left
        with self.assertRaises(Fault):self.invoke(wire,'set','button_bindings',{'0':[1,2,0,0],'4':[1,1,0,0]})
        self.assertEqual(len(wire.commands),1);self.assertEqual(wire.commands[0][1],16)
        self.assertEqual(list(wire.pages[0][:4]),[1,1,0,0])
    def test_stale_fingerprint_disconnection_and_foreign_change_block(self):
        wire=Wire();bad={'changes':{'sleep':2},'profile':0,'fingerprint':'old'}
        with patch('logi_center.adapters.eweadn.eweadn_adapter.candidates',return_value=[ITEM]):
            with self.assertRaises(Fault):hardware('set',TARGET,'sensor_config',bad,transport=lambda _:wire)
        self.assertEqual(wire.commands,[])
        with patch('logi_center.adapters.eweadn.eweadn_adapter.candidates',return_value=[]):
            with self.assertRaises(Fault):hardware('read',TARGET,transport=lambda _:wire)
        wire.corrupt=True
        with self.assertRaises(Fault):self.invoke(wire,'set','sensor_config',{'debounce':6})
        self.assertEqual(len(wire.commands),1)
    def test_reset_requires_confirmation_and_is_reported_as_unverified(self):
        from logi_center.adapters.eweadn.eweadn_adapter import reset_plan
        wire=Wire()
        with self.assertRaises(ValueError):reset_plan(TARGET,wire.state(),False)
        def runner(args,**kwargs):
            value=json.loads(args[5]);return json.dumps(self.invoke(wire,'set',args[4],value['changes']))
        result=perform(reset_plan(TARGET,wire.state(),True),runner)
        self.assertEqual(result.state,State.SENT);self.assertEqual(wire.commands,[(6,255,b'')])

    def test_one_khz_connection_limit_is_enforced_before_any_write(self):
        for pid in ('103d','1029'):
            item={**ITEM,'pid':pid};wire=Wire()
            with patch('logi_center.adapters.eweadn.eweadn_adapter.candidates',return_value=[item]):
                state=hardware('read',selector(item),transport=lambda _:wire)
                self.assertEqual(state['max_report'],0)
                with self.assertRaises(ValueError):
                    setting_plan(selector(item),'sensor_config',{'polling_rate':2000},state)
            self.assertEqual(wire.commands,[])

    def test_profile_switch_stops_remaining_commands(self):
        wire=Wire();wire.profile_change=True
        with self.assertRaises(Fault):self.invoke(wire,'set','sensor_config',{'debounce':7,'sleep':60})
        self.assertEqual(len(wire.commands),1)


class Integration(unittest.TestCase):
    def test_two_units_remain_separate_and_aux_keyboard_requires_exact_physical_peer(self):
        from logi_center.core.devices.devices import Device
        from logi_center.adapters.eweadn.eweadn_adapter import EweadnAdapter
        with tempfile.TemporaryDirectory() as folder:
            items=[]
            for n in (1,2):
                p=Path(folder)/str(n);p.mkdir()
                for key,value in [('idVendor','372e'),('idProduct','1026'),('product','EWEADN receiver')]:
                    (p/key).write_text(value)
                items.append({**ITEM,'physical':str(p),'generation':str(p)+'/hid','node':'/simulation/'+str(n)})
            calls=[]
            def runner(args):calls.append(args);return json.dumps(Wire().state())
            adapter=EweadnAdapter(folder,runner=runner)
            with patch('logi_center.adapters.eweadn.eweadn_adapter.candidates',return_value=items):rows=adapter.discover()
            self.assertEqual(len(rows),2);self.assertNotEqual(rows[0].target,rows[1].target)
            self.assertNotEqual(rows[0].id,rows[1].id)
            self.assertTrue(all(args[2]=='read' for args in calls))
            same=Device('aux','Receiver keyboard','keyboard','linux-input','aux',physical=rows[0].physical+'|event1',vid='372e',pid='1026')
            other=Device('other','Keyboard','keyboard','linux-input','other',physical='/other-port',vid='372e',pid='1026')
            adapter.associate([*rows,same,other]);self.assertEqual(same.kind,'interface');self.assertEqual(other.kind,'keyboard')

    def test_battery_status_is_targeted_and_old_instance_is_ignored(self):
        from logi_center.core.devices.devices import Device
        from logi_center.core.services.battery_service import collect,apply
        from tests.unit.test_battery_service import NoKernel
        d=Device('s9','S9','mouse','eweadn',TARGET,capabilities=capabilities(TARGET,Wire().state()))
        calls=[]
        def runner(args):calls.append(args);return json.dumps({'battery_status':52,'charging':True})
        outcome=collect([d],runner,kernel_factory=NoKernel)
        self.assertEqual(calls,[['logi-sdk','eweadn','status',TARGET]])
        self.assertEqual(apply([d],outcome),(False,True))
        cap=next(c for c in d.capabilities if c.name=='battery_status')
        self.assertEqual((cap.value,cap.source),(52,'device'))
        d.targets={'eweadn':['reconnected']};outcome[0][0]=(d.id,'eweadn',TARGET,{'battery_status':1},None)
        apply([d],outcome);self.assertEqual(cap.value,52)

    def test_shared_receiver_artwork_requires_native_s9_model_identity(self):
        from logi_center.core.devices.device_artwork import DeviceArtworkProvider
        from logi_center.core.devices.devices import Device
        with tempfile.TemporaryDirectory() as folder:
            provider=DeviceArtworkProvider(Path(__file__).resolve().parents[2]/'assets/devices',data_dir=Path(folder))
            d=Device('s9','Unverified receiver','mouse','eweadn',TARGET,vid='372e',pid='1026')
            self.assertNotEqual(provider.resolve(d).source,'exact-model')
            d.capabilities=capabilities(TARGET,Wire().state())
            artwork=provider.resolve(d)
            self.assertEqual((artwork.source,artwork.path.name),('exact-model','eweadn-s9.svg'))
            self.assertAlmostEqual(provider.describe(artwork)['aspect'],250/485)

    def test_macro_repeat_modes_roundtrip_without_changing_legacy_entries(self):
        from logi_center.core.services.drafts import DraftStore
        from logi_center.core.services.macro_library import KEY,create,load
        with tempfile.TemporaryDirectory() as folder:
            store=DraftStore(Path(folder)/'logi_center.core.services.drafts.json');legacy=create('Legacy');held=create('Held');held['repeat_mode']='held'
            store.edit(KEY,[],[legacy,held]);self.assertEqual(load(store),[legacy,held])
            held['repeat_mode']='invalid';store.edit(KEY,[],[held])
            with self.assertRaises(ValueError):load(store)


try:
    from PySide6.QtCore import QObject,QCoreApplication
    from logi_center.qml_ui.bridge.editor import EditorController
except ImportError:QCoreApplication=None


@unittest.skipIf(QCoreApplication is None,'PySide6 unavailable')
class Editor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QCoreApplication.instance() or QCoreApplication([])
    def setUp(self):
        from logi_center.core.devices.devices import Device,DeviceManager
        from logi_center.core.services.drafts import DraftStore
        self.tmp=tempfile.TemporaryDirectory();self.owner=QObject();self.owner.tr=lambda text:text;self.owner.refresh=lambda:None
        self.owner._preferences_pool=ThreadPoolExecutor(max_workers=1);self.pool=ThreadPoolExecutor(max_workers=1);self.wire=Wire();self.writes=[]
        self.device=Device('unit-ewe','EWEADN S9 Ultra','mouse','eweadn',TARGET,physical=ITEM['physical'],vid='372e',pid='1026',connection='wireless',simulated=True)
        self.manager=DeviceManager();self.manager.devices=[self.device]
        self.ed=EditorController(self.owner,self.pool,store=DraftStore(Path(self.tmp.name)/'logi_center.core.services.drafts.json'),runner=self.runner)
        self.device.capabilities=capabilities(TARGET,self.wire.state());self.ed.bind(self.manager,self.device);self.wait()
    def runner(self,args,**kwargs):
        with patch('logi_center.adapters.eweadn.eweadn_adapter.candidates',return_value=[ITEM]),patch('logi_center.adapters.eweadn.eweadn_adapter.time.sleep'),patch('logi_center.core.services.drafts.atomic_json'):
            if args[2]=='set':self.writes.append(args)
            return json.dumps(hardware(args[2],args[3],args[4] if len(args)>4 else None,json.loads(args[5]) if len(args)>5 else None,transport=lambda _:self.wire))
    def wait(self):
        end=time.monotonic()+4
        while self.ed.busy and time.monotonic()<end:self.app.processEvents();time.sleep(.002)
        self.app.processEvents();self.assertFalse(self.ed.busy)
    def tearDown(self):
        self.ed.shutdown();self.pool.shutdown(wait=True);self.owner._preferences_pool.shutdown(wait=True);self.tmp.cleanup()
    def test_draft_cancel_apply_and_native_confirmation(self):
        self.ed.setSection('pointer');self.ed.edit('eweadn:dpi_config:x1',1200)
        self.assertEqual(self.writes,[]);self.assertEqual(self.ed.dirtyCount,2)
        self.ed.discardGroup();self.assertEqual(self.ed.dirtyCount,0)
        self.ed.setSection('advanced');self.ed.edit('eweadn:sensor_config:motion_sync',False);self.ed.applyGroup();self.wait()
        self.assertEqual(len(self.writes),1);self.assertEqual(self.ed.resultState,'confirmed')
        self.assertEqual(self.wire.pages[64][5],0x0a)
    def test_no_delegate_reset_and_profile_scoped_drafts(self):
        self.ed.setSection('pointer');events=[];self.ed.eweadnDpiModel.modelReset.connect(lambda:events.append('reset'))
        self.ed.eweadnDpiModel.rowsRemoved.connect(lambda *a:events.append('remove'))
        self.ed.edit('eweadn:dpi_config:x0',900);self.ed.setSection('other');self.ed.setSection('pointer')
        self.assertEqual(self.ed.eweadnFields['eweadn:dpi_config:x0']['value'],900)
        self.assertTrue(all(':profile:0:' in f.draft_key for f in self.ed._controls if f.backend=='eweadn'))
        # Leaving Pointer may temporarily remove display rows; ordinary edits
        # within the page must update cells without destroying slider delegates.
        events.clear();self.ed.edit('eweadn:dpi_config:x0',1000);self.assertEqual(events,[])
    def test_local_macro_capture_and_disconnection_never_write(self):
        self.ed.setSection('macros');self.ed.createLibraryMacro('Mouse test');self.ed.setRecording(True)
        self.assertTrue(self.ed.recording);self.ed.stopRecording();self.ed.addPause(100);self.ed.saveLibraryMacro('Mouse test')
        self.assertTrue(self.ed.macroLibraryAvailable);self.assertFalse(self.ed.macroSupported)
        self.device.connected=False;self.ed.applyGroup();self.assertEqual(self.writes,[])

    def test_old_reset_dialog_context_cannot_reset_a_refreshed_device(self):
        context=self.ed.eweadnContext
        self.wire.pages[64][4]=9;self.ed.reload();self.wait()
        self.assertNotEqual(context,self.ed.eweadnContext)
        self.ed.resetEweadn(True,context);self.assertEqual(self.writes,[])

    def test_failed_refresh_marks_previous_values_stale_and_success_clears_it(self):
        self.ed.setSection('advanced');original=self.ed.runner
        def failed(*args,**kwargs):raise Fault(__import__('execution').FaultCode.TIMEOUT,'eweadn','Unavailable')
        self.ed.runner=failed;self.ed.reload();self.wait()
        self.assertTrue(self.ed.liveReadError)
        self.assertTrue(all(row['stale'] for row in self.ed.fields._rows))
        self.ed.runner=original;self.ed.reload();self.wait()
        self.assertFalse(self.ed.liveReadError)
        self.assertTrue(all(not row['stale'] for row in self.ed.fields._rows));self.assertEqual(self.writes,[])

    def test_disabling_stage_preserves_but_does_not_apply_its_draft(self):
        self.ed.setSection('pointer');self.ed.edit('eweadn:dpi_config:x5',1200)
        self.ed.edit('eweadn:dpi_config:count',4)
        self.assertNotIn('eweadn:dpi_config:x5',self.ed.eweadnFields)
        self.ed.applyGroup();self.wait()
        self.assertEqual(self.ed.resultState,'confirmed')
        self.assertEqual(self.wire.state()['dpi_config']['x5'],26000)
        self.ed.edit('eweadn:dpi_config:count',6)
        self.assertEqual(self.ed.eweadnFields['eweadn:dpi_config:x5']['value'],1200)


if __name__=='__main__':unittest.main()
