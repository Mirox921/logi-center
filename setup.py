"""Setuptools resource-copy hook; project metadata lives in pyproject.toml."""
from pathlib import Path
import runpy
from setuptools import setup

BuildPy = runpy.run_path(str(Path(__file__).parent / 'scripts/build_package.py'))['BuildPy']
setup(cmdclass={'build_py': BuildPy})
