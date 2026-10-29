"""Explicit UI-only backup fixtures. No process, HID, audio or filesystem reads."""
import json
from devices import Device, Capability, DeviceManager
from mchose_adapter import setting_plan


class BackupSimulation:
    def __init__(self):
        self.values = {'dpi': 800, 'debounce': 4}
        self.legacy_dpi = 800
        self.writes = []
        self.fail_field = ''
        self.unverified = False
        caps = []
        for field, value in self.values.items():
            cap = Capability(field, 'mchose', True, True, True, True, value, 'simulation',
                             minimum=50 if field == 'dpi' else 0,
                             maximum=26000 if field == 'dpi' else 255)
            cap.plan = lambda value, field=field: setting_plan('sim-backup', field, value)
            caps.append(cap)
        self.devices = [Device('sim:backup-provider', 'MCHOSE · SIM', 'mouse', 'mchose',
                               'sim-backup', vid='3837', pid='1001', simulated=True, capabilities=caps),
                        Device('sim:backup-legacy', 'libratbag · SIM', 'mouse', 'ratbagctl',
                               'sim-ratbag', simulated=True)]
        self.manager = DeviceManager()
        self.manager.devices = self.devices

    def run(self, args, **unused):
        from execution import Fault, FaultCode
        if args[:2] == ['logi-sdk', 'mchose'] and args[3] == 'sim-backup':
            if args[2] == 'read':
                if self.unverified and self.writes:
                    raise Fault(FaultCode.TIMEOUT, 'simulation', 'Simulated readback timeout')
                return json.dumps(self.values)
            if args[2] == 'set' and args[4] in self.values:
                self.writes.append(args[4])
                if args[4] == self.fail_field:
                    raise Fault(FaultCode.DISCONNECTED, 'simulation', 'Simulated disconnect')
                self.values[args[4]] = json.loads(args[5])
                return ''
        if args[:2] == ['ratbagctl', 'sim-ratbag']:
            if args[2:] == ['info']:
                return f'Model: simulation-ratbag\nProfile 0: (active)\n  Report Rate: 1000Hz\n    0: {self.legacy_dpi}dpi (active) (default)\n'
            if args[2:] == ['dpi', 'get-all']: return '800 1600'
            if args[2:] == ['rate', 'get-all']: return '500 1000'
            if args[2:6] == ['profile', '0', 'resolution', '0']:
                if args[-2] == 'set':
                    self.writes.append('legacy:dpi')
                    self.legacy_dpi = int(args[-1]); return ''
                if args[-1] == 'get': return str(self.legacy_dpi)
        raise AssertionError('Unexpected simulated backup request')
