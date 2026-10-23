#!/usr/bin/env python3
"""Prepare a local, checksummed Arch build directory; never install packages."""
from pathlib import Path
import ast,hashlib,shutil,sys,tarfile
root=Path(__file__).resolve().parents[1]
destination=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path('/tmp/logi-center-arch-build')
destination.mkdir(parents=True,exist_ok=True)
version='0.4.0dev';archive=destination/('logi-center-'+version+'.tar.gz')
if archive.exists() or (destination/'PKGBUILD').exists():raise SystemExit('Choose an empty build directory; existing outputs are preserved.')
tree=ast.parse((root/'install.py').read_text())
modules=next(node.iter.elts for node in tree.body if isinstance(node,ast.For) and isinstance(node.target,ast.Name) and node.target.id=='filename')
files=[Path(ast.literal_eval(item)) for item in modules]
files += [p.relative_to(root) for p in root.glob('test_*.py')]
files += [p.relative_to(root) for p in (root/'docs').rglob('*') if p.is_file() and p.suffix in ['.md','.png']]
files += [Path('packaging/arch/README.md'),Path('packaging/udev/70-logi-center-mchose.rules')]
files += [Path(name) for name in ['install.py','LICENSE','README.md','README.ru.md','packaging/logi-center.desktop','packaging/icons/logi-center.svg']]
with tarfile.open(archive,'w:gz') as output:
    for name in sorted(set(files)):output.add(root/name,arcname='logi-center-'+version+'/'+str(name),recursive=False)
checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
recipe=(root/'packaging/arch/PKGBUILD').read_text().replace("sha256sums=('SKIP')", "sha256sums=('"+checksum+"')")
(destination/'PKGBUILD').write_text(recipe)
print('Prepared:',destination)
print('Source SHA-256:',checksum)
print('Build with makepkg in this directory. Nothing was installed.')
