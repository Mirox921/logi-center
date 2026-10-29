# Logi Center v0.5.1 — Qt6/QML

29 October 2026

Logi Center now launches Qt6/QML by default and ships a single QML interface.
The GTK presentation is removed from the current application; the public v0.4.0
release remains in Git history and the exact pre-cutover baseline is retained
in a separately verified local backup. Shared device services, adapters, drafts and backup formats are retained.

The v0.5.0 candidate was not published as a release: CI uncovered a legacy
Dashboard QA callback incompatibility. v0.5.1 corrects that fixture, adds a
regression test, and declares Cairo/headless Qt CI dependencies. The existing
v0.5.0 tag is retained; published tags/history are not rewritten.

## Highlights

- Graphite/amber Dashboard, responsive device editors and native QML backups.
- G502 HERO supplied SVGs shared across Dashboard and top/side button views;
  all 11 native IDs retained, clearer hover/selection overlays and profile-state
  handling. Native static/off/cycle/breathing parameters are capability-driven.
- Separate macro capture window and private reusable library; input is consumed
  locally while recording so Space and clicks do not activate other UI controls.
- Expanded K7 Ultra DPI/button/sensor/dock panels and Ace68-II keyboard editors,
  preserving model/firmware restrictions, RMW masks and readback guards.
- G515 scoped Solaar settings, RGB/per-key editors and availability correction:
  disabled RGB ownership does not make the whole device unavailable.
- Model-verified EWEADN S9 protocol adapter and supplied vector artwork;
  native macro-bank upload remains blocked without a safe read/rollback path.
- Audio endpoints, microphone controls/tests, EasyEffects import/presets,
  diagnostics, selective restore and private safety snapshots use shared services.
- RU/EN, reduced motion and persistent QML scale 75–200% after restart.
- English live Wayland screenshots and a lean repository/source archive.
  2241 generated historical screenshots no longer occupy the current Git tree;
  history, local archives and the four real test fixtures are preserved.

## Hardware evidence and limitations

The user physically confirmed G502 LED 1 Color Cycle, period 8000 ms,
brightness 255: continuous animation persists after closing Logi Center.
This does not certify breathing, all zones/speeds, reboot persistence or G HUB parity.

K7/Ace68 selected reversible tests and dock observations retain their exact
scope in device reports. New native sensor/key-bank paths are not all physically
verified. During the recent live read-only check, the K7 receiver was present
but returned an empty mouse identity reply; the editor now reports this state
with a wake/retry hint instead of hiding the error. No reset or profile recovery
is performed automatically.

S9 is protocol/mock-tested without a physical S9 in this environment. G515
availability is regression-tested, but the current machine lacks that keyboard.
No universal model/firmware certification is claimed. ckb-next remains detection-only;
unknown/unsupported features stay disabled. See [backend support](backend-support.md)
and [action-level verification](qml-parity.md).

## Install or upgrade

The release source is not a bundled AppImage. Install Python, PyYAML, PyGObject
(for shared Gio/GLib D-Bus readers), PySide6, Qt Quick/Controls and SVG;
Wayland additionally needs its Qt platform plugin. GTK4/libadwaita are no longer
application dependencies. Optional hardware backends are installed separately.

From the extracted source:

```sh
python app.py --version
python app.py
python install.py
```

**Rerun `python install.py` after updating source** if you launch from the
application menu: that launcher uses the installed copy, not your checkout.
Preferences, drafts, artwork and private backup files are preserved.
`--ui qml` remains compatible; `--ui gtk` directs you to the archived baseline.

The attached Arch package is built locally; clean-machine installation and
all optional-backend combinations are not certified. It was not installed into
this system during release preparation. Verify attached files with `SHA256SUMS`.

## Verification

See [release validation](release-validation-v0.5.1.md) for exact tests, packaging,
screenshot capture and hardware boundaries. Mock writes are not physical tests.
No physical settings or microphone recordings were changed to prepare this release.
