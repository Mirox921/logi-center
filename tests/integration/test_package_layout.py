"""Source and installed entry points must work without cwd/module aliases."""
from pathlib import Path
import ast
import contextlib
import io
import json
import os
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


class PackageLayout(unittest.TestCase):
    def test_runtime_imports_have_no_flat_project_module_dependencies(self):
        from scripts.source_manifest import runtime_files
        retired = {'backend', 'devices', 'execution', 'operations', 'drafts',
                   'control_service', 'qml_ui', 'mchose_adapter', 'eweadn_adapter',
                   'solaar_adapter', 'backups', 'capability_backup', 'i18n'}
        for path in runtime_files():
            if path.suffix != '.py':
                continue
            for node in ast.walk(ast.parse((ROOT/path).read_text())):
                if isinstance(node, ast.ImportFrom) and not node.level and node.module:
                    self.assertNotIn(node.module.split('.')[0], retired, str(path))
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotIn(alias.name.split('.')[0], retired, str(path))

    def test_source_version_from_unrelated_cwd_without_pythonpath(self):
        with tempfile.TemporaryDirectory() as folder:
            env = dict(os.environ, PYTHONPATH='')
            result = subprocess.run([sys.executable, str(ROOT/'app.py'), '--version'],
                                    cwd=folder, env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith('Logi Center '))

    def test_scoped_worker_imports_and_rejects_unknown_adapter_without_io(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, str(ROOT/'src/logi_center/_worker.py'),
                                     'sdk', 'unknown-test-adapter', 'discover'], cwd=folder,
                                    env=dict(os.environ, PYTHONPATH=''), capture_output=True,
                                    text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        reply = json.loads(result.stdout)
        self.assertFalse(reply['ok'])
        self.assertEqual(reply['code'], 'backend_unsupported')

    def test_installed_package_uses_only_its_bundled_resources(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder)
            with patch('pathlib.Path.home', return_value=home), \
                    patch.dict(os.environ, {'XDG_DATA_HOME': str(home/'data')}), \
                    contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(ROOT/'install.py'), run_name='__main__')
            runtime=home/'data/logi-center'
            code=("from logi_center.resources import assets_dir; "
                  "from logi_center.core.capabilities import Capability; "
                  "from logi_center.core.devices.devices import Capability as legacy; "
                  "assert Capability is legacy; "
                  "assert (assets_dir()/'mice/g502-top-wired-qt.svg').is_file(); "
                  "print(assets_dir())")
            env=dict(os.environ, PYTHONPATH=str(runtime))
            result=subprocess.run([sys.executable, '-c', code], cwd=folder, env=env,
                                  capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(runtime/'logi_center/assets'))
            version=subprocess.run([str(home/'.local/bin/logi-center'), '--version'],
                                   cwd=folder, env=dict(os.environ, PYTHONPATH=''),
                                   capture_output=True, text=True, timeout=10)
            self.assertEqual(version.returncode, 0, version.stderr)
