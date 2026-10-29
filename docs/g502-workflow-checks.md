# G502 verification output

```text
G502 editor/artwork verification, 2026-10-28

python scripts/check.py

----------------------------------------------------------------------
Ran 446 tests in 27.694s

OK

Targeted pre-check: python -m unittest -q test_g502_workflow test_mouse_editor test_qml_editor test_device_artwork test_backend test_device_service test_qml_translations
Ran 103 tests in 0.431s
OK

python scripts/qml_smoke.py
QML fonts loaded: display='Noto Sans', data='JetBrainsMono Nerd Font'
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.
PASS: qmllint accepted the QML pages and Theme module.

Focused fake-I/O QML functional matrix:
Dashboard, top/side, wired/wireless, macro library, lighting; RU/EN 640x780 and 1280x800.
All 11 native button IDs clicked through both labels and anchors.
QML fonts loaded: display='Noto Sans', data='JetBrainsMono Nerd Font'
PASS: mouse DPI/cache readback, macro, Ace68 selected key/device readback, audio/server readback, diagnostics; no real I/O.
Migration mock timings: {"mouse_open_ms": 357.9}
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.

GSETTINGS_BACKEND=memory python scripts/gui_smoke.py (host session)
GUI smoke: no writes/capture; editor, language, dialogs and cancellation passed

GSETTINGS_BACKEND=memory python scripts/simulation_smoke.py (host session)
Simulation GTK smoke: 15 scenarios; real CLI never called; no capture

Environment limits:
The sandboxed GTK simulation could not initialize Gtk. The approved host-session run above passed.
GSETTINGS_BACKEND=memory python scripts/peripheral_smoke.py:
RuntimeError: Widget snapshot not ready: dashboard-1000 (realized=True, mapped=True, visible=True, size=1000x780)
The snapshot-gated script did not complete. No blind retry or renderer/workspace changes.

Packaging:
bash -n packaging/arch/PKGBUILD: exit 0
Prepared: /tmp/logi-center-arch-build-g502-svg-20261028
Source SHA-256: e7cd2041aff05c61a858f705c555b9489aa689d870a9ba62cbf6d15b36422b9e
Build with makepkg in this directory. Nothing was installed.

No packages installed or published. No real hardware write tests.

Final narrow recorder check (640 px window) and top/side toggle click check:
QML fonts loaded: display='Noto Sans', data='JetBrainsMono Nerd Font'
PASS: mouse DPI/cache readback, macro, Ace68 selected key/device readback, audio/server readback, diagnostics; no real I/O.
Migration mock timings: {"mouse_open_ms": 325.2}
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.
QML fonts loaded: display='Noto Sans', data='JetBrainsMono Nerd Font'
PASS: mouse DPI/cache readback, macro, Ace68 selected key/device readback, audio/server readback, diagnostics; no real I/O.
Migration mock timings: {"mouse_open_ms": 346.9}
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.

Final targeted tests:
----------------------------------------------------------------------
Ran 35 tests in 0.179s

OK

Queued profile change regression check:
----------------------------------------------------------------------
Ran 68 tests in 0.344s

OK
```
