"""K7 dock reports are tested with memory only, never an attached receiver."""
import json
import unittest
from unittest.mock import patch

from logi_center.core.discovery.identity import identity
from logi_center.core.services.execution import Fault,FaultCode
from logi_center.adapters.mchose.mchose_adapter import DOCK_EFFECTS,dock_values,prepare_dock_record,dock_setting_plan,hardware
from logi_center.core.services.operations import perform,State


ORIGINAL=bytes([1,1,0,100,0,3,1,0,0,255,0,0,255,0,0])
ITEM={'node':'fake','physical':'fake','vid':'3837','pid':'1001','name':'MCHOSE K7 Ultra'}


class DockTransport:
    def __init__(self):self.record=ORIGINAL;self.commands=[];self.ignore_write=False
    def __enter__(self):return self
    def __exit__(self,*unused):pass
    def read_identity(self):return {'vid':0x3837,'pid':0x4150}
    def read(self):raise AssertionError('A dock setting must not access the mouse configuration')
    def exchange(self,report,command,args=b'',reply=True):
        self.commands.append((report,command,bytes(args),reply))
        if (report,command)==(0x11,0x1b):return self.record
        if (report,command)==(0x11,0x2b):
            if not self.ignore_write:self.record=bytes(args)
            return None
        raise AssertionError('Unexpected hardware command')


class K7DockTests(unittest.TestCase):
    def call(self,device,action,field=None,value=None,item=None):
        with patch('logi_center.adapters.mchose.mchose_adapter.candidates',return_value=[item or ITEM]),patch('logi_center.adapters.mchose.mchose_adapter.time.sleep'),patch('logi_center.adapters.mchose.mchose_adapter.atomic_json'):
            return hardware(action,identity('fake'),field,value,transport=lambda node:device)

    def test_official_k7_modes_and_native_flags(self):
        self.assertEqual(DOCK_EFFECTS,{'battery':1,'breathing':2,'flash':3,'cycle':4,'stars':5,'static':6,'wave':7})
        for name,effect in DOCK_EFFECTS.items():
            record=prepare_dock_record(ORIGINAL,{'mode':name})
            self.assertEqual((record[0],record[1],record[2]),(1,effect,0))
            self.assertEqual(dock_values(record)['mode'],name)
        self.assertEqual(prepare_dock_record(ORIGINAL,{'mode':'off'})[0],0)

    def test_color_brightness_duration_direction_preserve_other_bytes(self):
        record=prepare_dock_record(ORIGINAL,{'color':[12,34,56]})
        self.assertEqual(record[8:14],bytes([12,34,56,12,34,56]))
        self.assertEqual(record[:8],ORIGINAL[:8]);self.assertEqual(record[14],ORIGINAL[14])
        self.assertEqual(prepare_dock_record(ORIGINAL,{'brightness':0})[0],0)
        record=prepare_dock_record(ORIGINAL,{'mode':'wave','direction':1,'duration':2,'brightness':75})
        self.assertEqual((record[1],record[3],record[6],record[14]),(7,75,2,1))
        self.assertEqual(record[5],ORIGINAL[5])

    def test_invalid_changes_never_form_a_setting_report(self):
        for changes in ({'mode':'music'},{'mode':[]},{'enabled':1},{'brightness':101},{'brightness':True},
                        {'duration':3},{'direction':2},{'color':[1.5,2,3]},{'unknown':1}):
            with self.subTest(changes=changes),self.assertRaises((ValueError,TypeError)):
                dock_setting_plan('fake',changes,ORIGINAL)

    def test_apply_is_one_native_rgb_report_and_keeps_mouse_state_untouched(self):
        device=DockTransport();changes={'mode':'static','color':[255,0,0],'brightness':80}
        payload={'changes':changes,'expected_record':list(ORIGINAL)}
        result=self.call(device,'set','dock_lighting',payload)
        writes=[c for c in device.commands if c[1]==0x2b]
        self.assertEqual(len(writes),1);self.assertFalse(writes[0][3])
        self.assertEqual(result['dock_lighting']['color'],[255,0,0])
        self.assertEqual(result['dock_lighting']['mode'],'static')
        self.assertEqual(result['dock_lighting']['brightness'],80)

    def test_stale_or_wrong_target_blocks_before_write(self):
        device=DockTransport();original=list(ORIGINAL);original[1]=4
        with self.assertRaisesRegex(Fault,'Dock lighting changed'):
            self.call(device,'set','dock_lighting',{'changes':{'mode':'static'},'expected_record':original})
        self.assertTrue(all(c[1]!=0x2b for c in device.commands))
        for item in ({**ITEM,'pid':'1012'},{**ITEM,'vid':'5253'}):
            with self.subTest(item=item),self.assertRaises(Fault):self.call(device,'dock',item=item)
        device.read_identity=lambda:{'vid':0x3837,'pid':0x9999}
        with self.assertRaises(Fault):self.call(device,'set','dock_lighting',
            {'changes':{'mode':'static'},'expected_record':list(ORIGINAL)})

    def test_dock_read_remains_available_when_paired_mouse_is_asleep(self):
        device=DockTransport()
        def no_mouse():raise AssertionError('Reading the receiver RGB record must not wake the mouse')
        device.read_identity=no_mouse
        self.assertEqual(self.call(device,'dock')['dock_lighting']['mode'],'battery')
        self.assertEqual([c[1] for c in device.commands],[0x1b])

    def test_record_readback_mismatch_is_not_confirmation_or_retry(self):
        device=DockTransport();device.ignore_write=True
        plan=dock_setting_plan(identity('fake'),{'mode':'static','color':[255,0,0]},ORIGINAL)
        def runner(args):
            return json.dumps(self.call(device,args[2],args[4] if len(args)>4 else None,
                                        json.loads(args[5]) if len(args)>5 else None))
        result=perform(plan,runner)
        self.assertEqual(result.state,State.MISMATCH)
        self.assertEqual(len([c for c in device.commands if c[1]==0x2b]),1)

    def test_record_readback_can_confirm_requested_fields_without_claiming_optics(self):
        device=DockTransport();plan=dock_setting_plan(identity('fake'),{'mode':'cycle'},ORIGINAL)
        def runner(args):
            return json.dumps(self.call(device,args[2],args[4] if len(args)>4 else None,
                                        json.loads(args[5]) if len(args)>5 else None))
        result=perform(plan,runner)
        self.assertEqual((result.state,result.actual,result.source),(State.CONFIRMED,{'mode':'cycle'},'device'))
        off=dock_setting_plan(identity('fake'),{'mode':'off'},device.record)
        self.assertEqual(perform(off,runner).state,State.CONFIRMED)
        self.assertFalse(dock_values(device.record)['enabled'])
        self.assertEqual(dock_values(device.record)['mode'],'cycle')


if __name__=='__main__':unittest.main()
