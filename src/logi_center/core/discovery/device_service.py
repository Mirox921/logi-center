"""GTK/Qt-free orchestration for the existing device adapters.

This module only composes the existing read adapters. It does not define new
protocol behavior and is safe to call from a worker thread.
"""
from logi_center.core.devices.devices import DeviceManager
from logi_center.adapters.external.linux_input import InputAdapter, KernelBatteryAdapter
from logi_center.adapters.logitech.ratbag_adapter import RatbagAdapter
from logi_center.adapters.external.pulse_adapter import PulseAdapter
from logi_center.adapters.external.headset_adapter import HeadsetAdapter
from logi_center.adapters.logitech.saved_solaar import SavedSolaarAdapter
from logi_center.adapters.mchose.mchose_adapter import MchoseAdapter
from logi_center.adapters.external.openrgb_adapter import OpenRGBAdapter
from logi_center.adapters.external.openrazer_adapter import OpenRazerAdapter
from logi_center.adapters.external.rivalcfg_adapter import RivalcfgAdapter
from logi_center.adapters.external.ckb_adapter import CkbAdapter
from logi_center.adapters.mchose.ace68_adapter import Ace68Adapter
from logi_center.adapters.eweadn.eweadn_adapter import EweadnAdapter


def collect_device_snapshot(simulation=False, simulation_adapter=None, runner=None, keyboard_probe=None):
    """Return the same data shape consumed by the GTK pages plus DeviceManager."""
    from logi_center.adapters.external.backend import run as default_runner, keyboard_online
    runner = runner or default_runner
    keyboard_probe = keyboard_probe or keyboard_online

    if simulation:
        if simulation_adapter is None:
            from logi_center.core.services.simulation import SimulationAdapter
            simulation_adapter = SimulationAdapter()
        manager = DeviceManager([simulation_adapter])
        manager.discover()
        return {'manager': manager}

    data = {}
    queries = [
        ('mice', ['ratbagctl', 'list']),
        ('headset', ['headsetcontrol', '-o', 'json']),
        ('sinks', ['pactl', '-f', 'json', 'list', 'sinks']),
        ('sources', ['pactl', '-f', 'json', 'list', 'sources']),
        ('default_sink', ['pactl', 'get-default-sink']),
        ('default_source', ['pactl', 'get-default-source']),
    ]
    for key, args in queries:
        try:
            data[key] = runner(args, 40)
        except Exception as error:
            data[key + '_error'] = error
    try:
        data['keyboard_online'] = keyboard_probe()
    except Exception as error:
        data['keyboard_online_error'] = error

    cached = {tuple(args): data[key] for key, args in queries if key in data}

    def inventory_run(args, **kwargs):
        return cached[tuple(args)] if tuple(args) in cached else runner(args, **kwargs)

    from logi_center.adapters.logitech.ratbag_dbus import device_models
    manager = DeviceManager([
        InputAdapter(), KernelBatteryAdapter(), RatbagAdapter(inventory_run,detailed=True,model_lookup=device_models),
        PulseAdapter(inventory_run), HeadsetAdapter(inventory_run),
        SavedSolaarAdapter(), MchoseAdapter(), EweadnAdapter(runner=inventory_run), OpenRGBAdapter(),
        OpenRazerAdapter(), RivalcfgAdapter(), CkbAdapter(), Ace68Adapter(),
    ])
    manager.discover()
    data['manager'] = manager
    return data
