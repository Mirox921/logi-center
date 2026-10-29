"""Native advanced-key transactions on an in-memory keyboard, never real HID."""
import json
import unittest
from unittest.mock import patch
from ace68_adapter import hardware, selector, advanced_capability
from ace68_advanced import BANKS, prepare, _phase_encode, _phase_decode
from test_ace68_bindings import BindingWire
from test_ace68 import ITEM
from operations import perform, State
from execution import Fault


class AdvancedWire(BindingWire):
    def __init__(self):
        super().__init__()
        for read,write,area,size in BANKS.values():self.tables[read]=bytearray(area*4)
        self.tables[10]=bytearray(4*512)

    def request(self,command,offset,size,data=None):
        if command==11:
            self.writes.append((command,offset,data));self.tables[10][offset:offset+size]=bytes(data);return b''
        if command in (163,165,167):
            read=next(spec[0] for spec in BANKS.values() if spec[1]==command)
            self.writes.append((command,offset,data));self.tables[read][offset:offset+size]=bytes(data)
            return b''
        return super().request(command,offset,size,data)


class AdvancedTests(unittest.TestCase):
    def setUp(self):
        self.wire=AdvancedWire()
        self.patches=[patch('ace68_adapter.candidates',return_value=[ITEM]),patch('drafts.atomic_json')]
        for p in self.patches:p.start()

    def tearDown(self):
        for p in reversed(self.patches):p.stop()

    def call(self,action,field=None,value=None):
        return hardware(action,selector(ITEM),field,value,transport=lambda node:self.wire)

    def apply(self,change):
        observed=self.call('advanced')
        cap=advanced_capability(selector(ITEM),observed)
        def runner(args):
            return json.dumps(self.call(args[2],args[4] if len(args)>4 else None,json.loads(args[5]) if len(args)>5 else None))
        return perform(cap.plan(change),runner)

    def spec(self,kind):
        result={'kind':kind,'layer':0,'keys':[50], 'actions':[[16,0,4]]}
        if kind in ('rs','socd'):result.update(keys=[30,50],actions=[[16,0,4],[16,0,7]])
        if kind=='socd':result['priority']=1
        if kind=='mt':result.update(actions=[[16,0,4],[16,1,0]],time=200)
        if kind=='dks':result.update(actions=[[16,0,4]]*4,points=[10,30,30,10],phases=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])
        return result

    def test_reads_never_write(self):
        self.assertEqual(self.call('advanced')['advanced_keys'],{})
        self.assertEqual(self.wire.writes,[])

    def test_all_native_types_round_trip_and_remove_without_collateral(self):
        for kind in ('tgl','mt','rs','socd','dks'):
            with self.subTest(kind=kind):
                self.wire=AdvancedWire();before={k:bytes(v) for k,v in self.wire.tables.items()}
                spec=self.spec(kind);key='0:'+str(min(spec['keys']))
                result=self.apply({key:spec})
                self.assertEqual(result.state,State.CONFIRMED,result)
                self.assertEqual(result.actual[key],spec)
                first_reference=next(i for i,w in enumerate(self.wire.writes) if w[0]==9)
                self.assertTrue(all(w[0] in (163,165,167,161) for w in self.wire.writes[:first_reference]))
                for bank in (3,4,5,7):self.assertEqual(bytes(self.wire.tables[bank]),before[bank])
                if kind!='socd':self.assertEqual(bytes(self.wire.tables[160]),before[160])
                else:
                    for offset,(old,new) in enumerate(zip(before[160],self.wire.tables[160])):
                        if old!=new:self.assertIn(offset,(30*8+1,50*8+1));self.assertEqual(old&15,new&15)
                self.assertEqual(self.apply({key:None}).state,State.CONFIRMED)
                self.assertEqual(self.call('advanced')['advanced_keys'],{})
                for name,specification in BANKS.items():self.assertFalse(any(self.wire.tables[specification[0]]))

    def test_unknown_records_and_padding_are_never_allocated_or_overwritten(self):
        self.wire.tables[164][:6]=bytes([1,2,3,4,5,6]);self.wire.tables[164][250]=123
        self.apply({'0:50':self.spec('mt')})
        self.assertEqual(list(self.wire.tables[164][:6]),[1,2,3,4,5,6])
        self.assertEqual(self.wire.tables[164][250],123)
        self.assertEqual(self.call('advanced')['raw_bindings'][0][150:153],[146,1,20])

    def test_full_bank_is_a_safe_failure(self):
        self.wire.tables[164][:192]=bytes([1])*192
        with self.assertRaisesRegex(ValueError,'unused zero'):prepare(self.call('advanced'),{'0:50':self.spec('mt')})
        self.assertEqual(self.wire.writes,[])

    def test_stale_context_and_profile_block_before_any_write(self):
        cap=advanced_capability(selector(ITEM),self.call('advanced'))
        plan=cap.plan({'0:50':self.spec('tgl')});payload=json.loads(plan.command[5])
        self.wire.tables[5][9]^=1
        with self.assertRaises(Fault):self.call('set',plan.command[4],payload)
        self.wire.tables[4][0]=1
        with self.assertRaises(Fault):self.call('set',plan.command[4],payload)
        self.assertEqual(self.wire.writes,[])

    def test_invalid_parameters_and_fn_replacement_are_rejected(self):
        observed=self.call('advanced')
        for kind in ('tgl','mt','rs','socd','dks'):
            spec=self.spec(kind);spec['keys'][0]=7;identifier='0:'+str(min(spec['keys']))
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'Fn'):prepare(observed,{identifier:spec})
        for time in (-10,15,1010):
            spec=self.spec('mt');spec['time']=time
            with self.assertRaises(ValueError):prepare(observed,{'0:50':spec})
        spec=self.spec('dks');spec['points']=[1,2,3,4]
        with self.assertRaises(ValueError):prepare(observed,{'0:50':spec})
        self.assertEqual(self.wire.writes,[])

    def test_dks_phase_codec_matches_official_thermometer_bits(self):
        for phase,word in [([1,0,0,0],1),([2,0,0,0],3),([3,0,0,0],31),([4,0,0,0],255),([0,0,0,1],512)]:
            self.assertEqual(_phase_encode(phase),word);self.assertEqual(_phase_decode(word),phase)

    def test_disconnect_after_data_does_not_install_key_reference(self):
        request=self.wire.request
        def interrupted(*args,**kwargs):
            response=request(*args,**kwargs);self.wire.disconnected=True;return response
        self.wire.request=interrupted
        result=self.apply({'0:50':self.spec('tgl')})
        self.assertFalse(result.accepted);self.assertEqual([w[0] for w in self.wire.writes],[167])

    def test_socd_priority_cannot_change_other_layer_or_unknown_bits(self):
        spec=self.spec('socd');self.assertEqual(self.apply({'0:30':spec}).state,State.CONFIRMED)
        writes=len(self.wire.writes)
        second=self.spec('socd');second.update(layer=1,priority=3)
        with self.assertRaisesRegex(ValueError,'shared with another layer'):
            prepare(self.call('advanced'),{'1:30':second})
        self.assertEqual(len(self.wire.writes),writes)
        self.wire.tables[160][30*8+1]|=128
        with self.assertRaisesRegex(ValueError,'Unknown native priority'):
            prepare(self.call('advanced'),{'0:30':spec})
