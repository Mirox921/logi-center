"""Release metadata stays consistent with the installed application version."""
from pathlib import Path
import contextlib,io,re,unittest
from version import VERSION


class ReleaseVersion(unittest.TestCase):
    def test_package_and_readmes_match_runtime_version(self):
        root=Path(__file__).resolve().parent
        package=re.search(r'^pkgver=(.+)$',(root/'packaging/arch/PKGBUILD').read_text(),re.M)[1]
        self.assertEqual(package,VERSION)
        for name in ('README.md','README.ru.md'):
            self.assertIn('/releases/tag/v'+VERSION,(root/name).read_text())

    def test_version_command_needs_no_gui_or_device_discovery(self):
        import app
        with contextlib.redirect_stdout(io.StringIO()) as out:
            with self.assertRaises(SystemExit) as result:app.main(['--version'])
        self.assertEqual(result.exception.code,0)
        self.assertEqual(out.getvalue().strip(),'Logi Center '+VERSION)
