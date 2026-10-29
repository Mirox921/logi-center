#!/usr/bin/env python3
"""Offline editor schematics, using GTK's canonical geometry and anchor frame."""
# Allow direct execution without installing developer tools.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import scripts  # source-package bootstrap
from pathlib import Path
import re,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cairo
from scripts.artwork.mouse_art import render,WIDTH,HEIGHT

def main():
    directory=Path(__file__).resolve().parents[1]/'assets/mice/diagrams'
    directory.mkdir(exist_ok=True)
    for filename,name in [('g502.svg','G502'),('generic.svg','Generic')]:
        target=directory/filename
        with cairo.SVGSurface(str(target),WIDTH,HEIGHT) as surface:
            render(cairo.Context(surface),WIDTH,HEIGHT,name,count=0,studio=False)
        # A neutral schematic, never a representation of the live RGB value.
        def neutral(match):
            shade=sum(float(v.rstrip('%')) for v in match[1].split(','))/3
            return 'rgb('+','.join(f'{shade:.6f}%' for _ in range(3))+')'
        text=re.sub(r'rgb\(([^)]+)\)',neutral,target.read_text())
        target.write_text(text)

if __name__=='__main__':main()
