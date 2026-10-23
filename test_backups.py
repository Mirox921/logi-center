import unittest,tempfile,copy
from pathlib import Path
from unittest.mock import patch,Mock
from backups import seal,validate,read_backup,write_backup,preview,restore
from operations import State
from execution import Fault,FaultCode

def sample(dpi=800,rate=1000):
    return seal('mouse','usb:046d:c08b:0',{'profiles':[{'index':0,'active':True,'rate':rate,'resolutions':[{'index':0,'dpi':dpi,'active':True,'default':True,'disabled':False}],'buttons':[{'index':0,'action':['button','1']}],'leds':[]}]},'backend_cache')
class Backups(unittest.TestCase):
    def test_corrupt_integrity(self):
        data=sample();data['settings']['profiles'][0]['rate']=500
        with self.assertRaisesRegex(ValueError,'integrity'):validate(data)
    def test_wrong_model(self):
        other=seal('mouse','different',sample()['settings'],'backend_cache')
        with self.assertRaisesRegex(ValueError,'model'):preview(sample(),other,'m')
    def test_injected_command_cannot_become_restore_action(self):
        data=sample();data['settings']['profiles'][0]['buttons'][0]['action']=['shell','rm -rf /']
        data=seal('mouse',data['device']['model'],data['settings'],'backend_cache')
        with self.assertRaises(ValueError):validate(data)
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'backup.json';data=sample();write_backup(data,path)
            self.assertEqual(read_backup(path),data)
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
    def test_partial_restore_has_safety_copy_and_stops(self):
        current=sample();wanted=sample(1600,500);plan=preview(wanted,current,'mouse')
        runner=Mock(side_effect=['','500',Fault(FaultCode.DISCONNECTED,'mouse','gone')])
        with tempfile.TemporaryDirectory() as root,patch('backups.snapshot',return_value=current):
            report=restore(plan,{'dpi'},'mouse',runner,safety_root=root)
            self.assertTrue(Path(report.safety_copy).exists());self.assertTrue(report.stopped)
            self.assertEqual([r.state for _,r in report.results],[State.SENT,State.DISCONNECTED])
    def test_changed_since_preview_aborts_before_write(self):
        plan=preview(sample(1600),sample(),'mouse');runner=Mock()
        with patch('backups.snapshot',return_value=sample(1200)):
            with self.assertRaisesRegex(ValueError,'changed'):restore(plan,{'dpi'},'mouse',runner)
        runner.assert_not_called()
    def test_selection_omits_unselected_settings(self):
        current=sample();plan=preview(sample(1600),current,'mouse');runner=Mock()
        with tempfile.TemporaryDirectory() as root,patch('backups.snapshot',return_value=current):
            report=restore(plan,{'buttons'},'mouse',runner,safety_root=root)
            self.assertEqual(report.results,[]);runner.assert_not_called()

    def test_unbalanced_macro_rejected(self):
        data=sample();data['settings']['profiles'][0]['buttons'][0]['action']=['macro','+KEY_A']
        with self.assertRaisesRegex(ValueError,'held down'):validate(seal('mouse',data['device']['model'],data['settings'],'backend_cache'))
    def test_non_string_action_rejected_before_command(self):
        data=sample();data['settings']['profiles'][0]['buttons'][0]['action']=['button',1]
        with self.assertRaises(ValueError):validate(seal('mouse',data['device']['model'],data['settings'],'backend_cache'))
    def test_unsupported_version(self):
        data=sample();data['version']=True
        from backups import digest
        data['sha256']=digest(data)
        with self.assertRaisesRegex(ValueError,'version'):validate(data)
