"""G502 profile/cache, artwork metadata and macro library: no real device I/O."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from backend import read_mouse
from devices import RatbagAdapter
from drafts import DraftStore
from logitech_status import read_device
from mouse_models import G502_ART,scan_key,validate_macro
import macro_library
import test_qml_editor as common


class Workflow(unittest.TestCase):
    def test_qt_compatibility_assets_are_reproducible_without_changing_paths(self):
        import xml.etree.ElementTree as ET
        from scripts.prepare_g502_svg import compatible,SOURCES
        folder=Path(__file__).resolve().parent/'qml_ui/assets/devices/exact'
        for source,target in SOURCES.items():
            raw=(folder/source).read_bytes();prepared=(folder/target).read_bytes()
            self.assertEqual(compatible(raw),prepared)
            before=ET.fromstring(raw);after=ET.fromstring(prepared)
            self.assertEqual([n.get('d') for n in before.iter() if n.tag.endswith('}path')],
                             [n.get('d') for n in after.iter() if n.tag.endswith('}path')])
            self.assertFalse(any(n.tag.endswith('}clipPath') or 'clip-path' in n.attrib or 'rgba(' in str(n.attrib) for n in after.iter()))

    def test_supplied_svg_bytes_and_vector_contents_are_preserved(self):
        import hashlib,xml.etree.ElementTree as ET
        folder=Path(__file__).resolve().parent/'qml_ui/assets/devices/exact'
        lines=(folder/'g502-inputs.sha256').read_text().splitlines()
        self.assertEqual(len(lines),4)
        for line in lines:
            digest,name=line.split();raw=(folder/name).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),digest)
            tags={element.tag.rsplit('}',1)[-1] for element in ET.fromstring(raw).iter()}
            self.assertFalse(tags & {'image','script','foreignObject'})

    def test_live_profile_directory_overrides_daemon_cache_without_writes(self):
        info='Model: usb:046d:c08b:0\nProfile 0:\n  Report Rate: 1000Hz\n  LED: 0, depth: rgb, mode: cycle, duration: 8000, brightness: 255\nProfile 1: (active)\n  Report Rate: 1000Hz\n  LED: 0, depth: rgb, mode: on, color: ffffff\n'
        calls=[]
        def run(args):
            calls.append(args)
            if args[-1]=='info':return info
            if args[-1]=='capabilities':return 'on off cycle breathing'
            return '1000'
        data=read_mouse('exact-target',run,live_reader=lambda target:{'mode':'onboard','profile':0,'profile_count':2})
        self.assertEqual((data['active'],data['daemon_active'],data['profile_mismatch']),(0,1,True))
        self.assertEqual(data['profiles'][data['active']]['leds'][0]['mode'],'cycle')
        self.assertTrue(all('set' not in call for call in calls))

    def test_unavailable_live_read_keeps_cache_source_honest(self):
        run=lambda args:'Model: usb:046d:c08b:0\nProfile 1: (active)\n' if args[-1]=='info' else ''
        def fail(target):raise ValueError('Missing optional API')
        data=read_mouse('target',run,live_reader=fail)
        self.assertEqual(data['active'],1);self.assertTrue(data['live_profile_error'])
        self.assertNotIn('daemon_active',data)

    def test_incompatible_live_directory_is_not_displayed_as_verified_profile(self):
        run=lambda args:'Model: usb:046d:c08b:0\nProfile 1: (active)\n' if args[-1]=='info' else ''
        data=read_mouse('target',run,live_reader=lambda target:{'mode':'onboard','profile':0,'profile_count':5})
        self.assertEqual(data['active'],1);self.assertTrue(data['live_profile_error'])
        self.assertNotIn('daemon_active',data)

    def test_live_transport_closes_without_rgb_cleanup_and_rejects_identical_units(self):
        from logitech_status import hardware
        info=SimpleNamespace(vendor_id='046d',product_id='c08b')
        base=Mock();base.receivers_and_devices.return_value=[info]
        device=Mock();device.handle=123;device.cleanups=[Mock()]
        create=Mock(return_value=device);instances=[device]
        modules={'logitech_receiver':SimpleNamespace(base=base),
                 'logitech_receiver.device':SimpleNamespace(create_device=create,Device=SimpleNamespace(instances=instances)),
                 'logitech_receiver.hidpp20':SimpleNamespace(OnboardProfiles=Mock()),
                 'logitech_receiver.hidpp20_constants':SimpleNamespace(SupportedFeature=Mock())}
        with patch.dict('sys.modules',modules),patch('logitech_status.read_device',return_value={'profile':0}):
            self.assertEqual(hardware('read','usb:046d:c08b:0'),{'profile':0})
            base.close.assert_called_once_with(123);device.close.assert_not_called();device.cleanups[0].assert_not_called()
            self.assertEqual(instances,[])
            base.receivers_and_devices.return_value=[info,info];create.reset_mock()
            from execution import Fault
            with self.assertRaises(Fault):hardware('read','usb:046d:c08b:0')
            create.assert_not_called()

    def test_profile_directory_is_not_assumed_to_be_sector_minus_one(self):
        features=SimpleNamespace(ONBOARD_PROFILES=0x8100)
        device=Mock();device.feature_request.side_effect=[b'\x01',b'\x00\x05',b'ignored']
        class Profiles:
            @staticmethod
            def get_profile_headers(reader):
                reader.feature_request(0x8100,0x50,0)
                return [(5,1),(9,1)]
        result=read_device(device,features,Profiles)
        self.assertEqual(result['profile'],0);self.assertEqual(result['sector'],5)
        self.assertEqual([call.args[1] for call in device.feature_request.call_args_list],[0x20,0x40,0x50])

    def test_unexpected_library_write_request_is_denied_before_transport(self):
        device=Mock();device.feature_request.side_effect=[b'\x01',b'\x00\x01']
        class Profiles:
            @staticmethod
            def get_profile_headers(reader):return reader.feature_request(0x8100,0x30,1)
        with self.assertRaises(ValueError):read_device(device,SimpleNamespace(ONBOARD_PROFILES=0x8100),Profiles)
        self.assertEqual(device.feature_request.call_count,2)

    def test_detailed_inventory_has_settings_before_opening_editor(self):
        def run(args):
            if args==['ratbagctl','list']:return 'exact: Logitech G502 HERO'
            if args[-1]=='info':return 'Model: usb:046d:c08b:0\nProfile 0: (active)\n  Report Rate: 1000Hz\n    0: 800dpi (active)\n  LED: 0, depth: rgb, mode: cycle\n'
            if args[-1]=='capabilities':return 'on off cycle breathing'
            return '800 1000'
        device=RatbagAdapter(run,detailed=True).discover()[0]
        from device_presentation import available_settings
        self.assertGreater(available_settings(device),0)

    def test_top_and_side_are_disjoint_and_cover_eleven_native_ids(self):
        top=G502_ART['top']['anchors'];side=G502_ART['side']['anchors']
        self.assertEqual(set(top)|set(side),set(range(11)))
        self.assertFalse(set(top)&set(side));self.assertEqual(set(side),{3,4,5})
        for view in G502_ART.values():
            for x,y in view['anchors'].values():self.assertTrue(0<x<1 and 0<y<1)

    def test_physical_scan_codes_ignore_active_cyrillic_layout(self):
        for platform in ('wayland','xcb'):
            self.assertEqual(scan_key(38,platform),'KEY_A')
            self.assertEqual(scan_key(54,platform),'KEY_C')
            self.assertEqual(scan_key(36,platform),'KEY_ENTER')
        self.assertIsNone(scan_key(38,'offscreen'))

    def test_private_library_round_trip_multiple_macros_including_mouse(self):
        with tempfile.TemporaryDirectory() as directory:
            store=DraftStore(Path(directory)/'drafts.json')
            entries=[macro_library.create('Copy',['+KEY_LEFTCTRL','KEY_C','-KEY_LEFTCTRL']),
                     macro_library.create('Click',['+BTN_LEFT','t50','-BTN_LEFT'])]
            store.edit(macro_library.KEY,[],entries)
            self.assertEqual(macro_library.load(DraftStore(store.path)),entries)
            self.assertNotEqual(entries[0]['id'],entries[1]['id'])
            data=json.loads(store.path.read_text());self.assertEqual(data['version'],1)
            for bad in (['+BTN_LEFT'],['-KEY_A'],['+KEY_A','+KEY_A','-KEY_A'],['shell:command'],['t0']):
                with self.assertRaises(ValueError):validate_macro(bad)


@unittest.skipUnless(common.QCoreApplication,'Optional PySide6 unavailable')
class BridgeWorkflow(unittest.TestCase):
    setUpClass=classmethod(common.EditorTests.setUpClass.__func__)
    wait=common.EditorTests.wait
    tearDown=common.EditorTests.tearDown

    def setUp(self):
        common.EditorTests.setUp(self)
        self.device.name='Logitech G502 HERO';self.device.vid='046d';self.device.pid='c08b'
        self.device.backend='ratbagctl';self.device.backends=['ratbagctl'];self.device.targets={'ratbagctl':['exact']}
        self.device.capabilities=[];self.editor.bind(self.manager,self.device)
        self.state={'active':0,'text':'Model: usb:046d:c08b:0','dpis':[],'rates':[],'led_modes':{},'button_types':{i:[0,1,2,3,4] for i in range(11)},
            'profiles':[{'index':0,'rate':1000,'resolutions':[],'leds':[],'buttons':[{'index':i,'action':'button 1','macro':False} for i in range(11)]}]}
        self.editor.reader=lambda target:self.state
        self.wait()
        self.editor._ratbag=self.state;self.editor._build();self.calls=[]

    def test_both_views_retain_native_selection_and_library_does_not_write(self):
        self.editor.setSection('buttons')
        self.wait()
        self.assertEqual({b['index'] for b in self.editor.g502Buttons},{0,1,2,6,7,8,9,10})
        self.editor.setG502View('side');self.assertEqual({b['index'] for b in self.editor.g502Buttons},{3,4,5})
        self.editor.selectButton(5);self.assertEqual(self.editor.selectedButton,5)
        self.editor.createLibraryMacro('First');self.editor.setRecording(True)
        self.editor.recordKey('a',True);self.editor.recordKey('a',False);self.editor.stopRecording()
        self.editor.createLibraryMacro('Second');self.editor.setRecording(True)
        self.editor._record_event('BTN_LEFT',True);self.editor._record_event('BTN_LEFT',False);self.editor.stopRecording()
        self.assertEqual(len(self.editor.macroLibrary),2)
        self.owner._preferences_pool.submit(lambda:None).result()
        entries=macro_library.load(DraftStore(self.editor.store.path))
        self.assertEqual(entries[0]['tokens'],['+KEY_A','-KEY_A'])
        self.assertEqual(entries[1]['tokens'],['+BTN_LEFT','-BTN_LEFT'])
        self.editor.applyMacro();self.assertEqual(self.editor.resultState,'unsupported');self.assertEqual(self.calls,[])

    def test_connection_changes_both_views_without_changing_native_buttons(self):
        for connection,files in [('usb',('g502-top-wired-qt.svg','g502_hero_side_wired_fixed.svg')),
                                 ('wireless',('g502-top-wireless-qt.svg','g502_hero_side_wireless.svg'))]:
            self.device.connection=connection
            ids=set()
            for view,filename in zip(('top','side'),files):
                self.editor.setG502View(view)
                self.assertTrue(self.editor.buttonDiagram.endswith(filename))
                ids.update(row['index'] for row in self.editor.g502Buttons)
            self.assertEqual(ids,set(range(11)))
        self.assertEqual(self.calls,[])

    def test_changed_physical_profile_blocks_button_write_before_daemon_cache(self):
        self.state['daemon_active']=0
        def run(args,**unused):
            self.calls.append(args)
            if args[0]=='logi-sdk':return json.dumps({'mode':'onboard','profile':1})
            return '0'
        self.editor.runner=run
        index=next(i for i,row in enumerate(self.editor.assignments) if row['value']==['button','2'])
        self.editor.chooseAssignment(index);self.editor.applyAssignment(index);self.wait()
        self.assertTrue(any(args[0]=='logi-sdk' for args in self.calls))
        self.assertFalse(any('set' in args for args in self.calls))

    def test_queued_button_write_keeps_submitted_profile_when_observation_changes(self):
        from threading import Event
        from copy import deepcopy
        gate=Event();started=Event()
        def hold():started.set();gate.wait(2)
        self.pool.submit(hold);self.assertTrue(started.wait(1))
        self.state['daemon_active']=0
        def run(args,**unused):
            self.calls.append(args)
            if args[0]=='logi-sdk':return json.dumps({'mode':'onboard','profile':1})
            return '1'
        self.editor.runner=run
        try:
            index=next(i for i,row in enumerate(self.editor.assignments) if row['value']==['button','2'])
            self.editor.chooseAssignment(index);self.editor.applyAssignment(index)
            changed=deepcopy(self.state['profiles'][0]);changed['index']=1
            self.state['profiles'].append(changed);self.state['active']=1;self.state['daemon_active']=1
        finally:gate.set()
        self.wait()
        self.assertFalse(any('set' in args for args in self.calls))

    def test_recorder_eats_item_key_events_and_mouse_events(self):
        from PySide6.QtCore import QObject,QEvent,Qt,QPointF
        from PySide6.QtGui import QKeyEvent,QMouseEvent
        capture=QObject();item=QObject();item.mapFromGlobal=lambda point:point;item.contains=lambda point:True
        child=QObject();child.window=lambda:capture
        self.editor.beginMacroCapture(capture,item)
        for kind in (QEvent.Type.KeyPress,QEvent.Type.KeyRelease):
            event=QKeyEvent(kind,Qt.Key.Key_Space,Qt.KeyboardModifier.NoModifier,' ')
            self.assertTrue(self.editor.eventFilter(child,event));self.assertTrue(event.isAccepted())
        for kind,buttons in ((QEvent.Type.MouseButtonPress,Qt.MouseButton.LeftButton),(QEvent.Type.MouseButtonRelease,Qt.MouseButton.NoButton)):
            event=QMouseEvent(kind,QPointF(10,10),QPointF(10,10),Qt.MouseButton.LeftButton,buttons,Qt.KeyboardModifier.NoModifier)
            self.assertTrue(self.editor.eventFilter(child,event))
        self.editor.stopRecording()
        tokens=[row['token'] for row in self.editor.macroEvents if not row['token'].startswith('t')]
        self.assertEqual(tokens,['+KEY_SPACE','-KEY_SPACE','+BTN_LEFT','-BTN_LEFT'])

    def test_profile_sync_needs_explicit_action_and_rechecks_device(self):
        self.state.update(daemon_active=1,profile_mismatch=True,live_profile={'mode':'onboard','profile':0,'profile_count':1})
        self.editor._build();self.assertEqual(self.calls,[])
        daemon=[1]
        def run(args,**unused):
            self.calls.append(args)
            if args[0]=='logi-sdk':return json.dumps(self.state['live_profile'])
            if 'set' in args:daemon[0]=int(args[-1]);return ''
            return str(daemon[0])
        self.editor.runner=run;self.editor.reader=lambda target:self.state
        self.editor.syncRatbagProfile();self.wait()
        self.assertEqual(daemon[0],0)
        self.assertEqual(len([args for args in self.calls if 'set' in args]),1)
        self.calls.clear();self.state['live_profile']['profile']=1
        self.editor.syncRatbagProfile();self.wait()
        self.assertFalse(any('set' in args for args in self.calls))
