# Optional Qt Quick interface

The experimental Qt frontend is launched with `python app.py --ui qml`;
`python app.py` and `--ui gtk` continue to launch GTK. Use `--simulate` for
isolated virtual devices. The current Qt shell is read-only and does not yet
have mouse, keyboard, audio, profile, backup or restore feature parity.

## Runtime and licensing

Application code and original generic PNG/SVG illustrations remain MIT licensed. The current offline layered 2D pipeline and asset manifest are documented in docs/illustration-pipeline.md; no renderer code is required at runtime.
The optional binding is PySide6; Qt Quick, Qt Quick Controls, Qt Quick Layouts
and Qt QML are in Qt Declarative, while QML SVG rendering uses Qt SVG. These
dependencies are not copied into the application tree and are not relicensed as
MIT. Qt for Python and Qt modules are available under LGPLv3/GPLv3 or commercial
terms depending on component/build; users and packagers must follow the license
of the installed Qt build. Arch provides the `pyside6` runtime and the separate
`qt6-svg` package. Refer to the official [Qt for Python licensing and
distribution documentation](https://doc.qt.io/qtforpython-6/) and the Arch
[PySide6 package](https://archlinux.org/packages/extra/x86_64/pyside6/) and
[Qt SVG package](https://archlinux.org/packages/extra/x86_64/qt6-svg/).

No third-party fonts are bundled; the GUI uses system fonts. Original generic
device illustrations are listed in
[`qml_ui/assets/devices/SOURCES.md`](../qml_ui/assets/devices/SOURCES.md).

## Verification

`scripts/qml_smoke.py` runs the simulation UI with Qt's offscreen platform if
PySide6 is installed. An offscreen smoke is not a replacement for live Wayland
validation. GTK remains the default until [`qml-parity.md`](qml-parity.md) is
complete.
