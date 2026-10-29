"""Ace68 QML bridge exercises the real planner with memory-only HID tables."""
import copy
import json
import unittest
from unittest.mock import patch
import tests.integration.test_qml_editor as common
from tests.unit.test_ace68 import ITEM
from tests.unit.test_ace68_advanced import AdvancedWire
from logi_center.adapters.mchose.ace68_adapter import Ace68Adapter,hardware,selector
from logi_center.protocols.ace68_protocol import MODES
from logi_center.core.devices.devices import DeviceManager
from logi_center.core.capabilities.model import Capability
from logi_center.core.services.execution import Fault


@unittest.skipUnless(common.QCoreApplication,'Optional PySide6 unavailable')
class AceEditorTests(unittest.TestCase):
    setUpClass=classmethod(common.EditorTests.setUpClass.__func__)
    wait=common.EditorTests.wait

    def setUp(self):
        common.EditorTests.setUp(self)
        self.wire=AdvancedWire();self.wire.tables[10]=bytearray(4*512)
        self.reads=[]
        self.patches=[patch('logi_center.adapters.mchose.ace68_adapter.candidates',return_value=[ITEM]),patch('logi_center.core.services.drafts.atomic_json')]
        for p in self.patches:p.start()
        def runner(args,**unused):
            self.reads.append(args)
            return json.dumps(hardware(args[2],selector(ITEM),args[4] if len(args)>4 else None,
                json.loads(args[5]) if len(args)>5 else None,transport=lambda node:self.wire))
        self.editor.runner=runner
        self.device=Ace68Adapter(runner=runner).discover()[0]
        self.manager=DeviceManager();self.manager.devices=[self.device]
        self.editor.bind(self.manager,self.device);self.wire.writes.clear();self.reads.clear()

    def tearDown(self):
        common.EditorTests.tearDown(self)
        for p in reversed(self.patches):p.stop()

    def test_multi_selection_drafts_batch_apply_and_no_unrelated_writes(self):
        self.editor.setSection('keys');self.editor.selectAceKeys('wasd')
        self.assertEqual(len(self.editor.aceSelectedKeys),4)
        self.editor.editAceKeys('actuation',.31)
        self.assertEqual(self.editor.dirtyCount,4);self.assertEqual(self.wire.writes,[])
        self.editor.applyGroup();self.wait()
        self.assertEqual(self.editor.resultState,'confirmed',self.editor.message)
        self.assertEqual(len(self.wire.writes),4)
        self.assertTrue(all(w[0]==161 for w in self.wire.writes))
        self.assertEqual(self.editor.dirtyCount,0)
        self.assertEqual(len([r for r in self.reads if r[2]=='set']),1)

    def test_layer_edit_is_profile_scoped_and_read_only_until_apply(self):
        self.editor.setSection('key_assignments');self.wait();self.editor.selectKey('50')
        self.editor.setAceLayer(2);self.editor.editAceBinding([16,1,6])
        self.assertEqual(self.wire.writes,[]);self.assertEqual(self.editor.dirtyCount,1)
        self.editor.setAceLayer(0);self.assertEqual(self.editor.aceBindingSelection['label'],'A')
        self.editor.applyGroup();self.wait()
        self.assertEqual(self.wire.tables[8][1024+150:1024+153],bytes([16,1,6]))
        self.assertEqual(self.wire.tables[8][150:153],bytes([255])*3)
        self.assertEqual(self.editor.resultState,'confirmed',self.editor.message)

    def test_last_fn_guard_stops_before_snapshot_or_write(self):
        self.editor.setSection('key_assignments');self.wait();self.editor.selectKey('7')
        self.editor.editAceBinding([16,0,4]);self.editor.applyGroup();self.wait()
        self.assertEqual(self.wire.writes,[]);self.assertEqual(self.editor.dirtyCount,1)

    def test_advanced_create_draft_cancel_apply_remove(self):
        self.editor.setSection('advanced_keys');self.wait();context=self.editor.aceContext
        spec={'kind':'mt','layer':0,'keys':[50],'actions':[[16,0,4],[16,1,0]],'time':200}
        self.editor.stageAceAdvanced(spec,context)
        self.assertEqual(self.editor.dirtyCount,1);self.assertEqual(self.wire.writes,[])
        self.editor.discardGroup();self.assertEqual(self.editor.dirtyCount,0)
        self.editor.stageAceAdvanced(spec,context);self.editor.applyGroup();self.wait()
        self.assertEqual(self.editor.resultState,'confirmed',self.editor.message)
        self.assertEqual(self.editor.dirtyCount,0)
        self.assertEqual(self.editor.aceAdvancedBindings[0]['spec'],spec)
        self.editor.removeAceAdvanced('0:50',context)
        self.assertEqual(self.editor.dirtyCount,1)
        self.editor.applyGroup();self.wait();self.assertEqual(self.editor.dirtyCount,0)

    def test_form_context_cannot_retarget_after_profile_switch(self):
        self.editor.setSection('advanced_keys');self.wait();context=self.editor.aceContext
        self.wire.tables[4][0]=1
        self.editor.reload();self.wait()
        self.editor.stageAceAdvanced({'kind':'tgl','layer':0,'keys':[50],'actions':[[16,0,4]]},context)
        self.assertEqual(self.editor.dirtyCount,0);self.assertEqual(self.wire.writes,[])

    def test_per_key_color_apply_preserves_unselected_and_unknown_bank_bytes(self):
        self.wire.tables[5][8]=0;self.wire.tables[10][383]=123
        self.editor.setSection('lighting');self.editor.readAceColors();self.wait()
        self.editor.selectAceKeys('wasd');self.editor.editAceColor([12,34,56])
        self.assertEqual(self.editor.dirtyCount,4);self.assertEqual(self.wire.writes,[])
        self.editor.applyGroup();self.wait()
        self.assertEqual(self.editor.resultState,'confirmed',self.editor.message)
        self.assertEqual(self.editor.dirtyCount,0)
        self.assertEqual(self.wire.tables[10][383],123)
        self.assertEqual(len(self.wire.writes),4)

    def test_lighting_controls_are_effect_specific_and_hidden_drafts_preserved(self):
        self.editor.setSection('lighting');self.editor.edit('mchose-ace68:lighting_speed',3)
        self.editor.edit('mchose-ace68:lighting_mode','Static')
        self.assertFalse(self.editor.aceLightOptions['speed'])
        self.editor.applyGroup();self.wait()
        self.assertEqual([w[1] for w in self.wire.writes],[8])
        self.assertEqual(self.editor._desired(self.editor._field('mchose-ace68:lighting_speed'))[0],3)

    def test_mac_mode_draft_disables_win_lock_without_hardware_write(self):
        self.editor.setSection('performance')
        self.editor.edit('mchose-ace68:win_lock',True)
        self.editor.edit('mchose-ace68:keyboard_mode','Mac')
        self.assertFalse(self.editor._desired(self.editor._field('mchose-ace68:win_lock'))[0])
        self.editor.edit('mchose-ace68:win_lock',True)
        self.assertFalse(self.editor._desired(self.editor._field('mchose-ace68:win_lock'))[0])
        self.assertEqual(self.wire.writes,[])

    def test_profile_scopes_lighting_and_performance_drafts_and_preserves_legacy(self):
        self.editor.setSection('lighting');self.editor.edit('mchose-ace68:brightness',66)
        old=self.editor._field('mchose-ace68:brightness').draft_key
        self.assertTrue(old.endswith(':profile:0'))
        self.wire.tables[4][0]=1;self.editor.reload();self.wait()
        field=self.editor._field('mchose-ace68:brightness')
        self.assertTrue(field.draft_key.endswith(':profile:1'))
        self.assertEqual(self.editor._desired(field)[0],75)
        self.wire.tables[4][0]=0;self.editor.reload();self.wait()
        self.assertEqual(self.editor._desired(self.editor._field('mchose-ace68:brightness'))[0],66)
        self.assertEqual(self.wire.writes,[])

    def test_bank_refresh_cannot_bypass_openrgb_ownership(self):
        self.wire.tables[5][8]=0
        self.device.capabilities.append(Capability('lighting','openrgb',True,True,True,True,[1,2,3],'backend_cache'))
        self.editor.setSection('lighting');self.editor.readAceColors();self.wait()
        self.assertFalse(self.editor.aceColorSelection['writable'])
        self.assertTrue(all(not f.writable for f in self.editor._controls if f.backend=='mchose-ace68' and f.group=='lighting'))
        for field in ('key_lighting','lighting_direction','lighting'):
            with self.assertRaises(Fault):self.editor._guard_ace_rgb(['logi-sdk','mchose-ace68','set','target','profile/0/'+field,'{}'],self.device)
        self.editor.editAceColor([1,2,3]);self.editor.applyGroup();self.wait()
        self.assertEqual(self.wire.writes,[])
