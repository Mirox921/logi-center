"""Ace68 native layers and RGB/performance writes, with memory-only transports."""
import json
import unittest
from unittest.mock import patch
from ace68_adapter import hardware,selector,binding_capability
from ace68_bindings import read,prepare,actions,validate_action
from ace68_protocol import KEY_INDICES,MODES,state
from test_ace68 import MemoryWire,ITEM
from execution import Fault
from operations import perform,State


class BindingWire(MemoryWire):
    def __init__(self):
        super().__init__()
        self.tables[7]=bytearray(16*512);self.tables[8]=bytearray([255])*(16*512)
        for bank in range(16):
            for key in KEY_INDICES:self.tables[7][bank*512+key*3:bank*512+key*3+3]=bytes([16,0,4])
            self.tables[7][bank*512+7*3:bank*512+7*3+3]=bytes([240,255,1 if bank%4<2 else 3])
    def request(self,command,offset,size,data=None):
        if command==9:
            self.writes.append((command,offset,data));self.tables[8][offset:offset+size]=bytes(data);return b''
        return super().request(command,offset,size,data)


class Ace68NativeBindings(unittest.TestCase):
    def test_action_codes_match_official_named_catalog_not_effect_indices(self):
        catalog={a['label']:a['value'] for a in actions()}
        for name,code in [('Следующий эффект',47),('Предыдущий эффект',46),('Ярче',50),('Темнее',51),
                          ('Выключить подсветку',53),('Ускорить эффект',54),('Замедлить эффект',55),('Следующий цвет',61)]:
            self.assertEqual(catalog[name],[240,code,0])
        self.assertEqual(catalog['Остановить воспроизведение'],[48,183,0])
        for unsupported in ([240,48,0],[240,60,0]):
            with self.assertRaises(ValueError):validate_action(unsupported)

    def setUp(self):
        self.wire=BindingWire();self.patches=[patch('ace68_adapter.candidates',return_value=[ITEM]),patch('drafts.atomic_json')]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
    def call(self,action,field=None,value=None):return hardware(action,selector(ITEM),field,value,transport=lambda node:self.wire)
    def write(self,changes):
        observed=self.call('bindings')
        return self.call('set','profile/0/key_remap',{'changes':changes,'expected_bindings':observed['raw_bindings']})

    def test_layer_reads_resolve_native_default_and_never_write(self):
        observed=self.call('bindings')
        self.assertEqual(observed['key_remap']['0:50'],[16,0,4])
        self.assertEqual(observed['key_remap']['2:7'],[240,255,3])
        self.assertEqual(len(observed['key_remap']),272);self.assertEqual(self.wire.writes,[])

    def test_partial_layer_write_preserves_other_layers_keys_and_config(self):
        before={key:bytes(data) for key,data in self.wire.tables.items()}
        actual=self.write({'1:50':[16,1,6],'3:30':[48,233,0]})
        self.assertEqual(self.wire.writes,[(9,512+50*3,[16,1,6]),(9,3*512+30*3,[48,233,0])])
        self.assertEqual(actual['key_remap']['1:50'],[16,1,6]);self.assertEqual(actual['key_remap']['3:30'],[48,233,0])
        for key in (3,4,5,7,160):self.assertEqual(bytes(self.wire.tables[key]),before[key])

    def test_fn_key_is_preserved_and_replacement_is_installed_first(self):
        observed=self.call('bindings')
        with self.assertRaisesRegex(ValueError,'Fn key'):prepare(0,observed,{'0:7':[16,0,4]})
        commands=prepare(0,observed,{'0:7':[16,0,4],'0:50':[240,255,1]})
        self.assertEqual([c[1] for c in commands],[150,21])

    def test_invalid_binding_and_reset_boot_codes_are_blocked(self):
        for bad in ([240,7,0],[240,8,0],[144,0,0],[16,0,255],[16,0,4.5],[16,True,4]):
            with self.subTest(bad=bad),self.assertRaises(ValueError):validate_action(bad)
        observed=self.call('bindings')
        with self.assertRaises(ValueError):prepare(0,observed,{'0:127':[16,0,4]})
        self.assertEqual(self.wire.writes,[])

    def test_stale_bindings_and_profiles_block_before_write(self):
        observed=self.call('bindings');self.wire.tables[8][150:153]=bytes([16,0,5])
        with self.assertRaisesRegex(Fault,'Bindings changed'):
            self.call('set','profile/0/key_remap',{'changes':{'0:50':[16,0,6]},'expected_bindings':observed['raw_bindings']})
        self.assertEqual(self.wire.writes,[])
        self.wire.tables[4][0]=1
        with self.assertRaises(Fault):self.call('set','profile/0/key_remap',{'changes':{'0:50':[16,0,6]},'expected_bindings':observed['raw_bindings']})

    def test_profile_change_between_keys_stops_remaining_writes(self):
        original=self.wire.request
        def switch(*args,**kwargs):
            result=original(*args,**kwargs);self.wire.tables[4][0]=1;return result
        self.wire.request=switch
        with self.assertRaisesRegex(Fault,'Profile changed'):self.write({'0:50':[16,0,5],'0:30':[16,0,6]})
        self.assertEqual(len(self.wire.writes),1)

    def test_binding_plan_confirms_only_native_readback(self):
        cap=binding_capability(selector(ITEM),self.call('bindings'))
        def runner(args):return json.dumps(self.call(args[2],args[4] if len(args)>4 else None,json.loads(args[5]) if len(args)>5 else None))
        result=perform(cap.plan({'0:50':[16,1,6]}),runner)
        self.assertEqual((result.state,result.actual),(State.CONFIRMED,{'0:50':[16,1,6]}))

    def test_all_verified_normal_effect_codes_are_available_and_independent(self):
        self.assertEqual(set(MODES),set(range(23))|{255})
        original=bytes(self.wire.tables[5])
        for mode in MODES.values():
            self.call('set','profile/0/lighting_mode',mode)
            actual=bytes(self.wire.tables[5]);self.assertEqual(actual[:8],original[:8]);self.assertEqual(actual[9:],original[9:])

    def test_performance_toggles_preserve_unknown_and_calibration_bits(self):
        self.wire.tables[5][6]=0xe6;self.wire.tables[5][7]=0x9d
        original=bytes(self.wire.tables[5])
        self.call('set','profile/0/win_lock',True)
        self.assertEqual(self.wire.tables[5][6],0xe7)
        self.call('set','profile/0/stability_mode',True)
        self.assertEqual(self.wire.tables[5][7],0x9f)
        with self.assertRaises(ValueError):self.call('set','profile/0/key_debounce',False)
        self.assertEqual(self.wire.tables[5][7],0x9f)
        self.wire.tables[5][7]=0x1d
        self.call('set','profile/0/key_debounce',True);self.assertEqual(self.wire.tables[5][7],0xfd)
        self.call('set','profile/0/key_debounce',False);self.assertEqual(self.wire.tables[5][7],0x1d)
        self.assertEqual(self.wire.tables[5][8:],original[8:])

    def test_mac_mode_uses_native_layer_and_only_clears_win_lock(self):
        self.wire.tables[5][1]=0xa0;self.wire.tables[5][6]=0xe7
        self.call('set','profile/0/keyboard_mode','Mac')
        self.assertEqual((self.wire.tables[5][1],self.wire.tables[5][6]),(0xa2,0xe6))
        self.assertEqual(self.call('read')['keyboard_mode'],'Mac')
        with self.assertRaises(ValueError):self.call('set','profile/0/win_lock',True)
