#!/usr/bin/env python3
"""Print a redacted, read-only report. No device changes or audio capture."""
# Allow direct execution without installing developer tools.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import scripts  # source-package bootstrap
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from logi_center.core.services.diagnostics import collect
from logi_center.core.devices.devices import DeviceManager
from logi_center.adapters.external.linux_input import InputAdapter
from logi_center.adapters.logitech.ratbag_adapter import RatbagAdapter
from logi_center.adapters.external.pulse_adapter import PulseAdapter
from logi_center.adapters.external.headset_adapter import HeadsetAdapter
from logi_center.adapters.logitech.saved_solaar import SavedSolaarAdapter
from logi_center.core.services.reports import build_report
from logi_center.adapters.mchose.mchose_adapter import MchoseAdapter
from logi_center.adapters.external.openrgb_adapter import OpenRGBAdapter
from logi_center.adapters.external.openrazer_adapter import OpenRazerAdapter
from logi_center.adapters.external.rivalcfg_adapter import RivalcfgAdapter
from logi_center.adapters.external.ckb_adapter import CkbAdapter
from logi_center.adapters.mchose.ace68_adapter import Ace68Adapter
manager=DeviceManager([InputAdapter(),RatbagAdapter(detailed=True),PulseAdapter(),HeadsetAdapter(),SavedSolaarAdapter(),MchoseAdapter(),OpenRGBAdapter(),OpenRazerAdapter(),RivalcfgAdapter(),CkbAdapter(),Ace68Adapter()])
manager.discover()
print(json.dumps(build_report(manager,collect()),ensure_ascii=False,indent=2))
