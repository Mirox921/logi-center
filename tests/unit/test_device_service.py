import unittest

from logi_center.core.discovery.device_service import collect_device_snapshot


class DeviceServiceTests(unittest.TestCase):
    def test_dashboard_fixture_accepts_discovery_callback_arguments(self):
        from scripts.illustration_dashboard import fixture_snapshot
        from logi_center.core.services.simulation import SimulationAdapter
        snapshot=fixture_snapshot(True,SimulationAdapter())
        self.assertEqual(len(snapshot['manager'].devices),10)
        self.assertTrue(all(d.simulated for d in snapshot['manager'].devices))

    def test_simulation_never_calls_real_command_runner(self):
        class OfflineSimulation:
            def discover(self):
                from logi_center.core.services.simulation import SimulationAdapter
                return SimulationAdapter().discover()
        def forbidden(*_args, **_kwargs):
            raise AssertionError('real I/O must not be called in simulation')
        snapshot = collect_device_snapshot(simulation=True, simulation_adapter=OfflineSimulation(), runner=forbidden)
        self.assertTrue(snapshot['manager'].devices)
        self.assertTrue(all(d.simulated for d in snapshot['manager'].devices))


if __name__ == '__main__':
    unittest.main()
