#!/usr/bin/env python3
"""Logi Center entry point. Qt Quick is the only in-tree GUI."""
import argparse
import sys
from version import VERSION


def main(argv=None):
    parser=argparse.ArgumentParser(description='Logi Center — Qt6/QML peripheral manager')
    parser.add_argument('--version',action='version',version='Logi Center '+VERSION)
    parser.add_argument('--ui',default='qml',metavar='qml',help='QML interface (default; retained for older launch commands)')
    parser.add_argument('--simulate',action='store_true',help='Use isolated simulated devices')
    parser.add_argument('--smoke',action='store_true',help='Run bounded GUI checks without hardware writes')
    parser.add_argument('--debug-text',action='store_true',help='Log Qt text rendering diagnostics')
    options,qt_args=parser.parse_known_args(argv)
    if options.ui!='qml':
        parser.error('GTK has been archived. Restore the GTK backup to use that version; this build uses QML only.')
    from qml_ui.main import run
    args=[sys.argv[0],*qt_args]
    args += [flag for flag in ('--simulate','--smoke','--debug-text') if getattr(options,flag[2:].replace('-','_'))]
    return run(args)


if __name__=='__main__':
    raise SystemExit(main())
