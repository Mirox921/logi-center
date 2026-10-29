import unittest,tempfile,json
from pathlib import Path
from unittest.mock import Mock
from logi_center.core.services.diagnostics import collect,fault_for,SafeLog
from logi_center.core.services.execution import Fault,FaultCode,classify,redact
class Diagnostics(unittest.TestCase):
    def test_missing_and_installed_but_unavailable_distinct(self):
        runner=Mock(side_effect=Fault(FaultCode.UNAVAILABLE,'ratbagctl','loader error'))
        report=collect(runner,which=lambda name:'/bin/'+name if name=='ratbagctl' else None,sysfs='/nonexistent')
        self.assertEqual(report[0]['state'],'component_unavailable')
        self.assertEqual(report[1]['state'],'missing_component')
    def test_permission_and_unsupported_and_disconnect(self):
        self.assertEqual(classify('hid','Permission denied').code,FaultCode.PERMISSION)
        self.assertEqual(classify('hid','Feature not supported').code,FaultCode.DEVICE_UNSUPPORTED)
        self.assertEqual(classify('hid','No online device').code,FaultCode.DISCONNECTED)
    def test_bad_config_and_internal_distinct(self):
        self.assertEqual(fault_for(ValueError('bad file')).code,FaultCode.CONFIG)
        self.assertEqual(fault_for(RuntimeError('internal')).code,FaultCode.INTERNAL)
    def test_log_redaction_and_no_command_values(self):
        from logi_center.core.services.operations import Result,State
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'diag.log';log=SafeLog(path)
            log.fault(Fault(FaultCode.CONFIG,'config','token=secret /home/person/private'))
            log.operation(Result(State.SENT,'ratbagctl',requested='private macro text'))
            log.close();text=path.read_text()
            self.assertNotIn('secret',text);self.assertNotIn('/home/person',text);self.assertNotIn('private macro text',text)
    def test_report_does_not_capture_audio(self):
        runner=Mock(return_value='[]')
        collect(runner,which=lambda name:None,sysfs='/nonexistent')
        self.assertFalse(any(c.args[0][0] in ['parec','paplay'] for c in runner.call_args_list))

    def test_rotated_logs_remain_private(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'diag.log';log=SafeLog(path)
            log.logger.handlers[0].maxBytes=100
            for index in range(4):log.fault(Fault(FaultCode.CONFIG,'test','x'*120))
            log.close()
            for entry in Path(root).glob('diag.log*'):self.assertEqual(entry.stat().st_mode & 0o777,0o600)
