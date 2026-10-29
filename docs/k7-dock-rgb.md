# K7 Ultra integrated charging dock RGB

## Physical observation, 2026-10-28

The user explicitly agreed to observe one three-second static-red trial.
`scripts/k7_rgb_trial.py --confirm K7-STATIC-RED-RESTORE --seconds 3` saved a
private snapshot, sent one native RGB record, read it back, restored the exact
original 15-byte record and verified restoration. The user confirmed that the
**dock strip** turned red and then returned to its previous battery-level
lighting. Thus this K7 receiver command targets the integrated dock, not the
mouse's top charging or underside DPI LEDs. Only static red and restoration of
this original mode have been optically verified in this test.

A subsequent read through the new SDK dock route reported `battery`, brightness
100 and stored RGB `[0, 255, 0]`. That RGB value is a stored parameter, not a
measurement of the strip's current battery-dependent color. Reading the
receiver RGB record works while the paired mouse is asleep. Writes continue
to require the exact connected K7 logical identity.

## Official source and supported fields

The official [M HUB](https://www.mchose.com.cn/) K7 `lightSetting` component was
inspected on 2026-10-28 in
`https://www.mchose.com.cn/assets/purify.es-D9IeuU3Y.js`.
SHA-256: `2b223ad993a4da4694dce52e63ecbb28e6b57c7c7b0053224b182f91b6efcd27`.
The downloaded bundle is research material in `/tmp`, not a runtime dependency
or a copied application asset. Its K7 path is distinct from MagDock 3837:1012.

| Mode | Native effect ID | Parameters exposed by the K7 panel | Physical status |
|---|---|---|---|
| Battery level | 1 | Brightness | Existing mode restored and observed |
| Breathing | 2 | Color, brightness | Protocol from M HUB; animation unverified |
| Flash away | 3 | Color, brightness, duration 0–2 | Protocol from M HUB; unverified |
| Color cycle | 4 | Brightness | Protocol from M HUB; animation unverified |
| Stars | 5 | Color, brightness, duration 0–2 | Protocol from M HUB; unverified |
| Static | 6 | Color, brightness | Static red at brightness 100 observed |
| Waves | 7 | Brightness, direction 0/1 | Protocol from M HUB; unverified |
| Off | Enable byte 0 | None | Protocol from M HUB; unverified |

Brightness is 0–100. Duration indices 0/1/2 mean short/medium/long; no physical
time unit is known. Wave direction is 0 clockwise / 1 counterclockwise. The
dedicated K7 panel provides no verified general animation-speed slider for
breathing/cycle/waves. Music (ID 0) uses host-generated updates and is not
implemented. Native effects require no application animation loop, but their
persistence after closing Logi Center has not been optically checked.

## Backend behavior

The existing MCHOSE transport reads report 0x11 / command 0x1B and writes its
15-byte record once through command 0x2B. New host-side validation carries the
exact expected original record; a concurrent change aborts before writing.
Changes are composed into one report, preserving the remaining bytes. Color
updates both triplets, as M HUB does. Native mode selection clears the host
independent/random-light flags according to the K7 panel. Firmware/reset,
pairing, mouse configuration, DPI, buttons and macros are not addressed by
this operation. A private pre-write RGB snapshot is retained.

Requested-field readback produces confirmed/mismatch/error states through the
existing Plan/perform services. Unrequested field drift is an error. A matching
record is not optical confirmation; no retry loop or software animation was
introduced. Sensor-flag write restrictions remain in place.

Verification: 50 targeted tests across `test_k7_dock`, `test_k7_rgb_trial` and
`test_backend_expansion` passed with in-memory transports. The real SDK dock
read succeeded. The first real SDK attempt required an awake logical mouse;
the corrected read-only receiver route now works independently of mouse sleep.
No physical dock write beyond the explicitly observed red/restoration trial
was performed during backend development.

## QML integration

`K7DockPanel.qml` follows the user's M HUB composition with the application's
graphite surfaces, chamfered frames, typography and restrained amber states.
The original `k7-dock.svg` is a reference-informed editable vector with no
manufacturer bitmap or logo. Its separate RGB strip is a draft preview, not
optical feedback. The battery gradient is a schematic guide; firmware chooses
the actual color and thresholds.

The shared `dock_lighting` capability supplies effect, enabled state, brightness,
color, duration and direction. `control_service.dock_controls` supplies ordinary
editor descriptors; the existing DraftStore, Apply/Cancel, executor, epoch and
readback paths are reused. One Apply composes all applicable changes into one
native RGB report. Readback uses the receiver's light record, and a successful
Apply performs a targeted settings read rather than a device rescan. Switching
lighting off preserves the selected native effect for later re-enabling.
Music is explained as unavailable; no host animation loop is started.

At desktop width the vector is left of the effect and parameter cards. At
640 px, controls and the lighting switch precede the preview. The device
passport is compact only while editing the dock, so the relevant controls fit
without changing other device pages. RU and EN use the existing translation
service. Existing GTK controls remain available.

Visual review: initial captures exposed a QML `state` binding collision that
hid the static color control, and a preview-first narrow layout that pushed
settings below the viewport. Both were corrected; narrow/desktop captures then
showed correct color preview and accessible controls. A second small correction
moved the lighting switch into the settings header on narrow windows. The
changed labels/buttons have no observed clipping or overlap in the final
captures under `docs/screenshots/redesign/k7-dock/`.

Final software verification: `scripts/check.py` passed 375 tests and compileall;
QML smoke/qmllint passed. Focused fake-I/O QML smoke checked Battery, Static and
Wave in RU/EN at 640 and 1000 px, including a real QML button click that only
created a draft. Tests cover composite Apply, exact-record conflict, mode-aware
controls, Cancel and installer resources. Installer, CI and Arch required-file
checks include the new QML/SVG. Other native modes, brightness levels,
directions/durations and persistence still need physical observation through
explicit user actions; passing software tests does not verify their appearance.

Native GTK GUI smoke also passed after the shared dock capability was added.
The checksummed Arch source was prepared at
`/tmp/logi-k7-dock-arch-20261028-final`; its manifest includes the new QML/SVG and
the two probe scripts imported by the packaged tests. PKGBUILD syntax passed.
No system installation or release was performed; a complete Arch package build
was not repeated in this UI stage.

## User acceptance, 2026-10-28

After the implemented dock editor was delivered, the user reported that
everything works. This confirms acceptance of the dock integration on the
attached unit. The detailed optical record remains the static-red/restoration
trial above; the user did not provide separate results for every effect,
parameter combination or operation after closing the application. Do not infer
those additional measurements or sensor-flag write support from this acceptance.
