# G502 SVG decoding budget, 2026-10-28

## Cause and correction

The failure was reproduced before the patch with `QT_SCALE_FACTOR=2 python
scripts/qml_smoke.py`: three hidden G502 panels attempted to decode
`diagrams/generic.svg` and reported `Unable to read image data`. The static
G502 panel existed even for non-G502/empty selections. Its sourceSize used
twice the 1103×2048 viewBox, independent of the displayed preview. Combined
with HiDPI and the different fallback aspect ratio, this inflated SVG
rasterization rather than merely enlarging the image on screen.

The source is now empty when the panel is hidden, is not a G502 editor, or
has no usable layout. The requested width follows displayed width/DPR and
is capped at 1024; height is derived by the SVG decoder. A single requested
dimension also avoids mixing top/side aspect ratios while QML bindings settle
during view changes. Minimum requested width is 8 to avoid rounding a shallow
SVG to zero height. The default Qt allocation limit is unchanged.

Qt documents the distinction between display geometry and decoding size in
[Image.sourceSize](https://doc.qt.io/qt-6/qml-qtquick-image.html#sourceSize-prop).
No supplied SVG, button mapping, hardware setting or global Qt configuration
was changed.

## Regression checks

Functional checks cover Dashboard, both G502 views/connection variants and
the K7 editor after switching away from G502. Hidden G502 image sources must
be empty, active images must decode, requested width must be bounded, aspect
ratio must remain correct, and all 11 labels/hit targets remain clickable.
RU/EN and 640/1280 logical px are covered. 100/125/150/200% checks use the
stricter process-local `QT_IMAGEIO_MAXALLOC=32`, rather than raising the
production 256 MiB limit. The 200% regression is now a dedicated CI step.
The full suite was not repeated for this localized QML change.

Representative images were opened: `docs/screenshots/g502-svg-memory/`.
The supplied top/side art and connector placement are preserved. The
offscreen software-renderer captures at 200% omit some existing Shape frame
layers; CutFrame/design tokens were not changed in this decoding fix.

## Portal warning

The real Wayland simulation smoke was run with the inherited `gtk3` platform
theme and memory GSettings. It passed without reproducing the reported
portal message. Qt's separate host-portal registration is in
[QDesktopUnixServices](https://github.com/qt/qtbase/blob/6.10/src/gui/platform/unix/qdesktopunixservices.cpp).
Its exact cause on the user's real-device startup remains unconfirmed. No
portal disable flag, service restart, log suppression or desktop change was
introduced. This test makes no claim about every native file-dialog action.

## Actual output

Before (200%, unpatched):
```text
QML warning: file://qml_ui/qml/G502ButtonPanel.qml:89:21: QML QQuickImage*: Error decoding: file://qml_ui/assets/diagrams/generic.svg: Unable to read image data
QML warning: file://qml_ui/qml/G502ButtonPanel.qml:89:21: QML QQuickImage*: Error decoding: file://qml_ui/assets/diagrams/generic.svg: Unable to read image data
QML warning: file://qml_ui/qml/G502ButtonPanel.qml:89:21: QML QQuickImage*: Error decoding: file://qml_ui/assets/diagrams/generic.svg: Unable to read image data
QML fonts loaded: display='Noto Sans', data='JetBrainsMono Nerd Font'
PASS: qmllint accepted the QML pages and Theme module.
```

100%:
```text
QML fonts loaded: display='Noto Sans', data='JetBrainsMono Nerd Font'
PASS: mouse DPI/cache readback, macro, Ace68 selected key/device readback, audio/server readback, diagnostics; no real I/O.
Migration mock timings: {"mouse_open_ms": 308.1}
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.
```

125%:
```text
QML fonts loaded: display='Noto Sans', data='JetBrainsMono Nerd Font'
PASS: mouse DPI/cache readback, macro, Ace68 selected key/device readback, audio/server readback, diagnostics; no real I/O.
Migration mock timings: {"mouse_open_ms": 360.0}
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.
```

150%:
```text
QML fonts loaded: display='Noto Sans', data='JetBrainsMono Nerd Font'
PASS: mouse DPI/cache readback, macro, Ace68 selected key/device readback, audio/server readback, diagnostics; no real I/O.
Migration mock timings: {"mouse_open_ms": 401.5}
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.
```

200%:
```text
QML fonts loaded: display='Noto Sans', data='JetBrainsMono Nerd Font'
PASS: mouse DPI/cache readback, macro, Ace68 selected key/device readback, audio/server readback, diagnostics; no real I/O.
Migration mock timings: {"mouse_open_ms": 351.8}
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.
```

QML/qmllint:
```text
QML fonts loaded: display='Noto Sans', data='JetBrainsMono Nerd Font'
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.
PASS: qmllint accepted the QML pages and Theme module.
```

Wayland / gtk3:
```text
QML fonts loaded: display='Noto Sans', data='JetBrainsMono Nerd Font'
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.
```

Targeted unit tests:
```text
----------------------------------------------------------------------
Ran 18 tests in 0.214s

OK
```
