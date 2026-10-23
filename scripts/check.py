#!/usr/bin/env python3
"""Run the small deterministic test suite without devices or audio capture."""
from pathlib import Path
import compileall,subprocess,sys
root=Path(__file__).resolve().parents[1]
if not compileall.compile_dir(root,quiet=1):raise SystemExit(1)
raise SystemExit(subprocess.call([sys.executable,'-m','unittest','-v'],cwd=root))
