#!/usr/bin/env python3
"""Print a redacted, read-only report. No device changes or audio capture."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from diagnostics import collect
print(json.dumps(collect(),ensure_ascii=False,indent=2))
