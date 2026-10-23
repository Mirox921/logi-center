#!/usr/bin/env python3
"""Print a redacted, read-only report. No device changes or audio capture."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from diagnostics import collect
from devices import DeviceManager,InputAdapter,RatbagAdapter,PulseAdapter,HeadsetAdapter,SavedSolaarAdapter
from reports import build_report
from mchose_adapter import MchoseAdapter
from openrgb_adapter import OpenRGBAdapter
from openrazer_adapter import OpenRazerAdapter
from rivalcfg_adapter import RivalcfgAdapter
from ckb_adapter import CkbAdapter
manager=DeviceManager([InputAdapter(),RatbagAdapter(detailed=True),PulseAdapter(),HeadsetAdapter(),SavedSolaarAdapter(),MchoseAdapter(),OpenRGBAdapter(),OpenRazerAdapter(),RivalcfgAdapter(),CkbAdapter()])
manager.discover()
print(json.dumps(build_report(manager,collect()),ensure_ascii=False,indent=2))
