#!/usr/bin/env python3
"""Reproducible adapter call-count benchmark; simulated transport, no hardware I/O."""
from pathlib import Path
import sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from devices import RatbagAdapter
count=50
for detailed in [True,False]:
    calls=[]
    def runner(args):
        calls.append(args)
        if args==['ratbagctl','list']:return '\n'.join(f'mouse-{i}: Generic gaming mouse {i}' for i in range(count))
        if args[-1]=='info':return 'Model: usb:1234:5678:0\nProfile 0: (active)\n  Report Rate: 1000Hz\n    0: 800dpi (active)\n'
        return '800 1600' if 'dpi' in args else '500 1000'
    start=time.perf_counter();devices=RatbagAdapter(runner,detailed=detailed).discover();elapsed=time.perf_counter()-start
    print(('eager' if detailed else 'lazy')+f': {len(devices)} devices, {len(calls)} transport calls, {elapsed*1000:.2f} ms (mock transport)')
