# Qt Quick interface

Qt6/QML is the default and only in-tree GUI. Launch with `python app.py`
or `logi-center` after installation; `--ui qml` remains compatible. Use
`--simulate` for isolated virtual devices. GTK recovery is documented in
[qml-cutover.md](qml-cutover.md). Implementation/physical-validation limits
remain tracked in [qml-parity.md](qml-parity.md).

The package, resource paths and development commands are documented in
[development/architecture.md](development/architecture.md).

## Runtime and licensing

Application code is licensed under GNU GPL v3.0 only (`GPL-3.0-only`); see
[LICENSE](../LICENSE). Original generic PNG/SVG illustrations keep their separate
MIT license in [assets/LICENSE-MIT.txt](../assets/LICENSE-MIT.txt). The current offline layered 2D pipeline and asset manifest are documented in docs/illustration-pipeline.md; no renderer code is required at runtime.
The required binding is PySide6; Qt Quick, Qt Quick Controls, Qt Quick Layouts
and Qt QML are in Qt Declarative, while QML SVG rendering uses Qt SVG. These
dependencies are not copied into the application tree and retain their original licenses. Qt for Python and Qt modules are available under LGPLv3/GPLv3 or commercial
terms depending on component/build; users and packagers must follow the license
of the installed Qt build. Arch provides the `pyside6` runtime and the separate
`qt6-svg` package. Refer to the official [Qt for Python licensing and
distribution documentation](https://doc.qt.io/qtforpython-6/) and the Arch
[PySide6 package](https://archlinux.org/packages/extra/x86_64/pyside6/) and
[Qt SVG package](https://archlinux.org/packages/extra/x86_64/qt6-svg/).

Bundled font sources/licenses are listed in
[assets/fonts/SOURCES.md](../assets/fonts/SOURCES.md). Original generic
device illustrations are listed in
[assets/devices/SOURCES.md](../assets/devices/SOURCES.md).

## Verification

`scripts/qml_smoke.py` runs the simulation UI with Qt's offscreen platform if
PySide6 is installed. An offscreen smoke is not a replacement for live Wayland
validation. Automated simulation does not certify physical hardware support.
