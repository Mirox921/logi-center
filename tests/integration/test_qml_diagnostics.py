import json,tempfile,time,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from logi_center.core.devices.devices import Device, DeviceManager
from logi_center.core.capabilities.model import Capability
try:
    from PySide6.QtCore import QObject,QCoreApplication
    from logi_center.qml_ui.bridge.diagnostics import DiagnosticController
except ImportError:QCoreApplication=None


@unittest.skipIf(QCoreApplication is None,'optional PySide6 unavailable')
class DiagnosticBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QCoreApplication.instance() or QCoreApplication([])
    def setUp(self):
        self.owner=QObject();self.owner.tr=lambda text:text;self.owner.simulation=True
        self.owner._manager=DeviceManager();self.owner._manager.devices=[Device('private','Mouse SN:SECRET123','mouse','test',physical='/private/device',capabilities=[Capability('macros','test',value=['SECRET_MACRO'])])]
        self.owner._current_devices=lambda:self.owner._manager.devices
        self.pool=ThreadPoolExecutor(max_workers=1);self.controller=DiagnosticController(self.owner,self.pool)
    def tearDown(self):self.controller.shutdown();self.pool.shutdown(wait=True)
    def test_report_export_reuses_allowlisted_schema(self):
        self.controller.sync()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'report.json';self.controller.exportReport(str(path))
            deadline=time.monotonic()+2
            while self.controller.busy and time.monotonic()<deadline:self.app.processEvents();time.sleep(.005)
            raw=path.read_text();report=json.loads(raw)
            self.assertEqual(report['format'],'logi-center-public-diagnostics')
            for private in ('SECRET123','/private/device','SECRET_MACRO'):self.assertNotIn(private,raw)
    def test_optional_component_collection_in_simulation_never_probes_host(self):
        from unittest.mock import patch
        with patch('logi_center.core.services.diagnostics.collect',side_effect=AssertionError('real I/O')):
            self.controller.collect()
        self.assertEqual(self.controller.components[0]['component'],'simulation')

    def test_sleeping_s9_discovery_fault_survives_qml_report_sync(self):
        from unittest.mock import patch,Mock
        from logi_center.adapters.eweadn.eweadn_adapter import EweadnAdapter
        from logi_center.core.services.execution import Fault,FaultCode
        from tests.unit.test_eweadn import ITEM
        with tempfile.TemporaryDirectory() as folder:
            node=Path(folder)/'usb';node.mkdir()
            for name,value in [('idVendor','372e'),('idProduct','1026'),('product','EWEADN S9')]:
                (node/name).write_text(value)
            runner=Mock(side_effect=Fault(FaultCode.TIMEOUT,'eweadn','Wake the mouse'))
            adapter=EweadnAdapter(folder,runner=runner)
            with patch('logi_center.adapters.eweadn.eweadn_adapter.candidates',return_value=[{**ITEM,'physical':str(node)}]):
                self.owner._manager=DeviceManager([adapter]);self.owner._manager.discover()
            self.controller.sync()
            device=json.loads(self.controller.reportText)['devices'][0]
            self.assertIs(device['simulated'],False)
            self.assertEqual(device['faults'],[{'component':'eweadn','code':'timeout'}])
            self.assertEqual(len(self.controller.inventory),1)
