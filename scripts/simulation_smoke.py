#!/usr/bin/env python3
"""Desktop integration of simulated capabilities with all real CLI I/O forbidden."""
from pathlib import Path
import sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.argv=['logi-simulation','--simulate','--smoke']
from unittest.mock import patch
from app import Center,GLib
from drafts import DraftStore
from reports import build_report
from operations import State
with tempfile.TemporaryDirectory() as root,patch('backend.run',side_effect=AssertionError('Real CLI call from simulation')) as hardware,patch('app.save_preferences'):
    app=Center();assert app.get_application_id().endswith('.Simulation');app.set_application_id('local.mirox.LogiCenter.SimulationCheck');app.draft_store=DraftStore(Path(root)/'drafts.json')
    checks=[]
    def inspect():
        assert len(app.device_manager.devices)==14
        assert all(d.simulated for d in app.device_manager.devices)
        assert not app.audio_session.processes
        result=app.simulation_adapter.apply('gaming-mouse','dpi',1600)
        assert result.state==State.SENT
        app.show_operation(result)
        assert all(d['simulated'] for d in build_report(app.device_manager)['devices'])
        checks.append('simulation');app.quit();return False
    GLib.timeout_add_seconds(3,inspect);app.run(['logi-simulation'])
    assert checks==['simulation'];hardware.assert_not_called()
print('Simulation GTK smoke: 14 scenarios; real CLI never called; no capture')
