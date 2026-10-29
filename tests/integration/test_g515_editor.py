"""G515 QML service tests. No physical hardware or installed Solaar imports."""
import tempfile,time,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock,patch
from logi_center.adapters.logitech.g515_layout import keys,saved_colors,group_ids
from logi_center.core.services.control_service import g515_controls,g515_lighting_plans
from logi_center.core.devices.devices import Device,DeviceManager
from logi_center.core.services.drafts import DraftStore
try:
    from PySide6.QtCore import QObject,QCoreApplication
    from logi_center.qml_ui.bridge.editor import EditorController
except ImportError:QCoreApplication=None


def fixture():
    return {'rgb_zone_1':{'ID':'1','color':'0xffffff','period':'3000','intensity':'100'},
            'per-key-lighting':{k['id']:'0xffffff' for k in keys()}}


class G515Data(unittest.TestCase):
    def test_layout_has_unique_native_led_ids_not_ordinal_keycodes(self):
        rows=keys();self.assertEqual(len(rows),87);self.assertEqual(len({r['id'] for r in rows}),87)
        mapping={r['label']:int(r['id']) for r in rows}
        self.assertEqual([mapping[x] for x in ['A','W','\\','Pause','Fn']],[1,23,46,69,111])
        self.assertEqual(group_ids('wasd'),{'23','1','19','4'})
        self.assertEqual(len(group_ids('all')),87)
        self.assertFalse(group_ids('unknown'))

    def test_unknown_sentinel_and_corrupt_colors_never_become_writable(self):
        self.assertEqual(saved_colors({'per-key-lighting':{'1':'0x123456','2':'-1','254':'123','3':True,'4':'garbage','5':'16777216'}}),{'1':[18,52,86]})
        self.assertFalse(saved_colors({}))
        controls=g515_controls([],fixture(),'one')
        self.assertEqual(len([f for f in controls if f.group=='freestyle']),87)
        key=next(f for f in controls if f.id=='g515:key:1')
        self.assertEqual(key.plans([18,52,86])[0].command,['solaar','config','G515','per-key-lighting','1','1193046'])
        self.assertIn('keyboard:one/',key.draft_key)
        self.assertEqual(key.source,'local_saved_settings')
        self.assertIsNone(key.plans([0,0,0])[0].reader)

    def test_native_effect_parameters_and_no_animation_fields_for_static(self):
        cycle=g515_lighting_plans(21,[1,2,3],8000,60)[1].command[-1]
        self.assertIn('ID: 21',cycle);self.assertIn('period: 8000',cycle);self.assertIn('intensity: 60',cycle)
        self.assertNotIn('color:',cycle)
        static=g515_lighting_plans(1,[1,2,3])[1].command[-1]
        self.assertIn('color: 0x010203',static);self.assertNotIn('period',static)
        self.assertEqual(g515_lighting_plans(0,[0,0,0])[1].command[-1],'!LEDEffectSetting {ID: 0}')
        for args in [(22,[0,0,0],3000,100),(21,[0,0,0],0,100),(10,[0,0,0],20001,100),(10,[0,0,0],3000,101)]:
            with self.assertRaises(ValueError):g515_lighting_plans(*args)

    def test_static_or_off_cache_does_not_remove_animation_controls(self):
        for effect in (0,1):
            fields=g515_controls([],{'rgb_zone_1':{'ID':str(effect),'color':'0xffffff'}})
            timing=[f for f in fields if f.id.startswith(('g515:period:','g515:intensity:'))]
            self.assertEqual(len(timing),4)
            self.assertTrue(all(f.source=='unavailable' and f.note for f in timing))
            self.assertEqual(next(f.observed for f in timing if f.id=='g515:period:21'),3000)


@unittest.skipIf(QCoreApplication is None,'PySide6 unavailable')
class G515Editor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QCoreApplication.instance() or QCoreApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.owner=QObject();self.owner.tr=lambda t:t
        self.owner._preferences_pool=ThreadPoolExecutor(max_workers=1);self.pool=ThreadPoolExecutor(max_workers=1)
        self.owner._keyboard_online=True;self.owner.refresh=Mock();self.calls=[]
        self.device=Device('g515-one','Logitech G515 LIGHTSPEED TKL','keyboard','solaar','G515',physical='/test/g515')
        self.manager=DeviceManager();self.manager.devices=[self.device]
        self.editor=EditorController(self.owner,self.pool,store=DraftStore(Path(self.temp.name)/'logi_center.core.services.drafts.json'),runner=self.run_fake)
        self.editor.keyboard_reader=lambda:dict(settings=[],saved=fixture(),sources={},target='G515',reachable=True,errors=[])
        with patch('logi_center.adapters.external.backend.saved_keyboard',return_value=fixture()),patch('logi_center.adapters.external.backend.keyboard_saved_settings',return_value=[]):
            self.editor.bind(self.manager,self.device);self.wait()
    def run_fake(self,args,**kwargs):self.calls.append(args);return ''
    def wait(self):
        deadline=time.monotonic()+3
        while self.editor.busy and time.monotonic()<deadline:self.app.processEvents();time.sleep(.005)
        self.app.processEvents();self.assertFalse(self.editor.busy)
    def tearDown(self):
        self.editor.shutdown();self.pool.shutdown(wait=True);self.owner._preferences_pool.shutdown(wait=True);self.temp.cleanup()
    def paint(self):
        self.editor.setSection('freestyle');self.editor.selectG515Group('wasd');self.editor.paintG515([10,20,30])
    def test_selection_drafts_cancel_and_unverified_apply(self):
        self.paint();self.assertEqual(self.calls,[]);self.assertEqual(self.editor.dirtyCount,4)
        self.editor.setSection('assignments');self.editor.setSection('freestyle');self.assertEqual(self.editor.dirtyCount,4)
        self.editor.discardGroup();self.assertEqual(self.editor.dirtyCount,0)
        self.paint();self.editor.applyGroup();self.wait()
        self.assertEqual(len(self.calls),6);self.assertEqual(self.calls[0],['solaar','config','G515','rgb_control','true'])
        self.assertIn('ID: 1',self.calls[1][-1])
        self.assertEqual({c[-2] for c in self.calls[2:]},group_ids('wasd'))
        self.assertTrue(all(c[-1]=='660510' for c in self.calls[2:]))
        self.assertEqual(self.editor.resultState,'sent_unverified');self.assertEqual(self.editor.dirtyCount,4)
    def test_effect_drafts_and_period_are_applied_together(self):
        self.editor.setSection('lighting');self.editor.edit('g515:effect',21);self.editor.edit('g515:period:21',8000)
        self.editor.edit('g515:intensity:21',55)
        self.editor.edit('g515:effect',10);self.editor.edit('g515:period:10',4000)
        self.editor.edit('g515:effect',21)
        self.assertEqual(self.editor.g515Fields['g515:period:21']['value'],8000)
        self.assertNotIn('g515:period:10',self.editor.g515Fields)
        self.editor.applyGroup();self.wait();self.assertEqual(len(self.calls),2)
        self.assertIn('period: 8000',self.calls[-1][-1]);self.assertIn('intensity: 55',self.calls[-1][-1])
    def test_no_writes_to_ambiguous_alias_or_after_disconnect(self):
        self.paint()
        self.manager.devices.append(Device('g515-two','G515','keyboard','solaar','G515',physical='/test/two'))
        self.editor.applyGroup();self.wait();self.assertEqual(self.calls,[])
        self.manager.devices.pop();self.device.connected=False
        self.editor.applyGroup();self.assertEqual(self.calls,[]);self.assertEqual(self.editor.dirtyCount,4)
    def test_disconnect_between_prelude_and_colors_stops_remaining_writes(self):
        self.paint()
        def disconnect(args,**kwargs):
            self.calls.append(args)
            if len(self.calls)==2:self.device.connected=False
            return ''
        self.editor.runner=disconnect;self.editor.applyGroup();self.wait()
        self.assertEqual(len(self.calls),2);self.assertEqual(self.editor.dirtyCount,4)
    def test_failed_key_does_not_drop_remaining_drafts(self):
        self.paint()
        def fail(args,**kwargs):
            self.calls.append(args)
            if 'per-key-lighting' in args:raise RuntimeError('fixture failure')
            return ''
        self.editor.runner=fail;self.editor.applyGroup();self.wait()
        self.assertEqual(len(self.calls),3);self.assertEqual(self.editor.dirtyCount,4)
        self.assertNotEqual(self.editor.resultState,'confirmed')
    def test_selection_is_device_scoped_and_reload_never_writes(self):
        structural=[]
        self.editor.g515KeyModel.modelReset.connect(lambda:structural.append('reset'))
        self.editor.g515KeyModel.rowsRemoved.connect(lambda *args:structural.append('removed'))
        self.paint();self.editor.selectG515Key('1',False)
        with patch('logi_center.adapters.external.backend.saved_keyboard',return_value=fixture()),patch('logi_center.adapters.external.backend.keyboard_saved_settings',return_value=[]):
            self.editor.reload();self.wait()
        self.assertEqual(self.editor.g515SelectionCount,1);self.assertEqual(self.editor.dirtyCount,4)
        self.assertEqual(self.calls,[])
        self.assertEqual(structural,[])

    def test_false_sysfs_probe_does_not_hide_a_solaar_keyboard(self):
        self.owner._keyboard_online=False
        self.editor.bind(self.manager,self.device,reload=True);self.wait()
        self.assertIn('g515:effect',[f.id for f in self.editor._g515])
        self.assertEqual(len(self.editor.g515Keys),87)
        self.assertEqual(self.calls,[])


if __name__=='__main__':unittest.main()
