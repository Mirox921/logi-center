"""Exact-model settings use native commands; all I/O here is memory only."""
import json
import struct
import unittest
from unittest.mock import patch

from devices import identity
from execution import Fault
from k7_settings import actions,prepare,values,unchanged,action_label
from mchose_adapter import decode,hardware,k7_setting_plan,k7_capabilities
from operations import perform,State


ITEM={'node':'fake','physical':'fake','vid':'3837','pid':'1001','name':'MCHOSE K7 Ultra'}


def raw_config():
    raw=bytearray(63);raw[0]=1;raw[1]=raw[2]=0x30
    raw[4:16]=struct.pack('<6H',400,800,1600,3200,6400,42000)
    raw[16]=6;raw[17]=0xa1;raw[18]=4;raw[19]=3
    for i in range(6):raw[20+4*i]=i<<4
    raw[44:49]=bytes([123,45,67,89,101])
    raw[50]=1;raw[51:63]=raw[4:16]
    return raw


class NativeTransport:
    def __init__(self):
        self.raw=raw_config();self.commands=[];self.ignore=False;self.collateral=False;self.ident={'vid':0x3837,'pid':0x4150,'mode':1,'battery':38,'charging':False}
    def __enter__(self):return self
    def __exit__(self,*unused):pass
    def read(self):return decode(bytes(self.raw),self.ident)
    def exchange(self,report,command,args=b'',reply=True):
        self.commands.append((report,command,bytes(args),reply))
        if self.ignore:return
        r=self.raw
        if (report,command)==(0x12,0x40):
            r[1]=(r[1]&240)|args[0];r[2]=(r[2]&240)|args[1]
            r[4:16]=args[3:15];r[16]=args[15];r[51:63]=args[17:29]
        elif (report,command)==(0x12,0x52):
            i=args[0];r[20+4*i]=(i<<4)|args[2];r[21+4*i:24+4*i]=args[3:6]
        elif (report,command)==(0x11,0x42):
            r[17]=(r[17]&252)|args[0]
            for position,mask in ((1,4),(2,8),(3,16)):
                if args[position]:r[17]=(r[17]&~mask)|(mask if args[position]==1 else 0)
            if args[6]:r[17]=(r[17]&63)|{1:0,2:128,3:192}[args[6]]
            if args[7]:r[49]=args[8]
        elif (report,command)==(0x11,0x43):r[18]=args[0]
        elif (report,command)==(0x11,0x0a):r[19]=args[1]
        else:raise AssertionError('Unapproved command in fake K7 transport')
        if self.collateral:r[44]^=1


class K7NativeSettings(unittest.TestCase):
    def call(self,device,field,payload):
        with patch('mchose_adapter.candidates',return_value=[ITEM]),patch('mchose_adapter.atomic_json') as snapshot,patch('mchose_adapter.time.sleep'):
            result=hardware('set',identity('fake'),field,payload,transport=lambda node:device)
            self.assertEqual(snapshot.call_count,1)
            return result

    def execute(self,device,field,changes):
        return self.call(device,field,{'changes':changes,'expected_raw':list(device.raw),'expected_mode':device.ident['mode']})

    def test_decode_all_stages_axes_buttons_and_sensor(self):
        state=NativeTransport().read()
        self.assertEqual(state['dpi_config']['x5'],42000)
        self.assertEqual(state['dpi_config']['y0'],400)
        self.assertEqual(state['sensor_config']['performance_mode'],1)
        self.assertEqual(state['sensor_config']['lod'],1)
        self.assertEqual(state['button_bindings']['4'],[0,0])
        state['identity']={**state['identity'],'pid':0x1234}
        self.assertEqual(k7_capabilities('fake',state),[])

    def test_dpi_packet_and_profile_button_rate_preservation(self):
        device=NativeTransport();before=bytes(device.raw)
        state=self.execute(device,'dpi_config',{'x1':850,'y1':900,'count':5,'active':1})
        self.assertEqual((state['dpi'],state['stage'],state['dpi_config']['y1']),(850,1,900))
        report,command,args,reply=device.commands[0]
        self.assertEqual((report,command,reply),(0x12,0x40,False));self.assertEqual(len(args),29)
        self.assertEqual(args[:3],bytes([1,1,0]));self.assertEqual(args[15:17],bytes([5,255]))
        self.assertEqual(device.raw[20:50],before[20:50]);self.assertEqual(device.raw[17:20],before[17:20])
        self.assertEqual(device.raw[0],before[0]);self.assertEqual(device.raw[1]&240,before[1]&240)

    def test_sensor_off_is_two_not_zero_and_unknown_bits_survive(self):
        device=NativeTransport();before=bytes(device.raw)
        self.execute(device,'sensor_config',{'motion_sync':True,'ripple':False,'angle_snap':True,'rotation':-3})
        self.assertEqual(device.commands[0][:3],(0x11,0x42,bytes([1,2,1,1,0,0,0,1,253])))
        self.assertTrue(device.raw[17]&32);self.assertEqual(device.raw[17]&192,before[17]&192)
        self.assertEqual(device.raw[20:44],before[20:44]);self.assertEqual(device.raw[49],253)
        self.execute(device,'sensor_config',{'motion_sync':False})
        self.assertFalse(device.read()['sensor_config']['motion_sync'])

    def test_lod_and_mode_are_independent_of_filters(self):
        device=NativeTransport();old=device.raw[17]
        state=self.execute(device,'sensor_config',{'lod':2,'performance_mode':2})
        self.assertEqual(state['sensor_config']['lod'],2)
        self.assertEqual(state['sensor_config']['performance_mode'],2)
        self.assertEqual(device.raw[17]&60,old&60)

    def test_button_mapping_is_physical_and_preserves_underside(self):
        device=NativeTransport();before=bytes(device.raw)
        result=self.execute(device,'button_bindings',{'3':[1,0x080000],'4':[2,0x010600]})
        self.assertEqual([c[2] for c in device.commands],[bytes([3,0,1,8,0,0]),bytes([4,0,2,1,6,0])])
        self.assertEqual(result['button_bindings']['4'],[2,0x010600])
        self.assertEqual(device.raw[40:44],before[40:44]);self.assertEqual(device.raw[:20],before[:20])

    def test_left_click_guard_and_safe_reassignment_order(self):
        raw=raw_config()
        with self.assertRaisesRegex(ValueError,'left-click'):prepare(raw,'button_bindings',{'0':[9,0xffffff]},1)
        frames,unused=prepare(raw,'button_bindings',{'0':[1,0x020000],'4':[1,0x010000]},1)
        self.assertEqual([frame[2][0] for frame in frames],[4,0])

    def test_arbitrary_shortcut_uses_documented_modifier_and_usage_encoding(self):
        raw=raw_config();action=[2,0x070e00]  # Ctrl+Shift+Alt+K
        frames,unused=prepare(raw,'button_bindings',{'4':action},1)
        self.assertEqual(frames[0][2],bytes([4,0,2,7,14,0]))
        self.assertEqual(action_label(action),'Ctrl+Shift+Alt+K')
        self.assertEqual(action_label([4,123]),'Макрос на устройстве')
        for bad in ([2,0x070e01],[2,0x07ff00],[2,1.5],[True,0]):
            with self.assertRaises(ValueError):prepare(raw,'button_bindings',{'4':bad},1)

    def test_invalid_values_cannot_form_writes(self):
        for field,change in [('dpi_config',{'x0':851}),('dpi_config',{'count':0}),('dpi_config',{'count':1,'active':2}),
                             ('sensor_config',{'rotation':31}),('sensor_config',{'motion_sync':1}),
                             ('sensor_config',{'performance_mode':3}),('button_bindings',{'4':[4,123]})]:
            with self.subTest(field=field,change=change),self.assertRaises(ValueError):prepare(raw_config(),field,change,1)

    def test_axes_follow_firmware_availability_and_native_diff_is_not_readback_marker(self):
        raw=raw_config();raw[50]=0
        self.assertFalse(values(raw)['dpi_config']['axes_available'])
        with self.assertRaisesRegex(ValueError,'separate DPI axes'):prepare(raw,'dpi_config',{'y0':450},1)
        with self.assertRaises(ValueError):prepare(raw,'dpi_config',{'axes_available':True},1)
        frames,allowed=prepare(raw,'dpi_config',{'x0':450,'y0':450},1)
        self.assertEqual(frames[0][2][16],255);self.assertNotIn(50,allowed)

    def test_stale_baseline_and_wrong_identity_do_not_write(self):
        for profile_change in (True,False):
            device=NativeTransport();expected=list(device.raw)
            if profile_change:device.raw[0]=0
            else:device.ident['pid']=0x1234
            with patch('mchose_adapter.candidates',return_value=[ITEM]),self.assertRaises((Fault,ValueError)):
                hardware('set',identity('fake'),'sensor_config',{'changes':{'ripple':True},'expected_raw':expected,'expected_mode':1},transport=lambda node:device)
            self.assertEqual(device.commands,[])

    def test_collateral_stops_batch_and_retains_snapshot(self):
        device=NativeTransport();device.collateral=True
        with self.assertRaisesRegex(Fault,'Unrelated K7'):
            self.execute(device,'button_bindings',{'3':[1,0x080000],'4':[1,0x100000]})
        self.assertEqual(len(device.commands),1)

    def test_native_readback_confirms_or_reports_mismatch_without_retry(self):
        for ignored in (False,True):
            device=NativeTransport();device.ignore=ignored
            plan=k7_setting_plan(identity('fake'),'sensor_config',{'ripple':True},device.raw,1)
            def runner(args):
                if args[2]=='set':return json.dumps(self.call(device,args[4],json.loads(args[5])))
                return json.dumps(device.read())
            result=perform(plan,runner)
            self.assertEqual(result.state,State.MISMATCH if ignored else State.CONFIRMED)
            self.assertEqual(len(device.commands),1)

    def test_native_sleep_and_debounce_do_not_rewrite_full_configuration(self):
        for field,value,command in [('sleep',5,0x0a),('debounce',8,0x43)]:
            device=NativeTransport();state=self.call(device,field,{'value':value,'expected_profile':1})
            self.assertEqual(state[field],value);self.assertEqual(device.commands[0][1],command)

    def test_debounce_outside_official_range_is_blocked_before_snapshot_or_write(self):
        device=NativeTransport()
        with patch('mchose_adapter.candidates',return_value=[ITEM]),patch('mchose_adapter.atomic_json') as snapshot:
            with self.assertRaises(ValueError):
                hardware('set',identity('fake'),'debounce',{'value':21,'expected_profile':1},transport=lambda node:device)
        self.assertEqual(device.commands,[]);snapshot.assert_not_called()


if __name__=='__main__':unittest.main()
