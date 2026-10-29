#!/usr/bin/env python3
"""Offline Qt SVG compatibility copies; supplied artwork is never overwritten."""
# Allow direct execution without installing developer tools.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import scripts  # source-package bootstrap
from pathlib import Path
import re
import xml.etree.ElementTree as ET

SVG = '{http://www.w3.org/2000/svg}'
SOURCES = {'g502_transparent_wired.svg':'g502-top-wired-qt.svg',
           'g502_wireless.svg':'g502-top-wireless-qt.svg'}
# The original clip paths explicitly use these rectangles in local coordinates.
REGIONS = {'mouse-silhouette':('-551.5','-1024.5','1103','2048.5'),
           'cord-free-outline':('0','0','1103','2048')}


def compatible(raw):
    root = ET.fromstring(raw)
    if root.get('viewBox') != '0 0 1103 2048':
        raise ValueError('Unexpected G502 source canvas')
    for node in root.iter():
        for key,value in list(node.attrib.items()):
            # All source gradient stops are opaque; preserve their RGB exactly.
            node.set(key,re.sub(r'rgba\((\d+),(\d+),(\d+),1\)',r'rgb(\1,\2,\3)',value))
        if node.tag == SVG+'clipPath':
            region = REGIONS[node.get('id')]
            node.tag = SVG+'mask'
            node.attrib.pop('clipPathUnits',None)
            node.attrib.update(dict(zip(('x','y','width','height'),region)),
                               maskUnits='userSpaceOnUse',maskContentUnits='userSpaceOnUse')
            for shape in node.iter():
                if shape is node:continue
                shape.set('fill','white')
                if 'clip-rule' in shape.attrib:
                    shape.set('fill-rule',shape.attrib.pop('clip-rule'))
        if 'clip-path' in node.attrib:
            node.set('mask',node.attrib.pop('clip-path'))
    defs = root.find(SVG+'defs')
    if defs is None:raise ValueError('Missing SVG definitions')
    # A bounded outer compositing layer preserves text/coloured detail in Qt's
    # nested-mask renderer. It clips only to the existing page, never the mouse.
    viewport = ET.SubElement(defs,SVG+'mask',{'id':'qt-viewport','x':'0','y':'0',
        'width':'1103','height':'2048','maskUnits':'userSpaceOnUse','maskContentUnits':'userSpaceOnUse'})
    ET.SubElement(viewport,SVG+'rect',{'width':'1103','height':'2048','fill':'white'})
    drawings = [node for node in root if node.tag == SVG+'g']
    wrapper = ET.SubElement(root,SVG+'g',{'mask':'url(#qt-viewport)'})
    for drawing in drawings:
        root.remove(drawing);wrapper.append(drawing)
    ET.register_namespace('',SVG[1:-1])
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)+b'\n'


def generate(folder):
    for source,target in SOURCES.items():
        (folder/target).write_bytes(compatible((folder/source).read_bytes()))


if __name__ == '__main__':
    generate(Path(__file__).resolve().parents[1]/'assets/mice')
