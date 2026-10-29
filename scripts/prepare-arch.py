#!/usr/bin/env python3
"""Prepare a local, checksummed Arch build directory; never install packages."""
from pathlib import Path
import ast,hashlib,shutil,sys,tarfile
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from version import VERSION
destination=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path('/tmp/logi-center-arch-build')
destination.mkdir(parents=True,exist_ok=True)
version=VERSION;archive=destination/('logi-center-'+version+'.tar.gz')
if archive.exists() or (destination/'PKGBUILD').exists():raise SystemExit('Choose an empty build directory; existing outputs are preserved.')
tree=ast.parse((root/'install.py').read_text())
modules=next(node.iter.elts for node in tree.body if isinstance(node,ast.For) and isinstance(node.target,ast.Name) and node.target.id=='filename')
files=[Path(ast.literal_eval(item)) for item in modules]
files += [p.relative_to(root) for p in root.glob('test_*.py')]
files += [p.relative_to(root) for p in (root/'tests/fixtures').rglob('*') if p.is_file()]
files += [Path('mouse_art.py'),Path('AGENTS.md')]
files += [Path('scripts/gui_smoke.py'),Path('scripts/simulation_smoke.py'),Path('scripts/peripheral_smoke.py')]
files += [p.relative_to(root) for p in (root/'qml_ui').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
files += [p.relative_to(root) for p in (root/'illustrations').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
# Ship source tooling, not its generated captures/caches/build products.
files += [p.relative_to(root) for p in (root/'scripts').rglob('*')
          if p.is_file() and p.suffix in ('.py','.qml') and '__pycache__' not in p.parts]
# Unlicensed user-provided reference photos in docs/ are not redistributable
# assets. Only project screenshots and text documentation enter this archive.
files += [p.relative_to(root) for p in (root/'docs').rglob('*') if p.is_file() and
          ((p.suffix=='.md' and (root/'docs/screenshots') not in p.parents) or
           p==root/'docs/screenshots/README.md' or (root/'docs/screenshots/releases') in p.parents and
           p.suffix in ['.png','.json'])]
files += [Path('packaging/arch/README.md'),Path('packaging/arch/PKGBUILD'),Path('packaging/udev/70-logi-center-mchose.rules')]
files += [Path(name) for name in ['install.py','LICENSE','START_HERE.ru.md','README.md','README.ru.md','packaging/logi-center.desktop','packaging/icons/logi-center.svg']]
with tarfile.open(archive,'w:gz') as output:
    for name in sorted(set(files)):output.add(root/name,arcname='logi-center-'+version+'/'+str(name),recursive=False)
checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
recipe=(root/'packaging/arch/PKGBUILD').read_text().replace("sha256sums=('SKIP')", "sha256sums=('"+checksum+"')")
(destination/'PKGBUILD').write_text(recipe)
print('Prepared:',destination)
print('Source SHA-256:',checksum)
print('Build with makepkg in this directory. Nothing was installed.')
