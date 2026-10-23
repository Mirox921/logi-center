# Universal peripheral manager progress

Baseline: v0.3.0, clean tree, 69 hardware-free tests. Existing operation/backup/audio/event modules retained.

Audit: ratbag mouse CLI mostly vendor-independent; UI action types and layouts are partially model-specific. G515 Solaar controls/backup/ping and header batteries are hardcoded. Audio volumes already generic but labels rewrite model names. Whole-page refresh loses drafts. Backups select categories only. Diagnostics lacks device capability inventory/export. No Arch package.

Plan (dependency order):
1. Private persistent drafts + conflict handling; extend typed operation statuses and backup selection.
2. Capability/evidence model, adapter registry, identity-safe device manager, read-only HID/input and generic audio/headset providers; retain G515 isolated control path.
3. Integrate universal inventory/capability presentation, keyboard read-only layout where no write protocol, generic battery/audio names, explicit simulation mode.
4. Redacted JSON diagnostics preview/export, per-setting restore comparison.
5. Arch packaging, regression/GUI/simulation checks, documentation and measured timing.

Constraints: no raw guessed HID writes, full Solaar enumeration on startup, package installation, system permission change, physical unplug/reboot/audio capture, AUR publication or release/push. Missing keyboard programmable/per-key backend is a reported limitation, not a fabricated capability.

Implemented increments:
- drafts.py: private atomic JSON store, base/desired distinction, conflict detection, submitted-vs-confirmed state. GTK choices/audio volume/mouse lighting and macro/assignment drafts bind to it; per-page signatures avoid unnecessary rebuilds.
- devices.py: explicit capabilities/evidence + adapter registry and exact/uniqueness-guarded physical identity merge. Lazy ratbag detail avoids scanning every mouse on startup; Input/Pulse/HeadsetControl/local Solaar providers. Unknown functions stay unknown, never guessed.
- solaar_adapter.py: explicitly requested individual saved scalar probes; only backend-enumerated choices become writable, with parameter-specific uncached readback through isolated Solaar wrapper. Complex/per-key protocols remain unavailable.
- reports.py: allowlisted previewable JSON without setting values/macros/serials/physical paths. Per-setting restore current/desired/ID comparison and selection retains v1 backups.
- device_ui.py/keyboard_ui.py: shared capability inventory, generic keyboard reference diagram and preserved G515 path. Real kernel batteries from any manufacturer, real audio names and one hardware sidetone control. Simulation has 8 explicit scenarios and no real I/O.
- 88 unit tests pass; real and simulation GTK smoke passed at intermediate revisions; final integration pending. Arch source preparation and makepkg check() pass; package build ongoing. No physical writes/capture, package install or publication.

Integration review:
- Generic scalar controls now use provider-owned Plan factories and re-resolve current capabilities immediately before a write. Merged records retain each backend's selector; headset commands cannot accidentally target an audio endpoint name. No blind write retry/fan-out.
- Input key-mask parser preserves native word boundaries (important for mouse bits above 255). Missing audio fields stay unavailable, not fabricated zero-volume controls. Unavailable headset battery never becomes a negative percentage.
- Solaar reset/firmware/erase/profile-mode settings stay read-only; live probes remain explicit. Settings without enumerated legal values stay read-only. Per-key RGB/remapping is not implemented for hardware without a verified parameter adapter.
- Draft conflict markers persist on controls; macro reset does not erase drafts on other buttons. Generic choice values are language-independent; G515 color/effect drafts included. Private preference writes are atomic.
- Latest: 94 unit tests pass; intermediate real GUI and simulation smoke pass. makepkg --nodeps built a development package and ran 88 tests from its source snapshot; final package will be rebuilt after final edits. namcap unavailable; package not installed.
- Measured: 50 mock mice, eager 151 transport calls / ~2.46 ms vs lazy 1 / ~0.08 ms. Current-host baseline CLI read batch ~0.127 s, additional cached inventory/identity ~0.020 s; these are observations, not universal startup guarantees.

Final safety review:
- ratbagctl's short nickname scheme can collide; duplicate selectors are represented separately and cannot be read/edited through the mouse UI. Every ratbag write rechecks exact unique inventory (no model substring fallback).
- Receiver child /inputN:slot identity is preserved; two keyboards behind one receiver stay distinct. Current app observations are reused only with the same backend target and model, without forging new timestamps.
- Simulation has a separate application ID and window title, preventing redirection into an already running real-device instance.
- 102 tests now pass, including collisions, receiver slots, draft submission state and language-independent choices. Full real GTK and simulation checks passed; final post-review smoke/rebuild follows. Public report generation on current hardware: no discovery faults; no private identities/values exported.

Final source: 103 tests pass. Added embedded-serial report redaction and retained offline documentation/images in the Arch source/package. Runtime/code is frozen for the final package, manifest and GTK checks.

Final verification completed:
- 103 tests OK in source and final makepkg check(); compileall, diff check, shell syntax and desktop validation pass.
- Independent final GUI smoke passes (full generic mouse fixture, macro drafts, offline header, language, JSON diagnostics/restore dialogs and cancelled recording preparation). Final simulation smoke passes with distinct app ID, shared editors and no real CLI/capture.
- Final package: /tmp/logi-center-arch-0.4.0dev/logi-center-0.4.0dev-1-any.pkg.tar.zst; SHA-256 94d7d741c638891dd4f9a0782531673d471f9739b296820faddc5c98ed7885b4. All 22 runtime modules byte-match source; launcher/desktop/icon/offline docs present; no home/etc files. Built with --nodeps; no installation, namcap unavailable.
- Per-user runtime updated and byte-compared; open pre-update window was not terminated to avoid losing old-version unsaved edits. No GitHub/AUR publication. Physical write/restore/reconnect/audio/session tests remain pending; see universal-upgrade.md readiness table.

Device-name search added after the universal upgrade:
- Devices tab has a case-insensitive search entry; whitespace is normalized, an empty-result message appears and backend diagnostics remain visible. Filtering only hides existing groups, preserving controls/drafts. Query survives inventory rebuild and language switch; stale search callbacks are ignored.
- Updated device_ui.py/devices.py/i18n.py and search/GTK checks. 104 unit tests and live GTK smoke pass; no hardware writes/capture. Per-user runtime updated; existing open window is not forcibly closed. The earlier staged Arch package predates this UI addition.

2026-10-23: optional multi-vendor backend cycle implemented; read [backend expansion progress](backend-expansion-progress.md) and [support/limits](backend-support.md). 132 tests, GTK/simulation checks and local Arch build passed; K7 hardware access remains permission-denied. No new physical setting writes tested.
