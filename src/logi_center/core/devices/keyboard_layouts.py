"""Data-only ANSI layouts. Ace68-II labels mirror ace68_adapter.LAYOUT.

Widths, gaps and positions are in units (1u = one key pitch). Shared by QML reference diagrams and the offline renderer; no hardware I/O.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Key:
    label: str
    x: float
    y: float
    width: float = 1
    height: float = 1


@dataclass(frozen=True)
class Layout:
    name: str
    width_u: float
    height_u: float
    size_mm: tuple
    keys: tuple
    row_widths: tuple


def row(labels, widths, y, x=0, height=1):
    keys = []
    for label, width in zip(labels, widths, strict=True):
        keys.append(Key(label, x, y, width, height))
        x += width
    return keys


ALPHA_LABELS = [list('`1234567890-=') + ['Backspace'],
                ['Tab', *list('QWERTYUIOP[]'), '\\'],
                ['Caps', *list("ASDFGHJKL;'"), 'Enter'],
                ['LShift', *list('ZXCVBNM,./'), 'RShift'],
                ['LCtrl', 'Super', 'LAlt', 'Space', 'RAlt', 'Fn', 'Menu', 'RCtrl']]
ALPHA_WIDTHS = [[1] * 13 + [2], [1.5] + [1] * 12 + [1.5],
                [1.75] + [1] * 11 + [2.25], [2.25] + [1] * 10 + [2.75],
                [1.25] * 3 + [6.25] + [1.25] * 4]


def alpha_rows(y=0):
    return [key for index, (labels, widths) in enumerate(zip(ALPHA_LABELS, ALPHA_WIDTHS))
            for key in row(labels, widths, y + index)]


def ace68():
    labels = [['Esc', *list('1234567890'), '-', '=', 'Backspace', '`'],
              ['Tab', *list('QWERTYUIOP'), '[', ']', '\\', 'Del'],
              ['Caps', *list('ASDFGHJKL'), ';', "'", 'Enter', 'PgUp'],
              ['LShift', *list('ZXCVBNM'), ',', '.', '/', 'RShift', 'Up', 'PgDn'],
              ['LCtrl', 'Super', 'LAlt', 'Space', 'RAlt', 'Fn', 'RCtrl', 'Left', 'Down', 'Right']]
    widths = [[1] * 13 + [2, 1], [1.5] + [1] * 12 + [1.5, 1],
              [1.75] + [1] * 11 + [2.25, 1], [2.25] + [1] * 10 + [1.75, 1, 1],
              [1.25] * 3 + [6.25] + [1] * 6]
    return tuple(key for index, (names, sizes) in enumerate(zip(labels, widths))
                 for key in row(names, sizes, index))


def extended(full=False):
    keys = alpha_rows(1.5)
    keys.append(Key('Esc', 0, 0))
    for group, start in enumerate((1.5, 6, 10.5)):
        keys.extend(Key(f'F{group * 4 + i + 1}', start + i, 0) for i in range(4))
    keys.extend(Key(label, 15.5 + i, 0) for i, label in enumerate(('Print', 'Scroll', 'Pause')))
    for r, labels in enumerate((('Insert', 'Home', 'PgUp'), ('Del', 'End', 'PgDn'))):
        keys.extend(Key(label, 15.5 + i, 1.5 + r) for i, label in enumerate(labels))
    keys.append(Key('Up', 16.5, 4.5))
    keys.extend(Key(label, 15.5 + i, 5.5) for i, label in enumerate(('Left', 'Down', 'Right')))
    if full:
        for r, labels in enumerate((('Num', '/', '*', '-'), ('7', '8', '9', '+'),
                                     ('4', '5', '6'), ('1', '2', '3', 'NumEnter'), ('0', '.'))):
            if r == 4:
                keys.extend((Key('0', 19, 5.5, 2), Key('.', 21, 5.5)))
            else:
                keys.extend(Key(label, 19 + i, 1.5 + r, 1, 2 if label in ('+', 'NumEnter') else 1)
                            for i, label in enumerate(labels))
    return tuple(keys)


def laptop():
    keys = [key for key in alpha_rows(.85) if key.y < 4.85]
    for key in row(['LCtrl', 'Super', 'LAlt', 'Space', 'RAlt', 'Fn', 'RCtrl', 'Left', 'Down', 'Right'],
                   [1.25, 1, 1, 5.75, 1, 1, 1, 1, 1, 1], 4.85):
        if key.label == 'Down':
            keys.extend((Key('Up',key.x,key.y,1,.5),Key('Down',key.x,key.y+.5,1,.5)))
        elif key.label in ('Left','Right'):
            keys.append(Key(key.label,key.x,key.y+.5,1,.5))
        else:keys.append(key)
    keys.extend(row(['Esc'] + [f'F{i}' for i in range(1, 13)] + ['Power'], [15 / 14] * 14, 0, height=.7))
    return tuple(keys)


LAYOUTS = {
    # Rows declare (start_y, total_width, intentional_blank_width). Width of
    # vertically spanning Enter/+ keys is counted in both occupied rows.
    '60': Layout('ANSI 60%', 15, 5, (295, 105), tuple(alpha_rows()), tuple((y, 15, 0) for y in range(5))),
    '65': Layout('Ace68-II / ANSI 65%', 16, 5, (315, 105), ace68(), tuple((y, 16, 0) for y in range(5))),
    'tkl': Layout('ANSI TKL', 18.5, 6.5, (360, 140), extended(),
                  ((0, 18.5, 2.5), (1.5, 18.5, .5), (2.5, 18.5, .5),
                   (3.5, 18.5, 3.5), (4.5, 18.5, 2.5), (5.5, 18.5, .5))),
    'full': Layout('ANSI full size', 23, 6.5, (440, 140), extended(True),
                   ((0, 23, 7), (1.5, 23, 1), (2.5, 23, 1), (3.5, 23, 4), (4.5, 23, 3), (5.5, 23, 1))),
    'laptop': Layout('Generic laptop', 15, 5.85, (295, 112), laptop(),
                     tuple((y,15,2 if y==4.85 else 0) for y in (0,.85,1.85,2.85,3.85,4.85,5.35))),
}


def validate_layout(layout):
    errors = []
    for key in layout.keys:
        if key.width <= 0 or key.height <= 0 or key.x < 0 or key.y < 0 or \
           key.x + key.width > layout.width_u + 1e-6 or key.y + key.height > layout.height_u + 1e-6:
            errors.append(f'{key.label}: key outside declared unit bounds')
    for index, a in enumerate(layout.keys):
        for b in layout.keys[index + 1:]:
            if min(a.x + a.width, b.x + b.width) - max(a.x, b.x) > 1e-6 and \
               min(a.y + a.height, b.y + b.height) - max(a.y, b.y) > 1e-6:
                errors.append(f'{a.label}/{b.label}: overlapping key rectangles')
    for y, declared, blank in layout.row_widths:
        occupied = sum(key.width for key in layout.keys if key.y <= y + 1e-6 < key.y + key.height)
        if abs(occupied + blank - declared) > 1e-6 or abs(declared - layout.width_u) > 1e-6:
            errors.append(f'row {y}: occupied {occupied}u + declared gaps {blank}u != {declared}u')
    return errors
