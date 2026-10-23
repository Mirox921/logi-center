import json,unittest
from devices import Device,Capability,DeviceManager
from reports import build_report
class Reports(unittest.TestCase):
    def test_sensitive_identifiers_values_choices_and_macros_omitted(self):
        manager=DeviceManager();manager.devices=[Device('secret-id','Audio personal name','audio','pactl',target='secret-endpoint',physical='/home/alice/private',capabilities=[Capability('output:secret-endpoint:volume','pactl',value='private macro',choices=['private macro',10])])]
        text=json.dumps(build_report(manager))
        for secret in ['secret-id','secret-endpoint','/home/alice','private macro','Audio personal name']:self.assertNotIn(secret,text)
        self.assertIn('volume',text)
    def test_simulation_evidence_is_preserved(self):
        from simulation import SimulationAdapter
        manager=DeviceManager([SimulationAdapter()]);manager.discover();report=build_report(manager)
        self.assertTrue(all(d['simulated'] for d in report['devices']))
