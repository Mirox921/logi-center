"""Confirmed G515 LS TKL diagnostics as regression fixtures; no device I/O."""
import tempfile,unittest,sys
from pathlib import Path
from unittest.mock import Mock,patch
from execution import Fault,FaultCode
from g515_adapter import read_snapshot,parse_value,READ_KEYS

OUTPUT={
'rgb_control':'# LED Control\n#   possible values: on/true/t/yes/y/1 or off/false/f/no/n/0 or Toggle/~\nrgb_control = False\n',
'brightness_control':'# Brightness Control\nbrightness_control = 83\n',
'rgb_zone_1':'rgb_zone_1 = !LEDEffectSetting {ID: 1, color: 0xffffff, period: 3000, intensity: 100}\n',
'per-key-lighting':'per-key-lighting = {1:0xffffff, 2:0xff0000, 3:No change}\n',
'rgb_idle_timeout':'# Idle Timeout\n#   possible values: one of [ Disabled, 15 Seconds, 30 Seconds, 1 Minute, 2 Minutes, 5 Minutes ]\nrgb_idle_timeout = 1 Minute\n',
'rgb_sleep_timeout':'# Sleep Timeout\n#   possible values: one of [ Disabled, 2 Minutes, 5 Minutes, 10 Minutes, 15 Minutes, 30 Minutes ]\nrgb_sleep_timeout = 5 Minutes\n'}


class G515Reads(unittest.TestCase):
    def test_detected_40b4_without_cache_false_control_keeps_all_other_settings(self):
        calls=[]
        def runner(args,**kwargs):
            calls.append(args);return OUTPUT[args[-1]]
        result=read_snapshot('G515 LS TKL',runner,cache={})
        self.assertTrue(result['reachable']);self.assertEqual(result['errors'],[])
        self.assertIs(result['saved']['rgb_control'],False)
        self.assertEqual(result['sources']['rgb_control'],'device')
        self.assertEqual(result['sources']['brightness_control'],'device')
        self.assertEqual(result['sources']['rgb_zone_1'],'backend_cache')
        self.assertEqual(result['saved']['per-key-lighting']['2'],'0xff0000')
        self.assertEqual(len(calls),len(READ_KEYS))
        self.assertTrue(all(c[:3]==['solaar','config','G515 LS TKL'] and len(c)==4 for c in calls))
        self.assertTrue({'rgb_idle_timeout','rgb_sleep_timeout','brightness_control'}<={s['key'] for s in result['settings']})
        from control_service import g515_controls
        fields=g515_controls(result['settings'],result['saved'],'test',result['target'],result['sources'])
        control=next(f for f in fields if f.id=='g515:rgb_control');self.assertEqual(control.observed,'false')
        self.assertEqual(control.source,'device')
        brightness=next(f for f in fields if f.id=='g515:brightness_control')
        self.assertEqual(brightness.observed,83);self.assertEqual(brightness.validate(79),79)
        self.assertEqual(brightness.plans(79)[0].command,['solaar','config','G515 LS TKL','brightness_control','79'])
        self.assertIn('g515:effect',[f.id for f in fields])

    def test_live_getters_win_but_synthetic_timer_defaults_do_not_overwrite_cache(self):
        cache={'rgb_control':'true','brightness_control':'50','rgb_idle_timeout':'0','rgb_sleep_timeout':'1800',
               'rgb_zone_1':{'ID':'21','period':'8000','intensity':'60'},'rgb_startup_animation':{'ID':'1'}}
        result=read_snapshot(runner=lambda args,**kw:OUTPUT[args[-1]],cache=cache)
        self.assertIs(result['saved']['rgb_control'],False)
        self.assertEqual(result['saved']['brightness_control'],83)
        self.assertEqual(result['saved']['rgb_idle_timeout'],'0')
        self.assertEqual(result['saved']['rgb_zone_1']['ID'],'21')
        self.assertEqual(result['saved']['rgb_startup_animation'],{'ID':'1'})
        self.assertEqual(cache['rgb_control'],'true')

    def test_failed_exit_empty_stdout_and_unreadable_settings_are_not_success(self):
        for output in ('','rgb_control = ? (failed to read from device)','Some other log'):
            with self.assertRaises(Fault):read_snapshot(runner=lambda *a,**kw:output,cache={})
        calls=[]
        def fail(args,**kwargs):calls.append(args);raise Fault(FaultCode.DISCONNECTED,'solaar','No online device')
        with self.assertRaises(Fault):read_snapshot(runner=fail,cache={})
        self.assertEqual(len(calls),1)
        fallback=read_snapshot(runner=fail,cache={'rgb_control':'false'})
        self.assertFalse(fallback['reachable']);self.assertTrue(fallback['errors'])
        self.assertEqual(fallback['settings'][0]['value'],'false')

    def test_tags_and_no_objects_or_evaluation(self):
        value,_=parse_value('rgb_zone_1',OUTPUT['rgb_zone_1'])
        self.assertEqual(value['color'],'0xffffff')
        for text in ('rgb_zone_1 = !LEDEffectSetting {broken',
                     'rgb_zone_1 = !!python/object/apply:os.system [touch nope]'):
            with self.assertRaises(ValueError):parse_value('rgb_zone_1',text)

    def test_config_name_case_tags_and_xdg_lookup(self):
        from backend import saved_keyboard,keyboard_saved_settings
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'solaar/config.yaml';path.parent.mkdir()
            path.write_text('- 1.1.20\n- _NAME: g515 LS TKL\n  _wpid: 40B4\n  rgb_control: false\n  rgb_zone_1: !LEDEffectSetting {ID: 1, color: 0xffffff}\n  rgb_startup_animation: !BootEffect {ID: 1}\n')
            with patch.dict('os.environ',{'XDG_CONFIG_HOME':folder}):
                value=saved_keyboard();self.assertEqual(value['_wpid'],'40B4')
                self.assertEqual(value['rgb_startup_animation']['ID'],'1')
                self.assertEqual(next(s['value'] for s in keyboard_saved_settings() if s['key']=='rgb_control'),'false')
            path.write_text(path.read_text()+'- _NAME: G515 LS TKL\n  rgb_control: true\n')
            self.assertEqual(saved_keyboard(path),{})


class ScopedProcess(unittest.TestCase):
    def test_single_read_bypasses_name_only_root_gate_and_uses_readonly_process(self):
        from backend import run
        with patch('execution.command',return_value=OUTPUT['rgb_control']) as execute,patch('backend.keyboard_online',return_value=False) as ping:
            self.assertIn('False',run(['solaar','config','G515 LS TKL','rgb_control']))
            args=execute.call_args.args[0]
            self.assertEqual(args[2:],['--read-only','config','G515 LS TKL','rgb_control'])
            ping.assert_not_called()

    def test_stdout_warning_and_exit_code_contract(self):
        from execution import command
        from backend import run
        text=command([sys.executable,'-c',"import sys;print('warning',file=sys.stderr);print('rgb_control = False')"])
        self.assertEqual(parse_value('rgb_control',text)[0],False)
        with self.assertRaises(Fault):command([sys.executable,'-c',"import sys;print('rgb_control = False');print('permission denied',file=sys.stderr);sys.exit(1)"])
        with patch('execution.command',side_effect=Fault(FaultCode.PERMISSION,'python','G515 LS TKL permission denied')):
            with self.assertRaises(Fault) as raised:run(['solaar','config','G515 LS TKL','rgb_control'])
        self.assertEqual(raised.exception.component,'solaar');self.assertNotIn('G515 LS TKL',raised.exception.message)

    def test_readonly_rejects_writes_enumeration_and_startup_commands(self):
        from solaar_write import read_only_args,guard_reads
        for args in (['config','G515'],['config','G515','rgb_control','true'],['show','G515'],['config','G515','rgb_startup_animation']):
            with self.assertRaises(ValueError):read_only_args(args)
        self.assertEqual(read_only_args(['config','G515','rgb_control']),['config','G515','rgb_control'])
        class Setting:
            def write(self,value):raise AssertionError('write reached transport')
            def apply(self):raise AssertionError('apply reached transport')
        class Override(Setting):
            def write(self,value):raise AssertionError('override reached transport')
        package=Mock(Setting=Setting);power=Mock()
        guard_reads(package,power)
        for call in (lambda:Override().write(True),lambda:Setting().apply(),lambda:power.start(None)):
            with self.assertRaisesRegex(RuntimeError,'disabled'):call()
        power.cleanup('device');power.stop.assert_called_once_with('device')


if __name__=='__main__':unittest.main()
