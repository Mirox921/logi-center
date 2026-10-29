"""Generate deterministic orthographic layered 2D device PNGs offline."""
import argparse
from pathlib import Path
from .models import ARTWORK_KEYS, build_model
from .render import save_png

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'assets/devices/generated'


def render_all(keys=ARTWORK_KEYS, output=OUT):
    for key in keys:
        model = build_model(key)
        for density in (1, 2):
            target = Path(output) / f'{key.replace("_", "-")}@{density}x.png'
            save_png(model, target, density)
            print(target, flush=True)
            if key == 'unknown' and Path(output).resolve() == OUT.resolve():
                name = 'fallback.png' if density == 1 else 'fallback@2x.png'
                (OUT.parent / name).write_bytes(target.read_bytes())

    from .metadata import write_metadata
    write_metadata(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', nargs='+', choices=ARTWORK_KEYS)
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    render_all(args.only or ARTWORK_KEYS, args.output)


if __name__ == '__main__':
    main()
