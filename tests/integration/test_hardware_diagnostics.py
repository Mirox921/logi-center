"""Reported S9/G515 failures reproduced without USB/HID configuration writes."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import contextlib,io,json,subprocess,tempfile,unittest

from logi_center.adapters.eweadn.eweadn_adapter import Transport,ReadTrace,read_state,capabilities
from logi_center.protocols.eweadn_protocol import response,ResponseError
from logi_center.core.services.execution import Fault,FaultCode
from tests.unit.test_eweadn import Wire,ITEM


class S9ReadDiagnostics(unittest.TestCase):
    def test_receiver_0b_length_variant_keeps_exact_payload_and_header_checks(self):
        payload=bytes(range(10))
        raw=bytes([3,0x50,0,11,0,128])+payload
        self.assertEqual(response(raw,128),payload)
        for bad in (raw[:-1],raw+bytes(1),raw[:3]+bytes([12])+raw[4:]):
            with self.assertRaises(ResponseError):response(bad,128)
        with self.assertRaises(ResponseError):response(raw,129)
        with self.assertRaises(ResponseError):response(raw,128,1)

    def test_receiver_zero_offset_variant_keeps_chunk_type_and_identity_validation(self):
        payload=bytes(range(10))
        raw=bytes([3,0x50,0,11,0,0])+payload
        self.assertEqual(response(raw,128),payload)
        with self.assertRaises(ResponseError):response(raw,128,1)
        with self.assertRaises(ResponseError):response(raw[:1]+b'\x65'+raw[2:],128)
        from logi_center.protocols.eweadn_protocol import model_identity
        with self.assertRaises(ValueError):model_identity(response(raw,128))

    def test_zero_offset_pages_reach_complete_validated_state_without_setters(self):
        pages=Wire().pages
        class Receiver(Transport):
            def __init__(self):super().__init__('unused');self.requests=[]
            def send(self,main,offset,data=b'',encap=0):
                self.requests.append((main,offset,encap))
            def get(self):
                main,offset,index=self.requests[-1]
                payload=bytes(pages[offset-index][index*10:(index+1)*10]).ljust(10,b'\0')
                return bytes([3,0x50,0,11,index,0])+payload
        receiver=Receiver()
        with patch('logi_center.adapters.eweadn.eweadn_adapter.time.sleep'):
            state=read_state(receiver,'wireless')
        self.assertEqual(state['model_id'],Wire().state()['model_id'])
        self.assertTrue(all(main==79 for main,_,_ in receiver.requests))


    def test_documented_short_final_frames_stop_without_requesting_missing_data(self):
        for page,size in ((65,41),(0,12)):
            class Short(Transport):
                def __init__(self):super().__init__('unused');self.sent=[];self.payload=bytes(range(size))
                def send(self,main,offset,data=b'',encap=0):self.sent.append((main,offset,encap))
                def get(self):
                    main,offset,chunk=self.sent[-1];data=self.payload[chunk*10:(chunk+1)*10]
                    return bytes([3,0x50,0,len(data),chunk,offset])+data
            wire=Short()
            with self.subTest(page=page),patch('logi_center.adapters.eweadn.eweadn_adapter.time.sleep'):
                self.assertEqual(wire.read_page(page),bytes(range(size)))
            self.assertEqual(len(wire.sent),(size+9)//10)

    def test_short_dpi_page_never_validates_independent_axes(self):
        wire=Wire();wire.pages[65]=wire.pages[65][:41];wire.pages[64][1]|=128
        with self.assertRaises(ValueError):read_state(wire,'wireless',allow_partial=True)

    def test_get_feature_uses_actual_count_and_never_promotes_padding_to_data(self):
        wire=Transport('unused');wire.fd=123
        valid=bytes([3,0x50,0,8,0,128])+bytes(range(8))
        def ioctl(fd,request,buf,mutate):
            buf[:len(valid)]=valid
            return len(valid)
        with patch('logi_center.adapters.eweadn.eweadn_adapter.fcntl.ioctl',side_effect=ioctl):
            raw=wire.get()
        self.assertEqual(len(raw),14);self.assertEqual(response(raw,128),bytes(range(8)))
        def truncated(fd,request,buf,mutate):
            buf[:8]=valid[:8]
            return 8
        with patch('logi_center.adapters.eweadn.eweadn_adapter.fcntl.ioctl',side_effect=truncated):
            with self.assertRaises(ResponseError):response(wire.get(),128)

    def test_protocol_timeout_identifies_page_chunk_and_rejection(self):
        class Stale(Transport):
            def send(self,*args,**kwargs):pass
            def get(self):return bytes([3,0x50,0,8,0,129])+bytes(58)
        trace=ReadTrace();wire=Stale('unused',trace)
        clock=iter(i*.2 for i in range(1000))
        with patch('logi_center.adapters.eweadn.eweadn_adapter.time.monotonic',side_effect=lambda:next(clock)),patch('logi_center.adapters.eweadn.eweadn_adapter.time.sleep'):
            with self.assertRaises(Fault) as error:wire.read_page(128)
        self.assertEqual(error.exception.code,FaultCode.TIMEOUT)
        self.assertIn('page 128, chunk 0',error.exception.message)
        self.assertEqual([e['attempt'] for e in trace.events if e['event']=='request'],[1,2,3])
        self.assertTrue(any(e.get('reason')=='offset' for e in trace.events))
        self.assertEqual(trace.events[-1]['event'],'protocol_timeout')

    def test_rejects_macro_reply_wrong_chunk_and_oversized_payload(self):
        for header,reason in (([3,0x65,0,8,0,128],'command_type'),
                              ([3,0x50,0,8,1,128],'encapsulation'),
                              ([3,0x50,0,11,0,128],'payload_length')):
            with self.subTest(reason=reason),self.assertRaises(ResponseError) as error:
                response(bytes(header)+bytes(64-len(header)),128)
            self.assertEqual(error.exception.reason,reason)

    def test_partial_identity_and_battery_never_enable_writes(self):
        class Sleeping(Wire):
            def read_page(self,page):
                if page==64:raise Fault(FaultCode.TIMEOUT,'eweadn','Page 64 chunk 0 timed out')
                return super().read_page(page)
        wire=Sleeping();state=read_state(wire,'wireless',allow_partial=True)
        self.assertTrue(state['partial']);self.assertEqual(state['read_error']['page'],64)
        caps=capabilities('private-selector',state)
        self.assertTrue(any(c.name=='battery_status' and c.readable for c in caps))
        self.assertFalse(any(c.writable or c.plan for c in caps))
        self.assertEqual(wire.commands,[])
        with self.assertRaises(Fault):read_state(wire,'wireless')
        wire.pages[128][2:]=bytes(6)
        with self.assertRaises(ValueError):read_state(wire,'wireless',allow_partial=True)

    def test_worker_deadline_preserves_only_safe_progress_without_raw_data(self):
        from scripts.eweadn_read_diagnostics import collect
        progress='LOGI_EWEADN_TRACE '+json.dumps({'event':'get_feature_start','elapsed_ms':12,'page':128,'chunk':0,'raw':'SECRET'})+'\n'
        process=Mock();process.communicate.side_effect=[subprocess.TimeoutExpired('worker',20,stderr=progress),('',progress)]
        process.poll.return_value=None
        with patch('scripts.eweadn_read_diagnostics._stop') as stop:
            report=collect(inventory=[ITEM],popen=Mock(return_value=process))
        stop.assert_called_once_with(process)
        self.assertEqual(report['state'],'worker_deadline')
        self.assertEqual(report['events'][0]['event'],'get_feature_start')
        raw=json.dumps(report)
        for private in ('SECRET',ITEM['physical'],ITEM['node'],ITEM['descriptor']):self.assertNotIn(private,raw)


RGB={'readable':False,'effects':[
    {'id':1,'parameters':{'color':{}}},
    {'id':10,'parameters':{'color':{},'period':{'minimum':1000,'maximum':20000,'default':5000},'intensity':{'minimum':0,'maximum':100,'default':100}}},
    {'id':21,'parameters':{'saturation':{'minimum':0,'maximum':255,'default':255},'period':{'minimum':1000,'maximum':20000,'default':5000},'intensity':{'minimum':0,'maximum':100,'default':100}}},
    {'id':22,'parameters':{'saturation':{'minimum':0,'maximum':255,'default':255},'period':{'minimum':1000,'maximum':20000,'default':5000},'intensity':{'minimum':0,'maximum':100,'default':100},'direction':{'choices':[0,1,2,3]}}},
    {'id':23,'parameters':{'color':{},'saturation':{'minimum':0,'maximum':255,'default':255},'period':{'minimum':2,'maximum':200,'default':20}}}]}


class G515Effects(unittest.TestCase):
    def test_zone_cli_installs_guard_before_execution(self):
        from logi_center.adapters.logitech.solaar_write import main
        templates=SimpleNamespace()
        events=[]
        modules={'logitech_receiver':SimpleNamespace(settings_templates=templates),
                 'solaar':SimpleNamespace(cli=SimpleNamespace(_find_device=lambda *args:())),
                 'solaar.gtk':SimpleNamespace(main=lambda:events.append('execute'))}
        with patch.dict('sys.modules',modules),patch(
                'logi_center.adapters.logitech.solaar_write.guard_effect_write',
                side_effect=lambda value:events.append('guard')):
            main(['config','G515 LS TKL','rgb_zone_1','!LEDEffectSetting {ID: 21}'])
        self.assertEqual(events,['guard','execute'])


    def test_effect_write_refreshes_process_local_control_and_rejects_cached_success(self):
        from logi_center.adapters.logitech.solaar_write import guard_effect_write
        sent=[]
        control=SimpleNamespace(name='rgb_control',_value=None,
            _rw=SimpleNamespace(read=Mock(return_value=b'\x03')),
            _validator=SimpleNamespace(validate_read=lambda raw:raw==b'\x03'))
        class Effect:
            def __init__(self):self._device=SimpleNamespace(settings=[control])
            def write(self,value,save=True):
                if control._value:sent.append(value)
                return value
        guard_effect_write(SimpleNamespace(RGBEffectSetting=Effect))
        effect=Effect();self.assertEqual(effect.write(21,save=False),21)
        self.assertEqual(sent,[21]);self.assertIs(control._value,True)
        for reply in (b'',None,b'\x00'):
            control._rw.read.return_value=reply
            with self.assertRaises(RuntimeError):effect.write(22)
        self.assertEqual(sent,[21])


    def test_readonly_configuration_changes_remain_in_memory(self):
        from logi_center.adapters.logitech.solaar_write import freeze_configuration
        configuration=SimpleNamespace(save=Mock(side_effect=AssertionError('disk write')),
                                      do_save=Mock(side_effect=AssertionError('disk write')))
        freeze_configuration(configuration)
        configuration.save(True);configuration.do_save()

    def test_remote_report_never_exports_cached_identity_palette_or_promotes_rgb(self):
        from scripts.g515_read_diagnostics import collect
        from tests.unit.test_g515_adapter import OUTPUT
        text='#   logi-center-rgb: '+json.dumps(RGB)+'\nrgb_zone_1 = !LEDEffectSetting {ID: 21, period: 5000}\n'
        with patch('logi_center.adapters.external.backend.saved_keyboard',return_value={'_serial':'SECRET','per-key-lighting':{'1':'PRIVATE'}}):
            report=collect(runner=lambda args,**kw:text if args[-1]=='rgb_zone_1' else OUTPUT[args[-1]])
        self.assertEqual(report['effect_source'],'backend_cache')
        self.assertFalse(report['rgb_control']['value'])
        self.assertEqual(report['persistence'],'unverified')
        for private in ('SECRET','PRIVATE'):self.assertNotIn(private,json.dumps(report))
        self.assertNotIn('per-key-lighting',report)
        self.assertEqual([r['setting'] for r in report['reads']],['rgb_control','brightness_control','rgb_zone_1','per-key-lighting','rgb_idle_timeout','rgb_sleep_timeout'])

    def test_native_modes_and_effect_specific_ranges_are_not_global_enum_guesses(self):
        from logi_center.core.services.control_service import g515_controls,g515_lighting_plans
        fields=g515_controls([{'key':'rgb_zone_1','native_rgb':RGB}],{'rgb_zone_1':{'ID':'1','color':'0xffffff'}})
        effect=next(f for f in fields if f.id=='g515:effect')
        self.assertEqual(effect.choices,[1,10,21,22,23])
        ripple=next(f for f in fields if f.id=='g515:period:23')
        self.assertEqual((ripple.minimum,ripple.maximum,ripple.observed),(2,200,20))
        self.assertNotIn('мс',ripple.label)
        cycle=g515_lighting_plans(21,[1,2,3],effect_info=RGB)
        self.assertIn('saturation: 255',cycle[-1].command[-1]);self.assertIsNone(cycle[-1].reader)
        self.assertEqual(cycle[0].command[-2:],['rgb_control','true'])
        wave=g515_lighting_plans(22,[1,2,3],effect_info=RGB,parameters={'direction':2})
        self.assertIn('direction: 2',wave[-1].command[-1])
        self.assertIn('period: 20',g515_lighting_plans(23,[1,2,3],period=20,effect_info=RGB)[-1].command[-1])
        with self.assertRaises(ValueError):g515_lighting_plans(23,[1,2,3],period=5000,effect_info=RGB)
        with self.assertRaises(ValueError):g515_lighting_plans(22,[1,2,3])

    def test_cycle_also_supplies_saturation_on_legacy_scoped_backends(self):
        from logi_center.core.services.control_service import g515_lighting_plans
        self.assertIn('saturation: 255',g515_lighting_plans(21,[1,2,3])[-1].command[-1])

    def test_write_only_zone_metadata_is_not_hardware_state(self):
        from logi_center.adapters.logitech.g515_adapter import read_snapshot
        from tests.unit.test_g515_adapter import OUTPUT
        text='#   logi-center-rgb: '+json.dumps(RGB)+'\nrgb_zone_1 = !LEDEffectSetting {ID: 21, period: 5000}\n'
        snapshot=read_snapshot(cache={},runner=lambda args,**kw:text if args[-1]=='rgb_zone_1' else OUTPUT[args[-1]])
        self.assertEqual(snapshot['sources']['rgb_zone_1'],'backend_cache')
        self.assertEqual(snapshot['rgb_capabilities'],RGB)
        self.assertIs(snapshot['saved']['rgb_control'],False)

    def test_led_control_failure_prevents_effect_write_and_cache_never_confirms(self):
        from logi_center.core.services.control_service import g515_lighting_plans
        from logi_center.core.services.operations import perform,State
        plans=g515_lighting_plans(21,[1,2,3],effect_info=RGB)
        calls=[]
        def runner(args):calls.append(args);return 'rgb_control = False\n' if len(args)==4 else ''
        result=perform(plans[0],runner)
        self.assertEqual(result.state,State.MISMATCH)
        self.assertFalse(result.accepted)
        self.assertFalse(any('rgb_zone_1' in args for args in calls))
        self.assertEqual(perform(plans[-1],lambda args:'').state,State.SENT)

    def test_metadata_comes_from_device_options_and_respects_write_only_getter(self):
        from logi_center.adapters.logitech.solaar_write import rgb_metadata
        option=SimpleNamespace(ID=21)
        setting=SimpleNamespace(_validator=SimpleNamespace(options=[option],readable=True),
            _rw=SimpleNamespace(read_fnid=None),possible_fields=[{'name':'period','min':1000,'max':20000}])
        templates=SimpleNamespace(hidpp20=SimpleNamespace(LEDEffects={21:['Cycle',{'period':6},{'period':5000}]}))
        self.assertEqual(rgb_metadata(setting,templates),{'readable':False,'effects':[{'id':21,'parameters':{'period':{'minimum':1000,'maximum':20000,'default':5000}}}]})


class InventoryEvidence(unittest.TestCase):
    def test_optional_missing_providers_do_not_hide_input_devices(self):
        from logi_center.core.devices.devices import Device,DeviceManager
        missing=SimpleNamespace(name='openrgb',discover=Mock(side_effect=Fault(FaultCode.MISSING,'openrgb','Not installed')))
        physical=Device('kernel','G515 LS TKL','keyboard','linux-input')
        manager=DeviceManager([missing,SimpleNamespace(discover=lambda:[physical])])
        manager.discover()
        self.assertEqual(manager.active('keyboard'),[physical])
        self.assertEqual(manager.faults[0].code,FaultCode.MISSING)

    def test_ambiguous_paired_serials_do_not_attach_saved_settings(self):
        from logi_center.core.devices.devices import Device
        from logi_center.adapters.logitech.saved_solaar import SavedSolaarAdapter
        peers=[Device(str(i),'G515 LS TKL','keyboard','linux-input',physical='/receiver'+str(i),vid='046d',
                      private_identity={'solaar_serial':'abcd1234'}) for i in (1,2)]
        cache=Device('cache','G515 LS TKL','keyboard','solaar-local',connected=None,private_identity={'solaar_serial':'abcd1234'})
        SavedSolaarAdapter().associate([*peers,cache])
        self.assertEqual(cache.physical,'')

    def test_paired_serial_links_cache_without_changing_receiver_identity_or_writability(self):
        from logi_center.core.devices.devices import Device,DeviceManager
        from logi_center.adapters.logitech.saved_solaar import SavedSolaarAdapter
        from logi_center.core.services.reports import build_report
        with tempfile.TemporaryDirectory() as folder:
            config=Path(folder)/'solaar.yaml'
            config.write_text('- _NAME: G515 LS TKL\n  _serial: ABCD1234\n  rgb_zone_1: {ID: 21}\n')
            adapter=SavedSolaarAdapter(config)
            cached=adapter.discover()
            physical=Device('kernel','G515 LS TKL','keyboard','linux-input',physical='/receiver|slot1',vid='046d',pid='c547',private_identity={'solaar_serial':'abcd1234'})
            records=[physical,*cached];adapter.associate(records);merged=DeviceManager.merge(records)
            self.assertEqual(len(merged),1);self.assertEqual(merged[0].backend,'linux-input')
            self.assertEqual(merged[0].pid,'c547');self.assertTrue(merged[0].connected)
            self.assertEqual(merged[0].targets['solaar-local'],['abcd1234'])
            self.assertFalse(any(c.writable for c in merged[0].capabilities))
            report=json.dumps(build_report(SimpleNamespace(devices=merged,faults=[])))
            self.assertIn('rgb_zone_1',report);self.assertNotIn('abcd1234',report)

    def test_name_only_duplicate_models_and_wrong_serial_never_merge(self):
        from logi_center.core.devices.devices import Device,DeviceManager
        from logi_center.adapters.logitech.saved_solaar import SavedSolaarAdapter
        for hints in ({},{'solaar_serial':'different'}):
            real=Device('a','G515 LS TKL','keyboard','linux-input',physical='/receiver|slot1',vid='046d',pid='c547',private_identity=hints)
            cache=Device('b','G515 LS TKL','keyboard','solaar-local',connected=None,private_identity={'solaar_serial':'abcd1234'})
            SavedSolaarAdapter().associate([real,cache])
            self.assertEqual(len(DeviceManager.merge([real,cache])),2)

    def test_audio_routes_keep_distinct_anonymous_scopes(self):
        from logi_center.core.devices.devices import Device,DeviceManager
        from logi_center.core.capabilities import Capability
        from logi_center.core.services.reports import build_report
        manager=DeviceManager();manager.devices=[Device('audio','PRO X','audio','pactl',capabilities=[
            Capability(prefix+':'+name,'pactl') for prefix in ('output:private-output','microphone:private-input') for name in ('volume','mute')])]
        report=build_report(manager);caps=report['devices'][0]['capabilities']
        self.assertEqual([(c['scope'],c['endpoint_id']) for c in caps],[('output',1),('output',1),('microphone',2),('microphone',2)])
        self.assertNotIn('private-',json.dumps(report))
