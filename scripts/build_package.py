"""Copy canonical non-Python resources into a wheel, never generate artwork."""
from pathlib import Path
import shutil
from setuptools.command.build_py import build_py


class BuildPy(build_py):
    def run(self):
        super().run()
        root = Path(__file__).resolve().parents[1]
        destination = Path(self.build_lib) / 'logi_center/assets'
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(root / 'assets', destination)
