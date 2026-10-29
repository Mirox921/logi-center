# Physical-device control pages — 2026-10-23

Ace68-II update (2026-10-28): native QML keyboard editors now cover trigger
multiselect, four assignment layers, per-key colors, advanced keys and native
performance flags. No new device cards or provider merging rules were added.
Read-only physical evidence and remaining macro/calibration/cloud gates are in
[ace68-editor.md](ace68-editor.md).

## Root causes

`Center.populate_mouse()` used only `ratbagctl list`; MCHOSE/OpenRazer/rivalcfg capabilities lived in inventory. Footer battery widgets used legacy ratbag presence and kernel battery files, never MCHOSE's observed battery capability. Keyboard pages rendered every device vertically, including a remembered G515 branch. Kernel input detection mistook touchpads and mouse/keyboard auxiliary interfaces for independent peripherals. A shared physical parent could also merge different device types.

## Changes

- `DeviceManager.active(kind)` selects current, non-disconnected devices with detected/live or kernel presence. Saved Solaar records and simulations are excluded from normal control pages; unknown backend-only records without current presence remain diagnostic. Temporary permission/read failures retain OS-confirmed devices; an explicit disconnected result excludes them. Physical merge keys include device type. Identical models on separate ports remain separate.
- `InputAdapter`: exclude BTN_TOOL_FINGER touchpads; retain HID parent identities for Bluetooth and read input bus type. Exact K7 auxiliary keyboard and exact Ace68-II auxiliary mouse interfaces remain diagnostic-only `interface` records. No generic name-based suppression.
- `peripheral_ui.py`: common mouse/keyboard selector, stable selected ID, current status/backend/manufacturer/profile metadata, battery, provider-owned capability controls and backups. Mouse settings no longer require the inventory page. Existing libratbag button/macro/LED/profile editor retained for the selected ratbag device. Read-only MCHOSE stage list and sensor flags are displayed honestly. Unknown standard devices have no invented controls.
- Keyboard page: responsive section navigation, overview/keys/profiles/lighting/more only when implemented; 68-key Ace diagram with proportional key widths and selected-key highlight. Bounded GTK minimum widths, compact controls and backup actions. Per-device section selection and existing device/profile/key drafts survive rebuilds; stale operations retain epoch/profile/connection guards. G515-specific controls require a selected currently detected G515 and live Solaar ping; history alone never creates a control panel.
- `device_status.py`: GTK-independent battery/status formatting. Real percent including 0 differs from unknown; coarse levels remain text. Charging, cache source, stale timestamp, read failure and permission failure have distinct labels. No last-known value is silently upgraded to a live read.
- Charge refresh: every 30 seconds, serialized executor, only reported MCHOSE/OpenRazer battery providers plus cheap kernel power-supply reads; no editor rebuild. Missing/failed reads retain error/freshness evidence. Power-supply events request a bounded update. `KernelBatteryAdapter` associates kernel battery facts only with a unique exact physical input parent, preserving existing kernel-backed Logitech battery support without joining by model name. Ambiguous receivers remain unassociated.
- Discovery monitors input/Bluetooth lifecycle in addition to USB/hidraw/sound; fallback includes input-node identities. Debounced hotplug disables old controls immediately, invalidates operations, rediscovers and restores context/drafts. No full discovery on ordinary widget changes or battery refresh.
- Inventory becomes overview/diagnostics and links to mouse/keyboard controls. Audio control architecture remains intact.

## Checks

178 deterministic unit tests pass, compileall and whitespace checks pass. New cases cover cross-vendor category membership, history/offline/simulation filtering, permission ambiguity, auxiliary interfaces, type-safe merging, identical units, exact kernel battery association, routing on disconnect/reconnect, unknown keyboards, battery provenance/charging/unknown/error cases. Unit tests import pure formatting rather than GTK, preserving headless CI.

Existing GTK smoke checks provider editors in the mouse page, no duplicate controls in diagnostic inventory, drafts, Ace selection, languages and dialog/capture cancellation. Simulation smoke retains 14 isolated scenarios and uses a unique application ID to prevent a previous test window absorbing a new launch.

Read-only physical GTK review: K7 Ultra is in mice with actual reported charge 54%; Ace68-II is in keyboards. Their auxiliary interfaces are absent from active control categories. Internal system mouse and keyboard remain selectable; touchpads are excluded. Existing settings were not changed. GTK render snapshots saved privately under `/tmp/logi-peripheral-review`; inspected mouse and keyboard images. Layout review tests wide and 520-pixel content, 68 key selection, minimum width and no horizontal overflow. The review script changes only its own temporary test window when Hyprland is available. No global display/window configuration is changed.

## Limits / release readiness

Physical unplug/replug, Bluetooth sleep and Logitech/Razer hardware are not exercised in this cycle; tests cover state/routing behavior, not hardware certification. A receiver's kernel presence is not proof its sleeping radio peripheral is awake; explicit backend disconnect takes precedence and ambiguous read failure is not treated as unplug. No general BlueZ pairing inventory is used as active-device evidence. No unsupported Ace advanced-key features were added. Existing backend limitations remain documented in `mchose-devices-progress.md` and `backend-support.md`.

The change fixes category routing and the tested connected-device UI; it does not establish universal support for all devices. Installer/runtime manifest and Arch archive must include the two new runtime modules. No publication or system package installation is implied.

Changed: `app.py`, `devices.py`, `discovery.py`, `mchose_adapter.py`, `ace68_adapter.py`, `device_ui.py`, `keyboard_ui.py`, `peripheral_ui.py` (new), `device_status.py` (new), `i18n.py`, `install.py`, `test_peripheral_ui.py` (new), `test_i18n.py`, `scripts/gui_smoke.py`, `scripts/simulation_smoke.py`, `scripts/peripheral_smoke.py` (new), this file and progress/agent documentation.

Final live review: actual own-window sizes 1000×780 and 640×780 passed. Ace diagram minimum 384 px, narrow allocated width 481 px; no horizontal scroll range. Read-only battery refresh retained the existing editor instance. Snapshot images were inspected. GTK mock unplug/replug removes the keyboard editor and restores its draft. 33 runtime modules are included by the installer; user settings and hardware parameters remain unchanged.

Follow-up: device inventory cards are now `Adw.ExpanderRow`, collapsed initially. The expanded state is retained by device ID across inventory rebuilds. Auxiliary `interface` records remain out of the user-facing device list. Charging state selects `battery-good-charging-symbolic` both in the mouse battery row and the global battery indicator; unknown/offline/permission states use distinct icons. GTK smoke explicitly exercises expand, collapse, refresh-state retention and charging-icon updates. Physical K7 charging-state assertion uses an in-memory capability fixture; the attached mouse was not on charge during the visual check, so no live charging state is claimed.

## 2026-10-25: Device artwork refinement
- Refined the generated mouse silhouette after visual review: elongated the body and narrowed its width so it reads as a real top-down mouse rather than a broad blob; removed the curved underside mark that looked like a smile.
- Re-generated all device class SVGs and refreshed `docs/screenshots/redesign/icons/contact-dark.png` / `contact-light.png` plus RU/EN Dashboard captures across 640–1920 px. Inspected 640, 1000 and 1920 Dashboard and the 1x/2x contact sheets.
- `python -m unittest -q` and `python scripts/check.py`: 214 tests pass. QML smoke and both visual gallery scripts pass. GTK GUI smokes remain blocked by the sandbox's missing display; no hardware operations were performed.

## 2026-10-25: Qt Quick Phase 1 shell (offscreen verified; real-session gate pending)
- Added optional `app.py --ui qml`; no flag and `--ui gtk` preserve GTK. The Qt import is only on the QML route, so missing PySide6 gives an explicit optional-dependency message.
- Added `device_service.py` as shared GTK/Qt orchestration over existing adapters, without changing protocols. Added toolkit-free `device_presentation.py` for readable names, transport-based grouping, exact known model names, connected-only filtering and generic class illustrations.
- Added a QML Dashboard, responsive cards, search/categories, built-in filter, a read-only capability page and a backend overview. The bridge performs discovery off the GUI thread, listens to existing DeviceMonitor events and updates stable device rows by ID. No QML hardware-write commands are present. Simulation uses existing SimulationAdapter.
- Added project-authored generic SVG assets; no product photos or third-party fonts. Updated optional Arch dependencies and source-install asset copying. PySide6/Qt remains optional; GTK remains default.
- Follow-up: Linux input bus type is now authoritative for I2C/I8042 internal devices even when VID/PID is present. Empty capability cards now say “Нет доступных настроек.” Added regression tests for both.
- Checks: PySide6 6.12.0 installed with user pacman authorization. `python -m compileall -q .`, `python -m unittest -q` (203 tests), `scripts/check.py`, and `scripts/qml_smoke.py` pass; qmllint accepts all QML pages. Live DeviceManager was read in offscreen Qt. Screenshots at 640/1000/1280/1920, English dashboard and detail saved under `docs/screenshots/redesign/after/`. GTK/simulation/peripheral GTK smokes remain blocked at GTK initialization because sandbox display access is unavailable. Direct Wayland Qt attempt aborted in Qt platform initialization; no session config was changed. See `docs/qml-parity.md`; Phase 1 is not passed.
- Live screenshot showed built-in mouse, built-in keyboard and Ace68-II; K7 Ultra was not present in that snapshot. Screens are offscreen renders, not proof of real Hyprland rendering. No hardware writes were performed. GTK remains the default.

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

## Header iteration: stage 1 (2026-10-25)

Implemented in the isolated `ui/dashboard-iteration` worktree: fixed header,
solid licensed project mark, successful-snapshot counters/time, readable RU/EN,
Tools menu, session settings and About. Backups launches a separate retained GTK
presentation using existing controls and restore dialog. The detached launcher
keeps simulation/language and cannot terminate an active GTK restore when QML
closes. No backend, identity or merge policy changed.

Stage 1b is intentionally pending header acceptance. Remaining stages: compact
toolbar; fixed-height cards with visible provider labels for uncertain duplicate
records; illustration provenance, graphite keyboards and corrected TKL/Full
block spacing (0.25–0.5u, 87/104 keys), distinct evidence-based silhouettes and
family scaling. A confirmed touchpad uses touchpad art; unknown pointers and
unclassified Bluetooth audio must remain visibly generalized. Family framing
must preserve visible mouse height >=60% of scene / keyboard width >=70% while
retaining relative variant sizes and source-canvas safety margins.

G502 duplicates are not yet altered: exact physical identity is still required
by DeviceManager. Later card source labels will expose the ambiguity, not merge
by name or VID/PID.

Stage 1 final checks: 231 unit tests/check.py, compileall, qmllint/QML offscreen,
QML real/simulated Wayland smoke, GTK GUI smoke, 15-scenario simulation smoke,
peripheral smoke and isolated GTK backup-entry smoke passed. Host access exposed
and fixed the existing Gtk.Picture(filename=...) presentation bug; new guards
prevent a partial Dashboard from falsely passing smoke. Native Wayland capture
at 1.25 DPR is reviewed; no physical charging transitions were performed.
Workspace 6 was used for native captures and the prior workspace restored.
See screenshots/redesign/header/validation.md for actual output and review gate.

## Stage 1b — service-backed QML backups

Tools now opens the QML backup page. Provider and legacy export/preview/selective
restore call unchanged services in the shared serial executor, with existing
Epoch/command cancellation and DeviceManager ownership checks. Fields retain
selection by device scope + backup checksum across re-preview; stale generations
cannot restore. Current/device/cache/local/server sources, actual returned values,
unconfirmed/partial outcomes and private safety-snapshot details stay separate.
GTK remains available through Open in GTK. No real hardware write was tested.
See docs/ui-iteration-progress.md and screenshots/redesign/backups/after/.

## Stage 2 — compact Dashboard toolbar

Removed the repeated page heading/subtitle and separate control rows. The header
plus one toolbar now occupy 110 px. Added counted tabs, inline/compact search,
Ctrl+K and slash, clear action, refresh glyph/progress and counted built-in toggle.
Counts follow search/built-in filtering but not the selected category, while the
header still reports unfiltered inventory. Filtering is entirely local.
State survives page changes; private GUI preferences preserve language/built-in
filter and reduced-motion choice across launches, without touching profiles or
legacy preferences. Simulation/smoke never write user UI preferences.

## 2026-10-25 — Dashboard cards / stage 3

All passports have a 164 px image scene and a reserved 36 px battery region;
percentage is 18 px mono. Known healthy connections use only a LED; unknown
transport has no empty frame. Type appears once, count uses a human plural.
The two G502 provider rows remain separate: discovery has insufficient shared
physical identity to merge them safely. Duplicate human names get a muted
libratbag/Solaar caption directly on each card; read-only records are subdued.
DeviceManager matching is unchanged. Details retain the provider and collapsed
local asset source/path/hash. Same-file artwork replacement changes the versioned
URL; a failed asynchronous decode rejects only that file signature and advances
the existing source chain. Simulation artwork/preferences use temporary storage.

Fresh battery presentation is extracted into GTK-free battery_presentation.py;
the existing GTK read-only polling is shared through battery_service.py. QML
polls on its serial worker, reacts to battery events, and adapts 3/8/30 seconds
(changed/stable/error); GTK retains its 5/10/30 schedule. Only battery/charging
capabilities change. Cache remains cache (including OpenRazer); numeric zero
remains zero, unknown remains -1, old values never fill the meter, and explicit
charging has an independent timestamp. Scoped access errors do not hide a fresh
kernel reading. No physical charging transition has been induced or verified.
Stable row IDs preserve cards, focus, source, selection and scroll on deltas.

Positive input evidence is required for touchpad artwork; i2c plus a vendor ID
alone no longer invents that subtype. Untyped internal pointers and Bluetooth
audio get neutral/generalized artwork and an undefined type caption.

## Stage 4 / final card artwork

Typed display routes select HDMI or DP; an untyped monitor uses a neutral audio
screen. No name-only subtype inference was added. Positive touchpad evidence,
undefined internal pointers and untyped BT remain distinct. Generic notes appear
on uncertain cards. Neutral silhouette distance is measured at 64px; the smallest
pair is >=0.17, above the conservative .12 threshold. G502 provider records remain
separate, with direct captions. The backend DeviceManager file is unchanged.

The same-file source URL is content-versioned and source SHA-256 is compared to
actual PNGs by the card smoke; gallery writes the actual repository-relative file
and hash. Details expose local provenance only in a collapsed disclosure. This
also removed the permanently visible opaque image slug and raw “generated” label.
The selected keyboard image uses actual bounds rather than shrinking the entire
transparent source canvas to a thumbnail. No startup rendering or copied product
photo is used. See header/iteration4/comparison.md and illustration review log.

Iteration5/E: unknown internal pointer resolves pointer_generic rather than the
old perforated module, with Type unknown/generalized artwork. Confirmed input
metadata selects touchpad; unknown Bluetooth remains a neutral audio module.
No discovery/identity/backend behavior changes. Local user-image precedence and
physical-device bindings are unchanged. All built-in/category counts share the
presentation filter pipeline introduced in A.

Iteration5 final QA: one presentation filter drives header/sections/tabs/built-in
availability; audio/other are explicit. Source captions preserve distinct G502
records. Wired/no-battery has no meter; USB devices with confirmed battery retain
it while charging. Card type/source captions12–13px, scenes320x240 and fixed slots.
Per-model fitting was explicitly selected by user. Hover reserve and source2x
pixel scale are measured, not guessed. Final icon acceptance/report:
docs/iteration5-report.md. Hardware and physical identification are unchanged.

# Live connection and duplicate-card correction (2026-10-26)

- The wired Logitech G PRO X USB sound-card variant advertises `CAP_BATTERY_STATUS` through HeadsetControl but returns `BATTERY_UNAVAILABLE`. For its confirmed USB product identity only, the presentation records battery absence from the model specification and hides the battery row. Other headsets with an unavailable reading remain unknown. The USB connection tag remains visible.
- Ratbag's read-only D-Bus `Device.Model` supplies a product VID/PID for its otherwise anonymous CLI inventory record. A G502 backend entry joins the kernel input entry only when the CLI name, D-Bus name, backend selector, and physical input candidate are each unique. `Device.Model` alone is not a physical identity; identical mice or unavailable D-Bus metadata remain separate. The auxiliary keyboard HID interface stays classified as an interface and is excluded from Dashboard cards.
- MCHOSE identity mode 0 identifies a wired link; modes 1/2 identify a wireless link through the USB receiver. K7 currently reports mode 1. The UI says “Беспроводное” and the detail says “Беспроводное через USB-приёмник”; it does not claim a specific radio frequency. Battery polling also refreshes the connection label when a new mode arrives. A failed read now leaves the mouse link unknown instead of reporting the receiver's USB bus as a wired mouse connection.
- Read-only live DeviceManager check: one active G502 card with Linux Input and libratbag, one active K7 card with wireless connection and 45% charge, one active wired PRO X card with USB and no battery row. [Dashboard at 1000 px](screenshots/README.md#historical-reviews), [Dashboard at 1920 px](screenshots/README.md#historical-reviews), [filtered wired headset](screenshots/README.md#historical-reviews) were captured in native Wayland on workspace 6.
- Sources: [libratbag D-Bus model semantics](https://github.com/libratbag/libratbag.github.io/blob/master/dbus.html), [Logitech wired PRO X product](https://www.logitechg.com/en-us/shop/p/pro-x-gaming-headset-blue-voice-mic-tech.981-000817), [MCHOSE protocol](https://github.com/alexfrih/mchose-linux/blob/main/PROTOCOL.md). The protocol document covers the family, while the K7 mode value was observed locally; no assumption about 2.4 GHz versus another wireless mode is made.

## QML editors

Functional migration is recorded in [qml-migration-progress.md](qml-migration-progress.md). Device pages now contain capability-driven editors; audio controls separate physical cards from server routes. GTK remains default and the action-level parity gate is explicit.
# K7 editor update, 2026-10-28

Dedicated QML K7DpiPanel / K7ButtonPanel / K7PerformancePanel follow the supplied
references in the current theme. An original button SVG separates native
indices/anchors from the illustration. Native commands come from exact K7 M HUB
schemas; Motion Sync false→true→false/readback/restore was physically verified.
Other new settings have mock coverage only. Complex macros stay read-only.
See [k7-controls.md](k7-controls.md); no dashboard/device merging changes.
