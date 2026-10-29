#!/usr/bin/env python3
"""Reproducible Qt-compatible SVG derivative; original user vector is preserved."""
from pathlib import Path
import xml.etree.ElementTree as E
SVG='{http://www.w3.org/2000/svg}'


def compatible(raw):
    root=E.fromstring(raw)
    if root.get('viewBox')!='150 20 250 485':raise ValueError('Unexpected S9 artwork canvas')
    for child in list(root):
        if not child.tag.startswith(SVG):root.remove(child)
    for node in root.iter():
        if node.tag==SVG+'clipPath':
            node.tag=SVG+'mask';node.attrib.pop('clipPathUnits',None)
            node.attrib.update(x='150',y='20',width='250',height='485',maskUnits='userSpaceOnUse',maskContentUnits='userSpaceOnUse')
            for shape in node:
                shape.set('fill','white');shape.set('stroke','none')
        if 'clip-path' in node.attrib:node.set('mask',node.attrib.pop('clip-path'))
    defs=root.find(SVG+'defs')
    mask=E.SubElement(defs,SVG+'mask',dict(id='qt-viewport',x='150',y='20',width='250',height='485',maskUnits='userSpaceOnUse',maskContentUnits='userSpaceOnUse'))
    E.SubElement(mask,SVG+'rect',dict(x='150',y='20',width='250',height='485',fill='white'))
    drawings=[c for c in root if c.tag!=SVG+'defs'];wrapper=E.SubElement(root,SVG+'g',{'mask':'url(#qt-viewport)'})
    for child in drawings:root.remove(child);wrapper.append(child)
    E.register_namespace('',SVG[1:-1])
    return b'\n'.join(line.rstrip() for line in E.tostring(root,encoding='utf-8',xml_declaration=True).splitlines())+b'\n'


if __name__=='__main__':
    folder=Path(__file__).resolve().parents[1]/'qml_ui/assets/devices/exact'
    (folder/'eweadn-s9.svg').write_bytes(compatible((folder/'eweadn-s9-original.svg').read_bytes()))
