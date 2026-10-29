#!/usr/bin/env python3
"""Prepare a local, checksummed Arch build directory; never install packages."""
# Allow direct execution without installing developer tools.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import scripts  # source-package bootstrap
from pathlib import Path
import hashlib,sys,tarfile
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from logi_center.version import VERSION
destination=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path('/tmp/logi-center-arch-build')
destination.mkdir(parents=True,exist_ok=True)
version=VERSION;archive=destination/('logi-center-'+version+'.tar.gz')
if archive.exists() or (destination/'PKGBUILD').exists():raise SystemExit('Choose an empty build directory; existing outputs are preserved.')
from scripts.source_manifest import source_files
files=source_files()
with tarfile.open(archive,'w:gz') as output:
    for name in sorted(set(files)):output.add(root/name,arcname='logi-center-'+version+'/'+str(name),recursive=False)
checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
recipe=(root/'packaging/arch/PKGBUILD').read_text().replace("sha256sums=('SKIP')", "sha256sums=('"+checksum+"')")
(destination/'PKGBUILD').write_text(recipe)
print('Prepared:',destination)
print('Source SHA-256:',checksum)
print('Build with makepkg in this directory. Nothing was installed.')
