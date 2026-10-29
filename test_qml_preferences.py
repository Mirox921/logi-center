import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from qml_ui.bridge.preferences import load_preferences, save_preferences, system_reduced_motion


class GuiPreferencesTests(unittest.TestCase):
    def test_private_roundtrip_keeps_unrelated_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'gui.json';path.write_text('{"future_setting": 7}')
            save_preferences({'language':'en','show_builtin':False,'reduced_motion':True},path)
            self.assertEqual(load_preferences(path),{'language':'en','show_builtin':False,'reduced_motion':True,'ui_scale':100})
            self.assertEqual(json.loads(path.read_text())['future_setting'],7)
            self.assertEqual(path.stat().st_mode & 0o777,0o600)

    def test_corrupt_preferences_are_not_destroyed(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'gui.json';path.write_text('broken')
            self.assertTrue(load_preferences(path)['show_builtin'])
            with self.assertRaises(ValueError):save_preferences({'language':'en'},path)
            self.assertEqual(path.read_text(),'broken')

    def test_system_reduced_motion_is_read_only_and_bounded(self):
        calls=[]
        def command(args,timeout):calls.append((args,timeout));return 'false\n'
        with patch.dict('os.environ',{'LOGI_CENTER_REDUCED_MOTION':'0'}):
            self.assertTrue(system_reduced_motion(command))
        self.assertEqual(calls,[(['gsettings','get','org.gnome.desktop.interface','enable-animations'],1)])
        self.assertNotIn('set',calls[0][0])

    def test_environment_override_never_probes_system(self):
        with patch.dict('os.environ',{'LOGI_CENTER_REDUCED_MOTION':'1'}):
            self.assertTrue(system_reduced_motion(lambda *_a,**_k:self.fail('unexpected system probe')))

    def test_scale_validation_and_external_factor_composition(self):
        from qml_ui.bridge.preferences import qt_scale
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'gui.json'
            for value in [True,0,999,100.1,'150',None]:
                path.write_text(json.dumps({'ui_scale':value}))
                self.assertEqual(load_preferences(path)['ui_scale'],100)
            save_preferences({'ui_scale':150},path)
            self.assertEqual(load_preferences(path)['ui_scale'],150)
        self.assertEqual(qt_scale({'QT_SCALE_FACTOR':'1.25'},150),'1.875')
        for bad in ('nan','bad','0','-2'):
            self.assertEqual(qt_scale({'QT_SCALE_FACTOR':bad},125),'1.25')
