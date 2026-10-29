"""Explicit source/runtime boundaries shared by packaging checks and builders."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _files(directory):
    return (p for p in (ROOT / directory).rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')


def runtime_files():
    return sorted({p.relative_to(ROOT) for directory in ('src/logi_center', 'assets')
                   for p in _files(directory)})


def source_files():
    paths = set(runtime_files())
    for directory in ('scripts', 'tests', 'packaging'):
        paths.update(p.relative_to(ROOT) for p in _files(directory)
                     if p.suffix in ('.py', '.qml', '.png', '.md', '.svg', '.desktop', '.rules')
                     or p.name == 'PKGBUILD')
    for p in _files('docs'):
        relative = p.relative_to(ROOT)
        if ((p.suffix == '.md' and 'screenshots' not in relative.parts)
                or relative == Path('docs/screenshots/README.md')
                or str(relative).startswith('docs/screenshots/releases/') and p.suffix in ('.png', '.json')):
            paths.add(relative)
    paths.update(Path(name) for name in (
        'setup.py', 'AGENTS.md', 'app.py', 'install.py', 'pyproject.toml', 'MANIFEST.in',
        'LICENSE', 'README.md', 'README.ru.md', 'ROADMAP.md', 'START_HERE.ru.md'))
    return sorted(paths)
