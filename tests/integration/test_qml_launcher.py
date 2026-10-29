"""QML-only routing, compatibility flags and missing-runtime failures; no GUI."""
import contextlib
import io
import os
import sys
import unittest
from unittest.mock import patch
import logi_center.cli as app


class LauncherTests(unittest.TestCase):
    def test_default_and_explicit_qml_preserve_simulation_and_qt_arguments(self):
        for flags in ([],['--ui','qml'],['--ui=qml']):
            with patch('logi_center.qml_ui.main.run',return_value=17) as run:
                result=app.main([*flags,'--simulate','--smoke','--debug-text','-platform','offscreen'])
            self.assertEqual(result,17)
            self.assertEqual(run.call_args.args[0],[sys.argv[0],'-platform','offscreen','--simulate','--smoke','--debug-text'])

    def test_legacy_gtk_request_cannot_launch_wrong_interface_silently(self):
        with patch('logi_center.qml_ui.main.run') as run,contextlib.redirect_stderr(io.StringIO()) as stderr:
            with self.assertRaises(SystemExit) as error:app.main(['--ui','gtk'])
        self.assertEqual(error.exception.code,2);run.assert_not_called()
        self.assertIn('GTK has been archived',stderr.getvalue())

    def test_missing_qt_reports_dependency_without_importing_gtk_or_discovering_devices(self):
        import builtins
        original=builtins.__import__
        def blocked(name,*args,**kwargs):
            if name.startswith('PySide6'):raise ModuleNotFoundError('Qt is not installed',name='PySide6')
            if name=='gi' or name.startswith('gi.'):raise AssertionError('GTK/GI imported by launcher')
            return original(name,*args,**kwargs)
        with patch('builtins.__import__',side_effect=blocked),patch.dict(os.environ),\
             patch('logi_center.adapters.external.backend.run',side_effect=AssertionError('Hardware I/O')),contextlib.redirect_stderr(io.StringIO()) as stderr:
            result=app.main(['--simulate'])
        self.assertEqual(result,2);self.assertIn('install PySide6',stderr.getvalue())

    def test_help_is_available_without_loading_either_gui(self):
        with patch('logi_center.qml_ui.main.run') as run,contextlib.redirect_stdout(io.StringIO()) as stdout:
            with self.assertRaises(SystemExit) as error:app.main(['--help'])
        self.assertEqual(error.exception.code,0);run.assert_not_called()
        self.assertIn('Qt6/QML',stdout.getvalue())
