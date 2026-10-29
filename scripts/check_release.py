#!/usr/bin/env python3
"""Check curated release files/links; no network, GUI or hardware access."""
# Allow direct execution without installing developer tools.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import scripts  # source-package bootstrap
from pathlib import Path
import argparse,json,re,struct,subprocess,sys,tarfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from logi_center.version import VERSION


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path)
    args=parser.parse_args()
    assert re.search(r'^pkgver=(.+)$',(ROOT/'packaging/arch/PKGBUILD').read_text(),re.M)[1]==VERSION
    from scripts.source_manifest import runtime_files
    import tomllib
    project=tomllib.loads((ROOT/'pyproject.toml').read_text())
    assert project['project']['scripts']['logi-center']=='logi_center.cli:main'
    assert project['project']['license']=='GPL-3.0-only'
    assert "license=('GPL-3.0-only')" in (ROOT/'packaging/arch/PKGBUILD').read_text()
    assert 'Version 3, 29 June 2007' in (ROOT/'LICENSE').read_text()
    assert (ROOT/'assets/LICENSE-MIT.txt').read_text().startswith('MIT License')
    required=('src/logi_center/cli.py','src/logi_center/resources.py',
              'src/logi_center/qml_ui/qml/Main.qml','assets/mice/models.json',
              'assets/fonts/SOURCES.md','assets/icons/logi-mark.svg')
    for name in required:assert Path(name) in runtime_files(),name
    for name in ('README.md','README.ru.md'):
        text=(ROOT/name).read_text();assert '/releases/tag/v'+VERSION in text
        links=re.findall(r'\]\(([^)]+)\)|(?:src|href)="([^"]+)"',text)
        for values in links:
            link=next(v for v in values if v)
            if '://' not in link and not link.startswith('#'):
                assert (ROOT/link.split('#',1)[0]).exists(),(name,link)
    gallery=ROOT/'docs/screenshots/releases'/('v'+VERSION)
    metadata=json.loads((gallery/'capture.json').read_text())
    assert metadata['language']=='en' and metadata['workspace']==9 and metadata['platform']=='wayland'
    assert 5<=len(metadata['captures'])<=12
    for item in metadata['captures']:
        p=gallery/item['file'];raw=p.read_bytes()
        assert raw[:8]==b'\x89PNG\r\n\x1a\n'
        assert struct.unpack('>II',raw[16:24])==(item['width'],item['height'])
    if (ROOT/'.git').exists():
        files=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
        assert not any(p.startswith(('docs/screenshots/redesign/','.agents/','.codex/')) for p in files)
        assert not any(p.endswith(('.pkg.tar.zst','.pyc')) for p in files)
    if args.archive:
        with tarfile.open(args.archive) as archive:
            names=archive.getnames();prefix='logi-center-'+VERSION+'/'
            assert not any('/screenshots/redesign/' in p or '/.agents/' in p or p.endswith('.pyc') for p in names)
            assert all(p.startswith(prefix) for p in names)
            assert sum('/docs/screenshots/releases/' in p and p.endswith('.png') for p in names)==len(metadata['captures'])
            for name in ('src/logi_center/version.py','scripts/check.py','scripts/check_release.py','packaging/arch/PKGBUILD'):
                assert archive.extractfile(prefix+name).read()==(ROOT/name).read_bytes(),name
    print('PASS: version, runtime manifest, README links and curated English workspace-9 gallery.')


if __name__=='__main__':main()
