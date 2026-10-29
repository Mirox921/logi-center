# G502 button overlay, 2026-10-28

The 11 native IDs, normalized SVG anchors and original 12×12 click targets
are unchanged. No controller, remapping, profile or hardware code changed.

Inactive visible dots are now 4 px at 38% opacity, hover dots 7 px, and the
selected dot 9 px in amber. Inactive connectors are hidden. Hover shows a
light connector at 78% opacity; the selected connector remains solid amber.
Dot/connector transitions use the existing Theme.motion (170 ms, zero with
reduced motion). Hovering a named callout also highlights its marker/line.
A graphite tooltip displays the existing localized button name after 300 ms.

Connectors use orthogonal segments with separate ordered side gutters. Wheel
press exits above the wheel markers and left tilt below them, avoiding shared
stems through neighbouring targets. Side-view routes go above/below the SVG.
Every route point is bounded inside the diagram, which clips its drawing.
The actual marker/hitbox centres stay at the existing physical button anchors;
spacing improves through smaller visible dots and separated connector stems.
A shared Canvas paints the active routes; animation/hover is local QML state.

## Verification

QML functional smoke checks every native label and hit target in top/side and
wired/wireless variants, RU/EN, at 640×780 and 1280×800. It asserts original
12×12 targets, bounded orthogonal routes, idle connector opacity, hover/leave
transitions, tooltip names, and unchanged selection/dirty count/write count
after real QTest mouse-move events. All backend writes go to fixtures; the
real runner is forbidden. HiDPI checks repeat top/side at 200% with a stricter
32 MiB decoder budget. 19 related unit tests plus QML/qmllint pass.

The initial visual review found the default white tooltip too conspicuous;
it was changed to the local graphite tooltip. Final selected/hover screenshots
were opened, including the narrow English top view. The selected amber wheel
line and hovered tilt line remain separate and other lines are absent. Native
Wayland/compositor behaviour was not retested for this local overlay change.

Screenshots: `docs/screenshots/g502-overlays/`. Earlier clutter baseline:
`docs/screenshots/g502-svg-compatibility/buttons-100.png`. Source/package
contents were prepared without installation.

## Actual output

### Unit tests

```text
----------------------------------------------------------------------
Ran 19 tests in 0.186s

OK
```

### QML/qmllint

```text
QML fonts loaded: display='Noto Sans', data='JetBrainsMono Nerd Font'
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.
PASS: qmllint accepted the QML pages and Theme module.
```

### Functional 100%

```text
QML fonts loaded: display='Noto Sans', data='JetBrainsMono Nerd Font'
PASS: mouse DPI/cache readback, macro, Ace68 selected key/device readback, audio/server readback, diagnostics; no real I/O.
Migration mock timings: {"mouse_open_ms": 303.0}
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.
```

### Functional 200%

```text
QML fonts loaded: display='Noto Sans', data='JetBrainsMono Nerd Font'
PASS: mouse DPI/cache readback, macro, Ace68 selected key/device readback, audio/server readback, diagnostics; no real I/O.
Migration mock timings: {"mouse_open_ms": 299.1}
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.
```

## DPI-down anchor correction

The user requested more separation from DPI+. Native button 6 (DPI−) moved
from y=214/680 to y=240/680, onto the lower top-button face. Its x coordinate,
12×12 target size, native ID and assignments stay unchanged; DPI+ stays put.
The left wheel-tilt exit now follows the lower DPI anchor plus clearance,
preserving ordered routes when both connectors are active.

The QML hover review now selects DPI+ and hovers DPI−. The screenshot was
opened: `docs/screenshots/g502-overlays/dpi-spacing.png`. RU/EN 640/1280 px
checks passed for both connection variants; 25 relevant unit tests and
QML/qmllint passed. Hover remained read-only and all 11 click targets passed.
