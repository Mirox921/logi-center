# Reliability upgrade progress

## Baseline / preparation
- Baseline: v0.2.0, commit 64f232d; working tree clean. 16 baseline tests.
- Runtime: app.py (GTK + inline actions), backend.py (CLI + parsing), i18n.py, solaar_write.py. Installer is a fixed runtime file list. No cancellation or operation result model.
- Available: GTK/libadwaita, pyudev, pactl, parec/paplay and pw-record/pw-play. G502 HERO + G PRO X USB connected; G305/G515 absent. Reading can be tested; no physical writes/recording without deliberate action.
- Skill review: system installer/creator and existing Omarchy available; official catalog reviewed; no relevant additional package installed. Project workflow recorded in AGENTS.md and .agents/skills/logi-hardware-validation.

## Plan / status
1. Verification: implemented with documented limits; physical validation pending. Parameter-specific result states; cache vs device provenance; timeout/disconnect handling.
2. Backup/restore: implemented with documented limits; physical validation pending. Versioned checksummed export, compatibility validation, selected preview, pre-restore backup, partial results.
3. Discovery: implemented with documented limits; physical validation pending. Debounced udev / PulseAudio events, generation guards and lifecycle cleanup.
4. Mouse editor: implemented with documented limits; physical validation pending. Model layouts, key capture and actual macro view/edit, preserve old controls.
5. Audio: implemented with documented limits; physical validation pending. Split presets, opt-in live meter and temporary original/processed samples.
6. Diagnostics: implemented and tested. Typed faults, capability checks, redacted bounded logs + UI.

## Audit findings
- Generic success on exit code; direct raw RGB writes; no readback policy.
- Main executor never shut down, UI rebuilds can race with queued callbacks.
- CLI profile data can be backend cache; hardware RGB previously differed physically.
- Solaar saved settings are local, not hardware snapshots.
- Presets combined by filename; global bypass affects both directions.
- All button key mappings lack visual editing and direct key capture.

Update after each stage with changed files, checks, limits and next action. Do not call mock tests hardware tests.

## Stage 1 implemented
- Added execution.py (typed faults, process deadlines/cancellation), operations.py (plans, observations, five result states + cancellation).
- UI writes now report verified / sent without verification / mismatch / fault / disconnected instead of generic success; profile/DPI/RGB paths included.
- Parameter policies: PulseAudio live server volume/mute/default; G515 live brightness only; G502 daemon cache is explicitly unverified even when matching; RGB cache mismatch reports requested and returned values; sidetone/RGB/timers without getter stay unverified.
- 26 tests pass (10 new operation tests), including mismatch, unavailable readback, disconnect, missing backend, cancellation and real subprocess timeout. No device writes made.
- Limits: libratbag does not expose optical LED state; retained provenance. UI generation/cancellation integration remains for stage 3.
- Next: versioned backup/restore with typed allowlisted actions and pre-restore safety snapshot.

## Stage 2 implemented
- Added backups.py: versioned JSON + SHA-256, model/type validation, typed allowlisted restore actions, per-category preview, pre-restore safety snapshot, stale-preview rejection and partial outcome report.
- Mouse captures supported profiles/macros/DPI/LED data as backend_cache; G515 exports local_saved_settings; audio exports audio_server values. Files are private and never execute embedded commands.
- Added export/restore controls for mouse, keyboard and audio. Restore stops at first mismatch/error/disconnect; no speculative automatic rollback over a failed transport. Safety snapshot can be restored explicitly.
- 33 tests pass, including corrupt input, incompatible model, unsafe action, partial restore, selection and changed-since-preview abort. Hardware restore not performed.
- Limits: not a full firmware image; independent audio channel restoration is skipped rather than flattened. Device-specific unsupported writes remain diagnosed by backend results.
- Next: event-based discovery, stale-task guards, cancellation and resource lifecycle.

## Stage 3 implemented
- discovery.py adds udev add/remove monitoring and a PulseAudio subscription (restart bounded at 5 seconds); cheap sysfs fallback only when udev unavailable.
- Debounced refresh preserves tab/scroll/selected mouse, deduplicates devices, blocks stale controls, invalidates old tokens and terminates cancellable command processes. Late results are ignored. Radio keyboard polling stays bounded at 30 seconds and reenables controls on reconnect.
- Executor and subscriptions have explicit shutdown. Old mouse selection/refresh callbacks use revision checks.
- 37 tests pass; inspected the installed pyudev callback signature and corrected to one Device argument. Mock rapid disconnect/reconnect and cancellation checked. Physical unplug/replug not exercised.
- Next: model-aware visual mouse editor and real key/macro capture.

## Stage 4 implemented
- Added mouse_models.py / mouse_editor.py: G502 and G305 schematics + generic layout, selectable button regions, current action and macro events, direct key press/release capture, delay insertion/removal, draft reset and explicit apply.
- Macro validation rejects unbalanced keys and warns on desktop shortcuts. Existing assignment dropdowns remain. ratbag_dbus.py reads ActionTypes; unknown macro capability disables new macro writes rather than assuming support.
- 41 tests pass (layout, recording autorepeat, unbalanced keys, key mapping and conflict checks included). No button write performed on physical hardware. Full Wayland shortcut interception depends on compositor; UI explains the limit.
- Next: separate microphone/headphone presets, explicit audio meter and private temporary recording paths.

## Stage 5 implemented
- audio_pipeline.py + microphone_ui.py add explicitly started live meter, max-8-second original recording, playback and immediate/delete-on-exit temporary sample cleanup. No capture occurs during construction/refresh/smoke tests.
- A processed sample is captured only when a real EasyEffects source exists AND its capture stream is linked to the selected raw source. Otherwise the UI explicitly records original only. No fabricated before/after comparison.
- Headphones/microphone controls and presets are separate. Inspected upstream EasyEffects CLI: `-l name` loads both directions if names collide. Direction-specific managed aliases prevent that; last selections are saved independently. Readback remains marked backend cache, not proven audible DSP.
- 49 tests pass: opt-in invariant, missing microphone/backend, actual route check, preset name collision isolation, temporary cleanup, peak processing and synthetic PCM WAV encoding. No user microphone capture was started; real signal/meter/playback still need user-triggered hardware validation.
- Next: diagnosis window, useful fault-specific recovery, bounded redacted logs, final integration smoke and documentation.

## Stage 6 implemented; integration reviewed
- diagnostics.py adds component/device/backend-specific faults and recovery hints, read-only diagnostics dialog and rotating private redacted logs. Requested/actual macro values never enter logs. scripts/diagnose.py emits a safe report; scripts/check.py runs syntax + tests; scripts/gui_smoke.py exercises widgets without writes/capture.
- Fixed ratbag key/disabled parsing, quote handling, macro tap comparison, LED case normalization, readback failures and EasyEffects boolean bypass parsing. Injected runners no longer query real D-Bus capabilities. Restore reports now include readable statuses and fault/mismatch details.
- Fixed microphone preparation cancellation race and surfaced asynchronous playback failures. Mock test added for playback failure; GUI smoke covers cancellation before recording.
- 64 unit tests pass; compileall passes. Connected G502 read-only snapshot: 5 profiles, JSON write/read/validate and identical preview passed. Audio server snapshot validates. GUI editor/language smoke passed; expanded dialog/cancel smoke passed.
- No physical write/restore, USB unplug, G515/G305 reconnect or real microphone capture performed. Final constraints and file map: docs/reliability-upgrade.md. No system permission/config changes or external publication.
- Final: all runtime modules installed for current user and compared byte-for-byte with source. Documentation lists per-stage scope and pending physical checks. Local changes retained in logical commits; no release/push performed.

## Mouse illustration refinement
- Replaced generic capsule with model-specific Cairo vectors: angular G502 with thumb shelf/paddles and rounded wireless G305 with two side buttons. Added metal wheel/grip/panel details, isolated callouts, selected-only leader and direct diagram hit selection. The illustration explicitly does not claim live RGB color.
- Files: mouse_art.py (new shared renderer), mouse_editor.py, mouse_models.py, i18n.py, install.py, scripts/gui_smoke.py. GUI smoke now uses its own application ID so an already open app cannot absorb the test launch.
- Checked rendered G502/G305 PNG previews visually; 64 unit tests, compileall, diff check and independent live GTK smoke pass. No hardware writes or microphone capture. G305 physical device remains unavailable.

## Assignment label correction
- Fixed typed assignment matching: `button 1` was incorrectly compared with `1`, causing standard clicks to select the custom macro entry. Both assignment interfaces now share assignment_label; recognized macros compare equivalent tap/press-release forms.
- Files: mouse_models.py, mouse_editor.py, app.py, test_mouse_editor.py. 67 unit tests, compileall and diff check pass. Actual device assignments are unchanged.

## Unplugged G502 header fix (before v0.3.0)
- Split remembered model name from live connectivity using MousePresence. Hotplug/refresh invalidates connectivity immediately; empty ratbag inventory marks it offline, backend failure leaves it unknown. Stale load callbacks are invalidated on refresh.
- app.py, discovery.py, test_discovery.py and scripts/gui_smoke.py updated; 69 unit tests pass, including unplug/reconnect and backend failure. Current disconnected hardware reports `No devices available.` from ratbag. Header regression is covered by independent GTK smoke.

2026-10-23: optional multi-vendor backend cycle implemented; read [backend expansion progress](backend-expansion-progress.md) and [support/limits](backend-support.md). 132 tests, GTK/simulation checks and local Arch build passed; K7 hardware access remains permission-denied. No new physical setting writes tested.

2026-10-23, subsequent MCHOSE cycle: see [mouse/keyboard progress and current hardware evidence](mchose-devices-progress.md). This supersedes the previous denied-access status for the local K7; Ace68-II uses an independent keyboard adapter.

2026-10-23: physical-device category and keyboard UI correction; see [current progress](category-ui-progress.md).

2026-10-24: Mouse charging indicator and collapsible device inventory cards; see [follow-up details](category-ui-progress.md).

## 2026-10-25: UX and device-state review
- Removed the forced dark theme; status follows GTK/libadwaita’s system theme. Added an operation spinner and removed the persistent bottom status/battery strips. Per-setting apply/reset actions now appear only for changed drafts.
- Reduced technical clutter in device inventory; backend provenance and limitations now live in collapsed advanced diagnostics. Status subtitles use human language. Device faults stay in diagnostics instead of generating repeated toasts while unrelated pages refresh.
- Reworked mouse navigation into compact Overview / Sensitivity / More / Profiles sections. Audio output/input rows are collapsible, volume drafts have contextual apply/reset, and backup controls are collapsed. Microphone test controls remain hidden until relevant and asynchronous errors are reported once.
- Tightened the gaming-mouse auxiliary keyboard filter to require exact USB parent, VID/PID, and exact model suffix match. Added regression tests for sibling/non-sibling interfaces. MCHOSE unknown battery values remain unknown rather than being omitted or shown as 0%.
- Validation: 183 unit tests, compileall, diff check, GTK smoke, 14 simulation smoke scenarios, and read-only live peripheral smoke passed. Captured and visually reviewed 1000x780 Devices/Mouse/Keyboard, 640x780 Keyboard, and fullscreen Audio in both light and dark app-local themes. No hardware writes or microphone capture.
- The MCHOSE adapter did not return a readable K7 battery value in this session, so no physical charging state was asserted. Audio screenshots use fixture device data; physical sound paths were not exercised. No display-resize path changes were made outside the temporary review window.

## 2026-10-25: dashboard, audio and responsive UI follow-up
- Added a live device dashboard as the landing page, with responsive device cards, local device illustrations, connection/capability/battery summaries, search and category filtering. Card clicks open the existing mouse, keyboard or audio controls; a back button returns to the dashboard. Backend diagnostics are in a compact header menu. GTK/libadwaita and the existing hardware services remain in use; no Qt rewrite or backend duplication was introduced.
- Audio page now groups output, microphone, equalizer, effects, test and advanced tools. It supports selecting an available default output/input, collapses other endpoints, labels HDMI/DP availability from server state, separates output and microphone preset groups, and updates battery widgets in-place.
- Added an EWEADN S9 detector for USB IDs 372e:1026 / 372e:1027. It classifies the device as a mouse and explicitly reports onboard configuration as unconfirmed; it sends no HID commands and installs no udev rules. Archive-derived host settings are not presented as hardware settings.
- Battery refresh now responds to UPower property events and power_supply udev changes, with a bounded adaptive read fallback; dashboard, mouse, keyboard and headset indicators are updated without rebuilding pages. Cached/unknown/stale charge states remain labeled. No charge-state write is used.
- Checks: 191 unit tests, compileall, diff check, GTK smoke, 14 simulation smoke scenarios and live peripheral smoke passed. On workspace 6, the live dashboard screenshot showed two-column cards at 1000 px; narrow keyboard smoke ran at 640x780 and reported 384 px minimum / 481 px allocated editor width. Screenshots are in `/tmp/logi-peripheral-review/` (`dashboard-1000.png`, `mouse-wide.png`, `keyboard-wide.png`, `keyboard-narrow.png`, `audio-fullscreen-light.png`, `audio-fullscreen-dark.png`, and device inventory views). Audio light/dark fullscreen screenshots use harmless fixture audio and perform no recording. Current live inventory included two mice and two keyboards; K7's latest battery read was unavailable and its cached state was labeled accordingly. Charging status was not physically asserted.
- Remaining: full G HUB-level visual polish and cross-category device detail are incremental; only GTK/libadwaita is retained because the existing application/backends are GTK-integrated and a Qt rewrite would need feature-parity work. EWEADN S9 is detection-only until its protocol/API can be confirmed; no onboard DPI, polling or battery control is claimed. Microphone monitoring/recording remains explicit user-initiated behavior.

2026-10-25: optional Qt Quick Phase 1 follow-up; GTK remains default. PySide6 6.12.0 was installed with explicit user authorization. QML offscreen smoke and qmllint pass; live DeviceManager screenshots were reviewed at 640/1000/1280/1920, with English and device-detail captures. Input bus classification now correctly marks the internal I2C pointer and I8042 keyboard; empty capability cards use a human-readable status. `203` unit tests, `scripts/check.py`, compileall and QML smoke pass. GTK GUI smokes cannot initialize in the restricted runtime. Real Wayland launch aborts during Qt platform initialization; do not bypass the session sandbox. Phase 1 remains blocked until a real Hyprland/Wayland GUI check is possible. See `docs/qml-parity.md`.

2026-10-25: Replaced hand-positioned SVG device art with an offline parametric mesh renderer. It produces deterministic transparent 1×/2× PNGs for 22 generic classes, uses the shared 25°/35° orthographic camera, faceted bevels, Lambert/Blinn-Phong/rim lighting, and mesh-projected blurred contact shadows. Three visual refinements addressed mouse-shell winding/seams, camera vertical projection, and headset continuity; a final diagonal mouse presentation improves scene occupancy without claiming a specific model. No exact-revision product image is bundled. QML cards use PNG artwork and do not import the renderer or pycairo at runtime. Replaced the selected QML display face with bundled Noto Sans (Apache-2.0), with Cyrillic coverage and actual Qt family registration checked; JetBrains Mono remains the data face. Final icon sheets and responsive simulated Dashboard screenshots were regenerated; see `docs/illustration-pipeline.md` and `docs/screenshots/redesign/icons/`. GTK is still the default and no hardware setting writes were made. Full test results and environment-limited GTK/Wayland checks are recorded in the completion report for this change.

## 2026-10-25: QML artwork and dashboard visual pass
- Narrowed/lengthened the generic mouse body in the SVG generator (0.82 horizontal scale) and removed the smile-like underside from the silhouette. Keyboard/touchpad contrast and straight keyboard outline remain generated from shared class illustrations; no illustration claims to be an exact product render.
- Captured simulated QML Dashboard images at 640/800/1000/1280/1600/1920 in RU and EN, device details, empty state, focus and known/unknown/charging battery states. Refreshed dark/light 1x/2x contact sheets for all 22 artwork keys. Outputs: `docs/screenshots/redesign/design-language/after/` and `docs/screenshots/redesign/icons/`.
- Verified bundled Noto Serif Display regular/bold and JetBrains Mono Qt family registration plus Latin/Cyrillic glyph coverage with `scripts/check_fonts.py`. 214 unit tests and `scripts/check.py` pass; `scripts/qml_smoke.py`, design gallery and icon gallery pass. `compileall` passes.
- GTK `gui_smoke.py`, GTK `simulation_smoke.py` and `peripheral_smoke.py` could not initialize GTK in this restricted run (`Gtk couldn't be initialized`; no Xvfb/display server available). QML was verified offscreen only; a usable real Hyprland/Wayland launch is unavailable. Hardware and physical charging were not exercised. GTK remains default and the QML parity gate remains blocked.

## 2026-10-25: layered 2D illustration pipeline (current)

- Supersedes the experimental 3D artwork renderer: straight top/front views,
  neutral graphite materials, clipped bevel/specular layers, silhouette-derived
  Gaussian contact/AO shadows and deterministic dither. The offline package
  builds 23 class/variant pairs (46 RGBA8 PNGs), 512x320 / 1024x640; neither
  Dashboard imports it. GTK Picture and QML share the provenance-aware provider.
- Class/variant selection now prefers typed metadata/capabilities/backend routes,
  never guesses a layout from the product title. Unknown internal pointers and
  untyped Bluetooth/audio use a neutral module. Exact-revision/system registries
  stay empty. User images use a stable hash slug in device-images/, retain old
  managed preferences, and have bounded WebP/SVG validation and local preview.
- Mouse, keyboard 65 and headset were viewed through three correction rounds
  plus a final padding pass. Remaining classes were inspected on the final
  dark/light, 1x/2x contact sheets. Local reference-photo overlays stay in /tmp;
  photos with unverified licenses are excluded from the source archive.
- Cards use 260 px compact composition; the real opaque device measures
  45.4%–47.9% of card height for all seven review fixtures at 1000/1280/1600/1920
  in RU/EN. Fixed a Qt software Shape scroll-clip leak and corrected the smoke
  visual-tree lookup so focus on Repeater cards is actually exercised.
- Validation: 227 unit tests, compileall, scripts/check.py, QML smoke/qmllint,
  all 46 PNG quality/determinism checks, gallery and screenshot capture pass.
  GTK gui/simulation/peripheral smokes were attempted but cannot initialize
  the display in the sandbox. No real Hyprland/hardware test is claimed.
  No settings writes, capture, system changes or publication were performed.
- Installer test uses a temporary home and verifies PNG/font/runtime copies with
  no illustrations/ runtime package. Documentation and full findings:
  docs/illustration-pipeline.md and screenshots/redesign/illustrations/validation.md.

## 2026-10-25 — header iteration, stage 1

Work is isolated in branch ui/dashboard-iteration; the original dirty tree was
preserved. Baseline checkpoint c01b543 records the existing project code and
assets, excluding unlicensed reference photos. Header stage adds a 68 px fixed
surface, solid instrument SVG shared with app icon/About, successful inventory
counts/time, readable RU/EN and a keyboard-accessible Tools menu. Settings is
explicitly session-scoped; Backups uses retained GTK controls in a detached
process. Stage 1b and the toolbar/card/artwork stages are still pending.

Two observed defects were corrected and recaptured: clipped RU/EN button text
and a Menu implicit-height binding loop. The three-bar sign replaces an initial
letter-like interior. See screenshots/redesign/header/validation.md for actual
checks and limits. No hardware writes or desktop configuration changes occurred.

Stage 1 final checks: 231 unit tests/check.py, compileall, qmllint/QML offscreen,
QML real/simulated Wayland smoke, GTK GUI smoke, 15-scenario simulation smoke,
peripheral smoke and isolated GTK backup-entry smoke passed. Host access exposed
and fixed the existing Gtk.Picture(filename=...) presentation bug; new guards
prevent a partial Dashboard from falsely passing smoke. Native Wayland capture
at 1.25 DPR is reviewed; no physical charging transitions were performed.
Workspace 6 was used for native captures and the prior workspace restored.
See screenshots/redesign/header/validation.md for actual output and review gate.

## 2026-10-25 — stage 1b QML backup presentation

Added a QObject facade, stable field model and QML backup page over the unchanged
legacy/provider services. No backend or backup-format changes. Explicit restore,
private safety snapshot, checksum/model checks, selected fields, source labels,
returned values, honest partial/unconfirmed outcomes and cancellation are retained.
18 new bridge tests and a memory-only QML workflow exercise the real services;
Wayland workflow passed on workspace 6 with previous workspace restored.
User approved autonomous continuation through the remaining stages; no more
intermediate acceptance requests. See docs/ui-iteration-progress.md.

## 2026-10-25 — stage 2 compact toolbar

Implemented the 110 px header/toolbar composition, counted tabs, real keyboard
search and compact popup, refresh and built-in toggle. Added bounded private GUI
preference storage and a one-shot read-only desktop animation preference on a
separate UI I/O worker. No command/wait is added to the UI thread; no hardware
or backup service code changed. Four preference tests and two bridge tests were
added (255 total). Responsive QML smoke covers six widths in RU/EN, actual typed
search, no extra discovery, popup/Escape and reduced-motion.

## 2026-10-25 — stage 3 cards and battery evidence

Uniform scenes, reserved battery rows, subtype/source captions and stable cards
are validated by 273 tests and offscreen + native Wayland screenshots. Extracted
existing GTK read polling into a shared toolkit-free service; QML uses it on its
worker with event-triggered/adaptive refresh. Simulation explicitly never starts
its poll timer. Cache/provenance, missing/zero/denied/stale/charging remain distinct.
Positive input evidence governs touchpad selection. DeviceManager, adapters and
backup services unchanged. GTK gui/simulation/peripheral checks all pass in the
host session. See header/stage3/validation.md. Stage 4 illustrations remain.

## 2026-10-25 — stage 4 final illustration/UI iteration

Graphite key series (mean top/body8–12 L*), TKL87/Full104 .5u block gaps,
laptop78 .7u function row/split arrows, distinct neutral silhouettes, matte
button-zone touchpad and confirmed HDMI/DP variants are implemented. Common
family mm scale preserves compact mice and keyboard sizes; prebuilt opaque-bounds
metadata frames the QML scene. Async cache-busted images, actual file/hash contact
tables and stable source captions remain presentation-only. Locale coverage now
checks QML and pure labels to prevent mixed English/Russian states. 281 tests,
compileall/check.py, qmllint/QML +backup/matrix smokes, GTK GUI/simulation15/
peripheral and native Wayland checks passed. 50 PNGs pass deterministic/quality
checks. Arch source inspected without installing. Screenshot evidence and exact
outputs: screenshots/redesign/header/iteration4/validation.md. GTK default and
old editors retained; full QML editor parity is not claimed. No physical writes.

## 2026-10-26 — QML text rendering

Wayland/OpenGL close-ups proved Qt's default LCD distance-field AA caused the
color fringe on small labels even with `Text.QtRendering`. QML now selects gray
AA before Qt import, uses a shared StyledText font path, and avoids the
Dashboard viewport texture. Both bundled families and hint tables were checked;
no replacement font was necessary. `--debug-text`, scripts/text_render_check.py,
125%-baseline native comparison and the review are in docs/typography-render.md.
GTK and hardware services are unchanged.

## QML functional migration, 2026-10-26

Supported mouse, Ace68, G515, audio/microphone, drafts and diagnostics actions now have service-backed QML presentations. Shared plans, DraftStore, AudioSession and both backup services are retained. See docs/qml-migration-progress.md and docs/qml-parity.md for verification, current K7 read failure and remaining release gates. GTK stays default; no hardware writes or system installation.

## K7 DPI state and context stabilization, 2026-10-28

The earlier K7 read failure is superseded by the successful 2026-10-27 reads
and user-observed charging/DPI LEDs in [k7-ultra-investigation.md](k7-ultra-investigation.md).
QML now shows the manual's six stage colors and observes configuration every
five seconds only while the K7 detail page/window is active. Reads share the
existing executor, preserve scoped drafts and reject stale replies. Shared
MCHOSE writes check the prepared profile and, for DPI, stage before sending;
readback from another context is not confirmation. Legacy unscoped drafts stay
available for manual review. Dock RGB targeting and reversible sensor-flag
writes remain unverified; no physical write was performed in this stage.

`scripts/check.py`: 365 tests passed. QML smoke/qmllint and focused fake-I/O
functional smoke passed; native GTK GUI and 15-scenario simulation passed.
Peripheral smoke stopped at the known null WidgetPaintable dashboard capture,
before its checks completed. Existing runtime files are already included by
the installer/Arch manifests and CI; no runtime file set changed.

## K7 dock RGB, 2026-10-28

An explicitly observed three-second native static-red test changed the dock
strip; the user confirmed its return to the original battery-level mode and
the complete original RGB record read back exactly. The physical target is
therefore established. The official K7 M HUB panel supplies seven native mode
IDs, brightness 0–100, duration indices for Flash/Stars and wave direction.
The shared MCHOSE backend now validates and applies a composite RGB record
with a private snapshot, exact-baseline guard and readback. Its receiver-only
read works during mouse sleep. Sensor flags remain read-only.

The QML dock editor follows the supplied reference in the current design
language, with an original SVG, effect-specific parameters and existing
Draft/Apply/Cancel. New assets enter installer/CI/Arch resource checks. Software
checks pass (375 tests, compileall, QML/qmllint and focused fake-I/O navigation).
Physical verification covers static red and original-mode restoration only;
other effects and persistence are not claimed. See [k7-dock-rgb.md](k7-dock-rgb.md).
# K7 reference-based editors, 2026-10-28

K7 now has dedicated DPI and button editors plus a compact sensor panel, using
the exact-model M HUB native commands through the shared control/worker path.
Drafts, Apply/Cancel, baseline/profile/mode guards, private snapshots and
field-specific readback are retained. Motion Sync alone was physically tested
false→true→false, with complete configuration restoration confirmed; other new
commands remain source-validated/mocked. See [k7-controls.md](k7-controls.md).
GTK stays default, complex K7 macro-bank editing remains unavailable, and the
working dock/G502 implementations are unchanged.

Final K7 controls validation: 400 tests passed, compileall and QML/qmllint passed;
GTK GUI and 15-scenario simulation passed. RU/EN offscreen captures cover 640
and 1280 px. The focused-input/telemetry regression and legacy scoped drafts
are covered. Current hardware evidence and remaining gaps: docs/k7-controls.md.

## Ace68-II reference-based native editors, 2026-10-28

Added six native QML sections with a shared 68-key multiselect diagram, 22
normal firmware effects/Off/Custom, per-key colors, four assignment layers,
RS/SOCD/DKS/MT/TGL and exact-model performance switches. All use existing
guarded adapter/Plan/executor and scoped Draft/Apply/Cancel. Bank allocation
preserves unknown records and profile/context changes stop pending writes.
Full suite: 427 passed; final catalog/ownership/priority safeguards: 98 relevant tests
passed. QML lint/loading, 40 RU/EN offscreen captures, GTK smoke and 15-scenario
simulation passed. New advanced/color/layer banks were physically read only;
new writes remain mocked. Macro/cloud/calibration/update gates and exact source
evidence are in [ace68-editor.md](ace68-editor.md). GTK stays default.

## G502 editor stabilization, 2026-10-28

Supplied wired/wireless top/side SVGs are integrated without modification.
The split diagram keeps all 11 native buttons. Macro recording has its own
modal window and reusable private library; mouse events are captured locally
but unverified native mouse-event macro playback stays blocked. Initial
ratbag capabilities are loaded during async discovery. Authorized read-only
HID++ evidence identified a physical/daemon profile mismatch; the editor now
follows hardware with explicit guarded synchronization and honest cache labels.
Details, screenshots and remaining physical gates: [g502-workflow.md](g502-workflow.md).
GTK stays default; no new physical setting writes were performed.

## G502 HiDPI decode fix, 2026-10-28

Reproduced hidden generic SVG decode errors at 200%. G502 image loading is
now gated by visibility/model/layout and uses bounded display-based width
with decoder-derived height, avoiding native-viewBox raster budgets and
transient top/side aspect mismatches. 100/125/150/200% fake-I/O checks pass
with a stricter 32 MiB decoder limit, all 11 buttons remain interactive, and
the 200% case enters CI. 18 targeted tests, QML/qmllint and native Wayland
simulation passed. The separately reported portal warning was not reproduced.
Evidence and limits: [g502-svg-memory.md](g502-svg-memory.md).

## G502 SVG feature compatibility, 2026-10-28

The remaining black panel/black gradients were Qt SVG incompatibilities, not
intended supplied artwork: unsupported clipPath and rgba gradient syntax.
Originals are preserved; reproducible compatible top SVGs use luminance masks
and equivalent rgb stops. Dashboard/editor share them without anchor changes.
Qt-versus-librsvg contour/material checks, 80 targeted tests and RU/EN 100/200%
fake-I/O click checks pass under a 32 MiB decoder limit; QML/qmllint passes.
Evidence: [g502-svg-compatibility.md](g502-svg-compatibility.md).

## G502 overlay interaction, 2026-10-28

Smaller inactive dots, hidden inactive connectors, smooth local hover, graphite
name tooltips and persistent amber selection replace the crowded overlay.
Ordered orthogonal routes separate wheel stems and stay clipped to the diagram.
All 11 IDs, 12×12 hitboxes, anchor centres, artwork scaling and remapping remain
unchanged. QTest hover does not change selection/drafts or send writes. RU/EN
640/1280 px at 100/200%, QML/qmllint and 19 relevant tests passed. Final images
were opened; details: [g502-overlays.md](g502-overlays.md).

G502 follow-up: moved only the DPI− anchor lower (native ID 6, y=240/680);
its target remains 12×12, DPI+ and mappings are unchanged. Wheel-tilt routing
keeps clearance from the new position. The DPI+/DPI− QML screenshot was opened;
RU/EN narrow/desktop interactions, 25 targeted tests and QML/qmllint pass.

## G515 reference editor, 2026-10-28

G HUB references now guide dedicated LIGHTSYNC, Freestyle, animation, assignment
and keyboard-settings sections in the existing QML theme. Added 87 native LED
zones over shared ANSI geometry, grouped/multiple selection, palette counts and
per-device color drafts through the existing Solaar CLI. Native breathing/cycle
period and intensity no longer reset to constants on Apply. Reads remain clearly
local; unverified submissions retain drafts. Ambiguous G515 aliases and mid-write
disconnects stop subsequent commands. Unsupported G HUB layers, host animations,
onboard slots and startup behavior are documented, without dummy controls.
Evidence, tests and limitations: [g515-editor.md](g515-editor.md). No physical
settings were changed; GTK remains default.

G515 validation: 116 integration tests, then 55 final affected tests passed;
QML/qmllint, compileall and isolated key/palette/Apply smoke passed. Final
640/1280 RU/EN images were opened. Fresh Arch source/manifest verification
includes the new helper, QML panel and smoke. No package installation or
physical write test was performed.

## G515 settings availability fix, 2026-10-29

Removed the name-only sysfs ROOT ping veto: successful Solaar detection/read
now works independently of rgb_control=False and missing local config. Scoped
read-only CLI queries use existing execution/Epoch guards and cache fallback;
actual getters win while RGB/per-key/host-timer values retain honest sources.
Fixed tag/map parsing, XDG lookup, exact cached device name routing, optional
Solaar rgb_power compatibility and arbitrary integer brightness percentages.
No physical writes, permissions or user configuration changes were performed.
Evidence and scope: [g515-settings-fix.md](g515-settings-fix.md).

Validation: 143 targeted tests passed; compileall, QML/qmllint and isolated G515
RU/EN 640/1280 mock smoke passed. GTK simulation/peripheral smoke could not
initialize GDK in this sandbox (no display/read-only dconf); not counted as
passes and not repeatedly retried. The attached G515 case remains user-assisted
read-only verification; it is not present in the current agent's sysfs.
`START_HERE.ru.md` supplies launch/dependency instructions for the source archive.

## EWEADN S9 integration, 2026-10-29

Added the model-verified ByteTech adapter, native DPI/sensor/button plans and
dedicated responsive QML editor, using the supplied archive plus official Hub
SDK evidence. Shared SDK/executor, generation/fingerprint/profile guards,
private pre-write snapshots and full readback remain in use. Established new
left-click mappings are verified before removing the old mapping. S9 receiver
identity alone is insufficient; model-ID checks also gate the supplied SVG.
The original user vector is preserved and a reproducible Qt-compatible vector
is shared by Dashboard/editor. UI scale 75–200% is persisted, with Qt restart.

Local macro capture/library/repeat metadata work; native macro-bank upload
remains blocked because the official writer formats the bank through OTA and
no bank read/rollback is established. Receiver firmware, profile switching and
firmware update are not fabricated. No real settings writes occurred; no S9
was physically available. GTK remains default. Exact feature matrix, sources,
test results, screenshots and physical test requirements: [eweadn-s9.md](eweadn-s9.md).


## QML-only cutover, 2026-10-29

User explicitly authorized QML as the sole primary interface and GTK removal
after software parity/regression checks. Archived the complete pre-cutover
b0a58d3 tree with SHA-256 before deletion. All 492 baseline tests, native
Wayland functional mock and QML backup checks passed before removing GTK
presentation modules. Shared services/protocols/drafts/backups remain intact.
QML is now the default; legacy GTK entry/widgets/backup process were removed,
and installer/package runtime dependencies switched to Qt. Recovery uses the
separate archive; it is not part of the installed QML application.

Post-removal check.py: 496 tests and compileall pass; final K7 recovery-message
checks: 53 tests pass. QML/qmllint, Wayland functional matrix and native backup
smoke pass. Real read-only G502/Ace68/headset navigation passed; K7 returned an
empty identity reply, now shown honestly with a wake/retry hint. No settings
writes or real audio capture occurred. Hardware verification remains scoped
by each device report. Details: [qml-cutover.md](qml-cutover.md).

Fresh checksummed Arch source and makepkg --nodeps --nocheck build passed.
Installed runtime/assets in staging byte-match the source; GTK GUI files and
dependencies are absent. Packaged default launcher simulation smoke passed.
No system package installation was performed.


## 2026-10-29 — src package and repository architecture

Moved production code to `src/logi_center`, grouped existing adapters by vendor,
and separated codecs, discovery/identity, Capability, Device/DeviceManager and
shared services. Extracted the existing input/power, libratbag, PulseAudio,
HeadsetControl and saved Solaar adapters from the inventory module without
changing protocol behavior. Updated all imports/mock targets and moved tests
into unit/integration/hardware (the latter uses fake transports only).

Canonical SVGs, PNGs, fonts, model metadata and notices moved into `assets`;
101 existing assets were byte-compared against HEAD and are unchanged. Central
resource resolution covers checkout, user-local, wheel and Arch layouts. QML
receives absolute asset URLs; button mappings/geometry are preserved. Offline
Cairo tooling lives under scripts/artwork and is excluded from runtime wheels.

Added pyproject/console entry point, wheel/sdist resource hook, source manifest,
package regression checks and CI coverage. Root `app.py` remains compatible.
Worker subprocesses resolve the installed package without cwd/PYTHONPATH.
Installer upgrades remove only known obsolete bundled files; private data stays
untouched. Backup service AST comparison confirms imports are the only changes
in backups.py/capability_backup.py. GTK remains externally archived.

Verification: 504 tests passed (26.503 s), compileall, qmllint/QML navigation,
functional stabilization and simulation smoke passed with real I/O blocked.
Reviewed the relocated G502 editor rendering; functional captures cover RU/EN
and 640/1280 widths. Built wheel from sdist; wheel CLI, resources, QML simulation
and scoped worker passed outside the checkout. Fresh checksummed Arch source
and makepkg --nodeps --nocheck passed; full Python tests ran separately. No
system installation, physical writes, recording, push or new release.

Architecture and commands: [development/architecture.md](development/architecture.md).


## 2026-10-29 — S9 discovery faults and G515 brightness levels

Fixed the positional Device constructor bug in EweadnAdapter: faults now reach
`faults`, while `simulated` remains False. Added discovery/filtering and public
JSON/QML diagnostic regression scenarios, including sleeping-device TIMEOUT.
The user's live S9 confirmation is recorded separately from our mock coverage.

Investigated the supplied G515 screenshots: installed Solaar rounds brightness
to firmware halving levels, explaining requested45/54 vs actual50. Scoped getter
now exports already-read validator metadata; QML selects actual supported
levels instead of arbitrary slider values on those builds. Continuous variants
remain compatible. Exact readback, real mismatch errors, dirty drafts and all
read-only process protections remain intact.

Checks: 51 targeted + 66 related tests passed; compileall passed. G515/S9 QML
smoke passed in RU/EN at 640/1280, with fake Apply/readback and no real writes.
Reviewed the G515 lighting screenshot. Peripheral read-only smoke navigated the
available Ace68 (0 live controls); it does not establish physical S9/G515
validation. No full test-suite rerun, hardware writes or system changes.
No runtime files were added: recursive installer/source/CI manifests already
include the modified modules and new tests. Remaining physical check: reopen
G515, choose an advertised brightness level and explicitly Apply; observe the
physical lighting and readback. See g515-settings-fix.md and eweadn-s9.md.

## 2026-10-29 — application license changed to GPLv3

Replaced root LICENSE with the official GNU GPL v3 text from
https://www.gnu.org/licenses/gpl-3.0.txt. Application licensing is
GPL-3.0-only in pyproject, Arch metadata, README RU/EN and QML About.
COPYRIGHT records project attribution and scope. Previously separate MIT
artwork retains its license in assets/LICENSE-MIT.txt; font and third-party
license texts are unchanged. Existing release tags/history remain untouched.

Wheel/sdist and user-local/Arch packaging now include LICENSE/COPYRIGHT.
Setuptools >=77 supplies SPDX License-Expression and license-files metadata.
Verified 7 targeted launcher/install/localization tests, release checks, wheel
built from sdist, SPDX metadata and license bytes in both distributions,
unchanged third-party notices, fresh Arch source and PKGBUILD syntax. No runtime
behavior changes, system installation or hardware operations.


## 2026-10-29 — remote S9/G515 hardware investigation

Used the supplied redacted log.json without committing it. S9 inner timeout
lacked page/chunk/latency evidence. Added bounded read-only trace collection,
ioctl start/end/count and frame validation reasons, preserving the 20 s worker
deadline and existing retries. Corrected actual feature byte-count handling
(no padded bytes as data) and documented short terminal page handling. Valid
model/status can survive a later page timeout; partial state never enables
writes, reset, configuration fingerprints or interactive editing.

G515 0x8071 zone has no actual getter in the inspected Solaar build; cache is
not firmware readback. Fixed Cycle 0x15 omitted saturation (serializer defaulted
the byte to zero), added per-device zone option/parameter metadata, adaptive
Wave/Ripple controls, exact LED Control readback before effects and honest
sent-unverified labels while retaining drafts. A truly readable backend can
confirm per-control scalar results; cache-only results cannot. Read-only Solaar
workers also freeze configuration persistence. No installed backend was edited.

Paired serial/input uniq uniquely associate Solaar cache and kernel device;
name/VID-PID matching never merges units or relabels receiver PID as keyboard
WPID. Scoped scalar reads reach inventory with provenance. rgb_zone_1 survives
report redaction; audio volume/mute scopes get anonymous endpoint IDs. Optional
missing providers remain isolated faults. Missing reliable identity leaves
cache rows separate in advanced diagnostics, deliberately.

Verification: full suite 528 tests passed (26.070 s); final feature-count,
short-page and readable-zone refinements passed 79 focused tests (0.499 s).
The final CLI timing/privacy checks passed 19 tests (0.026 s).
compileall, qmllint/QML navigation, S9/G515 fake Apply/readback, simulation smoke
and live read-only navigation passed. The last live navigation covered only the
locally available Ace68 with 0 live controls, not S9/G515. Reviewed native-effect
and unconfirmed-status captures RU/EN at 640/1280. Wheel/sdist and packaging
checks passed; source/CI recursive manifests include the new diagnostics scripts.
No physical writes, recordings, resets, firmware/pairing changes or system edits.

Physical S9 timeout cause and G515 LED animation/persistence remain pending
remote traces/observation. The G515 is at the user's friend's machine. Commands,
protocol evidence and remaining limits: [hardware-read-diagnostics.md](hardware-read-diagnostics.md).

## 2026-10-29 — follow-up from three remote read traces

S9 page128/chunk0 replies arrive promptly but fail length validation; added
strict short-frame compatibility for the supplied reference's 0x0b length
convention and useful numeric length rejection metadata. Exact remote header
still needs renewed trace; no guessed payload padding or timeout increases.
G515 read succeeds with RGB control enabled. Fixed process-local prerequisite
initialization before zone writes, rejecting failed getters instead of using
cached success. Installed Solaar packages remain unchanged.

58 targeted tests passed, followed by 22 diagnostic tests after adding the
worker-entry regression; compileall and diff checks passed. No physical writes.
Existing recursive installer/CI includes these changed modules; no new runtime
files or dependencies. Physical S9 read and G515 animation remain unverified.
See hardware-read-diagnostics.md for exact evidence and remote verification.
