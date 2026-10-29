# G502 top SVG compatibility fix

The uploaded source SVG renders correctly in librsvg, but Qt ignored its
clip paths and rendered rgba gradient stops black. This caused the rectangular
upper background and missing button shading in the Dashboard and editor.
The prior allocation fix remains necessary and unchanged; it did not address
these SVG feature differences. My earlier attribution to intended dark artwork
was incorrect. [Qt's documented support table](https://doc.qt.io/qt-6.10/topics-vectorimageformats.html)
explicitly excludes clip paths and supports masks in the software rasterizer.

## Implementation

- Original four supplied SVGs remain byte-identical, including the originals
  in Downloads. Two generated top-view SVGs are separate production copies.
- `scripts/prepare_g502_svg.py` preserves all original path data and transforms,
  converts known user-space clip regions into equivalent white/even-odd masks,
  and converts opaque rgba stops into identical rgb values. The outer page
  mask is necessary to retain coloured text/details in Qt's group compositing.
- No raster embedding/tracing, hardware logic, profiles or assignments change.
  Canvas dimensions and all 11 native anchors remain the same.
- Models manifest and mouse artwork metadata route Dashboard and editor to
  the compatible copies. Supplied side-view SVGs remain unchanged.
- Installer, CI and Arch resource checks include both new assets. The offline
  generator/check scripts and reference renders are included in source archives.

## Review and regression coverage

`docs/screenshots/g502-svg-compatibility/before-after.png` compares the old Qt
render, the original rendered in librsvg, and the corrected Qt render. Final
Dashboard and button screenshots were opened and reviewed. The broad rectangle
is absent, main buttons have gradients, the cyan LC mark and indicators remain.

The render check compares transparent contours with an independent librsvg
reference, allowing one pixel of antialiasing at contours/viewport boundaries.
It checks transparent front-corner pixels, two grayscale material samples and
coloured detail coverage; it detects both original failures and the lost-colour
case from an unbounded masked group. Current output: outside=0, missing=0
within the tolerance region for both wired and wireless variants. Minor Qt
viewport-edge antialiasing remains within the one-pixel allowance.

Functional fake-I/O tests cover RU/EN, 640/1280 px, top/side, wired/wireless,
Dashboard and all 11 labels/anchors at 100% and 200%, with the stricter local
32 MiB decoder limit. No physical writes. No full-suite repeat for this
localized artwork change.

### Qt SVG render check

```text
PASS: wired: transparent contour, gradients and coloured details; outside=0, missing=0
PASS: wireless: transparent contour, gradients and coloured details; outside=0, missing=0
```

### Targeted unit tests

```text
----------------------------------------------------------------------
Ran 80 tests in 0.352s

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
Migration mock timings: {"mouse_open_ms": 370.2}
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.
```

### Functional 200%

```text
QML fonts loaded: display='Noto Sans', data='JetBrainsMono Nerd Font'
PASS: mouse DPI/cache readback, macro, Ace68 selected key/device readback, audio/server readback, diagnostics; no real I/O.
Migration mock timings: {"mouse_open_ms": 354.4}
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.
```
