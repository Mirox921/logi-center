import unittest
from datetime import datetime,timedelta,timezone
from logi_center.core.services.battery_presentation import battery_display
from logi_center.core.capabilities.model import Capability
from logi_center.core.devices.devices import Device
from logi_center.core.services.execution import Fault,FaultCode
from logi_center.i18n import set_language


class BatteryDisplayTests(unittest.TestCase):
    def setUp(self):set_language('ru')
    def device(self, value=None, source='device'):
        return Device('one','Mouse','mouse','test',capabilities=[Capability('battery_status','test',True,True,value=value,source=source)])

    def test_unknown_is_never_zero_and_zero_remains_real(self):
        self.assertEqual(battery_display(self.device())['batteryPercent'],-1)
        self.assertEqual(battery_display(self.device(0))['batteryPercent'],0)
        self.assertEqual(battery_display(self.device(0))['batteryLabel'],'0%')

    def test_cached_and_stale_values_do_not_fill_live_meter(self):
        cached=battery_display(self.device(82,'backend_cache'))
        self.assertEqual(cached['batteryPercent'],-1);self.assertIn('82%',cached['batteryLabel'])
        d=self.device(50);d.capabilities[0].observed_at=(datetime.now(timezone.utc)-timedelta(seconds=100)).isoformat()
        self.assertEqual(battery_display(d)['batteryState'],'stale')
        self.assertEqual(battery_display(d)['batteryPercent'],-1)

    def test_permission_error_is_scoped_to_the_battery_provider(self):
        d=self.device(64);d.faults=[Fault(FaultCode.PERMISSION,'test','private detail')]
        result=battery_display(d)
        self.assertEqual(result['batteryState'],'denied');self.assertEqual(result['batteryPercent'],-1)
        d.capabilities.append(Capability('battery_status','kernel-battery',True,True,value=70,source='kernel'))
        result=battery_display(d)
        self.assertEqual(result['batteryPercent'],70)
        self.assertEqual(result['batterySource'],'kernel')

    def test_charging_requires_explicit_fresh_positive_evidence(self):
        d=self.device(90)
        self.assertFalse(battery_display(d)['charging'])
        c=Capability('charging','test',True,True,value=True,source='backend_cache');d.capabilities.append(c)
        self.assertFalse(battery_display(d)['charging'])
        c.source='device';self.assertTrue(battery_display(d)['charging'])
        c.observed_at='invalid';self.assertFalse(battery_display(d)['charging'])

    def test_charging_is_independent_of_percentage_and_newer_false_wins(self):
        d=self.device();d.capabilities.append(Capability('charging','test',True,True,value=True,source='device'))
        self.assertTrue(battery_display(d)['charging']);self.assertEqual(battery_display(d)['batteryPercent'],-1)
        d.capabilities.append(Capability('charging','kernel-battery',True,True,value=False,source='kernel'))
        self.assertFalse(battery_display(d)['charging'])

    def test_levels_remain_levels_and_disconnect_clears_live_state(self):
        d=self.device('High','kernel');result=battery_display(d)
        self.assertEqual(result['batteryPercent'],-1);self.assertEqual(result['batteryLabel'],'Высокий заряд')
        d.connected=False;result=battery_display(d)
        self.assertEqual(result['batteryState'],'disconnected');self.assertFalse(result['charging'])
