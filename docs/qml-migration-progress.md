# QML functional migration — 2026-10-26

## 2026-10-27 G502/K7 stabilization update

The user-approved G502 HERO SVG is now packaged under
`qml_ui/assets/devices/exact/` and selected by its confirmed USB product ID,
while a user image retains priority. Dashboard and button editor share the
same SVG; the old editor diagram and class PNG remain available. Qt Quick
offscreen captures at 640 and 1000 px verified aspect, callout visibility and
mock selection without physical writes. Product artwork is not a calibrated
measurement of physical button positions.

The user physically confirmed one G502 RGB configuration: LED 1 Color Cycle,
8000 ms, brightness 255, continuing after the GUI closed. Other modes/zones
are not thereby verified. See [g502-rgb.md](g502-rgb.md).

The earlier K7 configuration-read failure below was superseded by a successful
validated read-only K7 read on 2026-10-27. Explicit QML Refresh now performs
an asynchronous K7 configuration read without a full discovery pass and
updates the displayed profile. Dock and LED controls remain blocked because
their K7-specific target and reversible write behavior are unknown; sensor
flags remain read-only. See [K7 investigation](k7-ultra-investigation.md).

Sprint verification: `python scripts/check.py` passed **346 tests** and
compileall; QML smoke/`qmllint` passed; the isolated functional smoke passed
with no real I/O and saved 640/1000 px RU/EN G502 and K7 captures under
`/tmp/logi-sprint-functional/`. Selected inspected mock captures are retained
under [sprint screenshots](screenshots/README.md#historical-reviews). GTK GUI smoke passed on the existing Wayland
session with no writes/capture; GTK simulation smoke passed 15 scenarios with
the real CLI forbidden. The initial sandboxed GTK runs could not initialize
GDK because the session display/dconf were inaccessible there. A local Arch
source archive passed its checksum and `makepkg --nocheck --nodeps` built the
package without installing it; inspection confirmed the SVG and manifest.

GTK remains the default. Launch the migrated interface with `python app.py --ui qml`; use `--simulate` for isolated memory-backed devices. No release, installation, default switch or real setting write is part of this work.

## Implemented

- `control_service.py`: toolkit-free field descriptors, range/step validation, GTK-compatible draft keys, ratbag profile/DPI/stage/rate/LED plans, shared mouse actions and result messages, Ace68 key controls, scoped G515 saved-setting controls. GTK imports the shared labels/actions/messages instead of a second copy.
- `qml_ui/bridge/editor.py`: capability editors, lazy ratbag read, private drafts, per-device sections/key/button state, sequential Apply, partial-result handling, exact binding/Epoch guards, readback provenance, macro edit/capture/reset and assignment capability checks. Native Linux right modifiers remain distinct; Qt shortcuts are consumed only while explicitly recording in this window. Wayland compositor shortcuts can still be intercepted by the compositor.
- `DeviceEditor`, `ControlEditor`, `MouseButtons`, `KeyboardEditor`: real supported controls, shared Theme, explicit Apply/Cancel, generic reference diagrams when no per-key backend is known. Mode/profile/stage changes run before other pending fields; ratbag LED mode precedes color and color is skipped for off/cycle.
- `qml_ui/bridge/audio.py`, `AudioPage`, `AudioEndpoint`: server routes, defaults, volume drafts, mute, per-direction EasyEffects presets/import/bypass, external effects editor, original/processed microphone test through the existing `AudioSession`. Streams start only after an explicit action; preparation cancellation, source removal, playback failure and clip cleanup are covered with a fake session. Production simulation never opens a microphone.
- `qml_ui/bridge/diagnostics.py`: actual inventory, scoped explicit Solaar probes, component checks, existing allowlisted report preview/copy/export. Both backup formats retain the existing QML facade and unchanged backup services.
- `keyboard_layouts.py`: shared data-only layouts used by QML references and the offline renderer. The rendering pipeline and PNGs are unchanged.
- Installer, source archive, Arch recipe and CI include the new modules/components. Qt imports remain optional and GTK stays available.

## Safety and state

One shared worker executor serializes hardware work with the existing backup controller. Busy editor/audio/restore operations cannot enqueue conflicting writes. Device identity uses the physical binding and selectors; no model-only merge was added. Hotplug invalidates pending operations. Audio property-change events request a refresh without cancelling their own write; endpoint replacement invalidates the binding.

Drafts use the original `DraftStore` and legacy key formats. Confirmed fields clear individually; sent/unverified fields retain their state. A deliberate edit after a matching cache observation starts a new draft from that observation without treating cache as hardware proof. Resetting one mouse button preserves other button drafts. Two providers for the same setting get separate draft keys. Cancel/interruption reports that the device state should be checked before retrying, and does not promise rollback.

## Verification

Full stage check:

```text
python scripts/check.py
Ran 320 tests in 24.444s
OK
```

Final focused bridge/translation check after the last status-message changes: 29 tests passed. QML smoke and qmllint passed. The functional smoke forbids the real runner and exercises actual service plans, DPI/rate, profile switch/return, button macro, LED color-before-mode, Ace68 key entry plus an actual QML Apply click, audio/server readback and public reports.

```text
PASS: mouse DPI/cache readback, macro, Ace68 selected key/device readback, audio/server readback, diagnostics; no real I/O.
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.
PASS: QML backup preview, keyboard field selection, selective restore, private snapshot, partial result and RU/EN; memory I/O only.
GUI smoke: no writes/capture; editor, language, dialogs and cancellation passed
Simulation GTK smoke: 15 scenarios; real CLI never called; no capture
```

One full offscreen RU/EN matrix covers 640×780, 800×780, 1000×780, 1280×800, 1600×900 and 1920×1080. Native Wayland functional smoke passed at 1000×780 on workspace 6; the original workspace was restored. Native live navigation covered ratbagctl, MCHOSE, Ace68 and HeadsetControl without setting writes or capture.

The mock mouse-open interval observed by the native smoke was 103.7 ms (cached fixture, not hardware discovery/startup). No general CPU/memory optimization claim is made. Stable-ID model tests cover updates without resets.

## Visual inspection

The primary review found two concrete issues: software-rendered Shape borders escaped the ScrollView clip, and normal button padding hid short key legends at 640 px. Frame-only software layers fixed the clipping without rasterizing text; keyboard-specific padding and short legends fixed the essential labels. No further aesthetic redesign was performed.

- [Dashboard](screenshots/README.md#historical-reviews)
- [Mouse](screenshots/README.md#historical-reviews)
- [Ace68 at 640 px, EN](screenshots/README.md#historical-reviews)
- [Audio](screenshots/README.md#historical-reviews)
- [Macro editor, scrolled to editing controls](screenshots/README.md#historical-reviews)
- [Backups](screenshots/README.md#historical-reviews)
- [Diagnostics](screenshots/README.md#historical-reviews)
- [Native Wayland captures](screenshots/README.md#historical-reviews)
- [Real read-only device pages](screenshots/README.md#historical-reviews)
- [Current localized read-error presentation](screenshots/README.md#historical-reviews) (memory fixture; raw technical detail remains in diagnostics).

## Remaining parity gate / exact limitations

1. Real setting writes, hardware restore and actual microphone recording were not authorized or performed. G502 values and readback remain daemon-cache evidence. Ace68 native key/config reads succeeded; writable support remains constrained by the existing adapter/firmware checks.
2. K7 is currently visible through Linux input, but its configuration read returns `connection_error`. The new UI exposes the read failure and enables no invented settings. Its QML SDK-plan route is covered by a fake transport over the existing MCHOSE adapter. No protocol recovery/profile write, permission change or retry loop was introduced to bypass this condition.
3. G515 and the optional OpenRGB/OpenRazer/rivalcfg devices were not attached for this migration. G515 uses saved provenance and requires its existing online check; advanced Ace68 SOCD/DKS/Mod Tap/remapping/macros remain unavailable because the backend does not implement them.
4. The prior GTK peripheral screenshot smoke has a reproducible null WidgetPaintable snapshot after a page transition. Normal GTK GUI and simulation smokes pass. The unchanged capture failure was not retried repeatedly.
5. Native file-picker selection, clipboard copy and all external effects-editor interactions still need a manual pass. The old manual ISO preview is replaced by shared accurate ANSI TKL/full/60/laptop references; none is advertised as an automatically detected programmable layout.

The software paths are implemented and the available automated checks pass. Full release parity is not declared; GTK remains the default. The exact action-level status is in [qml-parity.md](qml-parity.md).

## G502 RGB Apply / telemetry follow-up — 2026-10-26

The attached G502 read-only probe reported active ratbag profile 1 and two RGB
zones, both in `cycle`. In that mode `ratbagctl` does not report a zone color.
The earlier QML Apply sorted color before mode, so the first write was made
while the device still used `cycle` and the intermediate color readback could
not be evaluated. The editor now sends the requested color-capable mode first,
then the chosen RGB value for the same zone and exact selector. Switching from
an unknown-color mode requires a deliberate color selection before Apply.
Each command remains serialized and the ratbagctl CLI commits it; its immediate
getter is a **ratbagd cache observation**, not a physical LED readback. The
editor updates only the affected cached LED fields instead of running the
entire `read_mouse` scan again. A software mock checks two ordered writes,
zone/selector, cache readbacks, retained unverified drafts and no extra full
scan. Physical light change is **not verified**: the live G502 was absent from
the current `ratbagctl list` read-only inventory. A controlled manual test is
needed before calling the hardware fault closed. If that test still fails,
inspect ratbagd `Resync`/device firmware behavior and report the unsupported
path rather than converting cache equality into success.

K7 battery polling now uses only the existing identity report (`0x06`), which
already contains charge, charging and connection mode. It no longer requests
the configuration report (`0x67`) on every telemetry poll. The exact HID
selector and USB/protocol identity guard still apply. A device/power event
triggers an immediate read after discovery; while a read/write is busy the
next attempt is delayed one second. A connected K7 with readable telemetry is
polled every three seconds when idle; failures back off to 30 seconds. These
are scheduling targets, not measured physical detection latency. On this
machine the K7 configuration read was previously failing and no live telemetry
latency could be measured; there is no evidence that its hardware exposes a
reliable one-second charging notification.

Verification for this follow-up: `scripts/check.py` passed 335 tests after
fixing a test that assumed the process-wide translation language was Russian;
`qml_functional_smoke.py --stabilization` and `qml_smoke.py` passed offscreen
with no real writes. A mock measured the battery transport's command count:
one identity report now, compared with identity plus configuration before.
The targeted LED mock confirms no full `read_mouse` call after Apply (the old
path did one info, two supported-value and two zone-capability CLI queries).
Wall-clock before/after on the live mouse could not be measured because
`ratbagctl list` returned zero devices in this process. GTK GUI and simulation
smokes could not initialize a display (`GDK_IS_DISPLAY` failure and read-only
`/run/user/1000/dconf`); they were not retried without a changed environment.

Follow-up: Qt Quick's `ColorDialog` sends `Math.round` channels through
`QVariant` as integral floats (`34.0`), while the editor's strict RGB
validation accepted only Python integers. The QML bridge now converts only
finite integral float channels before validation; fractional and out-of-range
values remain invalid. An offscreen dialog→bridge check accepted `#2266aa`,
showed `[34, 102, 170]` in the preview and created a dirty draft with zero
hardware writes. Editor unit tests and the QML functional smoke passed. The
physical G502 lighting result still requires the controlled manual test.

## G502 active-profile correction — 2026-10-26

The user confirmed a visible color change after selecting the wired G502
HERO's “Profile 1” in QML. Before that selection, ratbagd reported profile 1
active and near-white colors there while the physical light stayed red, matching
ratbag profile 0's stored color. After the selection, read-only `ratbagctl`
reported profile 0 active. This establishes a profile-selection/state problem
in the failed attempt; the earlier daemon-cache color readback was never proof
of visible light. The installed libratbag 0.18 device file for `usb:046d:c08b`
has no `INDEX_OFFSET` quirk, whereas [current upstream device data](https://github.com/libratbag/libratbag/blob/master/data/devices/logitech-g502-hero.device)
does. That discrepancy is a possible contributor, not proof of the exact
sequence of the user's earlier profile switch. No installed backend files or
device settings were changed by the agent.

QML now re-reads a previously selected ratbag mouse when its page is opened
again. If the active profile changes between reading the editor and Apply, the
existing guard still prevents the write; the editor now refreshes automatically,
shows a localized explanation, and keeps the profile-scoped draft. The same
guard covers button assignments. The speculative change to send LED mode after
color was discarded: the successful user test did not require that change.
Only this G502 active-profile color path has physical confirmation; optical
readback and other profiles/modes are still unverified.

Targeted verification: `test_qml_editor` 17 tests passed, including an external
profile-switch mock that issues no setting write and retains the draft;
`qml_functional_smoke.py --stabilization` passed offscreen with no real I/O;
targeted compilation and `git diff --check` passed.

## G502 HERO RGB follow-up — 2026-10-26

G502 HERO RGB follow-up: see [g502-rgb.md](g502-rgb.md). Read-only active
profile data showed `cycle` with `duration: 0` and `brightness: 0` on both
ratbagd LED records. QML now offers profile-scoped hardware cycle/breathing
period and brightness controls for the exact wired G502 HERO model, stages a
nonzero period on explicit mode selection, and applies period/brightness before
activating the mode. Static color and off keep their existing paths. The UI
reports ratbagd cache evidence without claiming optical confirmation. Mock
tests cover ordering, scope, draft separation, unsupported models and zero
period. No agent-originated hardware write or background RGB worker occurred.

Verification: `scripts/check.py` passed 340 tests; offscreen QML functional
lighting smoke passed, with RU/EN screenshots at 640 and 1000 px under
`screenshots/migration/g502-rgb/`. GTK `gui_smoke.py` and
`simulation_smoke.py` could not initialize a display in the sandbox
(`GDK_IS_DISPLAY` / read-only dconf); their failure preceded application
logic. Existing installer recursively copies the changed QML and existing
Python modules, and CI discovers the new tests and already runs the QML
functional smoke; no manifest entries were added. Physical continuous
animation and persistence after exit remain an explicit manual gate.

## Packaging checkpoint

Arch source packaging and `makepkg --nodeps --nocheck --noconfirm` build passed; no package was installed. The separately completed full stage check was not redundantly rerun by makepkg. All 175 installed runtime/QML/asset files were byte-compared with source; the offline renderer is excluded. The default launcher remains GTK.

## Stabilization after 86bd4f9

- The G502 button editor uses two offline SVG schematics exported from the GTK
  editor's 480×440 geometry. Eleven external numbered targets stay interactive;
  their semantic captions are in the selector and accessible names. The selected
  target points to the original physical anchor. Generic mouse schematics remain
  explicitly illustrative when an exact diagram is unavailable. Assignment and
  macro controls stack at 640 px and sit beside the schematic at 1000 px.
- QML field feedback now labels verified, sent with matching backend cache, sent
  without a reader, failed readback, mismatch, and operation failure separately.
  Cached RGB is marked as last observed; missing color stays unknown instead of
  being replaced with white. An actual read-only ratbagctl query returned
  `000000` for both active G502 LED zones, so the current black values originate
  in the daemon cache and do not establish visible hardware RGB. Drafts and
  operation states remain unchanged.
- Audio endpoint labels use PulseAudio/PipeWire description, route and bus
  metadata; backend names remain stable selection IDs. Read-only live metadata
  produced distinct PRO X, HDMI/DP 1–3, speaker and microphone rows. External
  changes to the default follow the active selector unless a user is previewing
  another endpoint. Distinct endpoints are never merged by label.
- Output/input presets report loading, missing EasyEffects, empty lists and
  read errors; Apply requires a listed preset and available EasyEffects.
  The existing import and external effect actions remain. Read-only capabilities
  render as observations, without disabled editable widgets.
- Representative offscreen RU/EN captures at 640×780 and 1000×780 are in
  `docs/screenshots/migration/stabilization/`. One primary visual pass and two
  corrective passes fixed clipped two-digit callouts and a missing English
  lighting-zone caption. The screenshots also show compact desktop grids and
  stacked narrow layouts. Tests use mock writes only; live lighting writes and
  EasyEffects application were not attempted. GTK stays default.

Targeted completion checks: 72 mouse/audio/editor/packaging/model tests passed;
35 focused stabilization/editor/audio/translation tests passed before the final
rendering correction; 16 directly affected tests passed after the final source
change. QML lint/loading and the original plus stabilization functional smokes
passed. Both functional smokes patched the real runner and reported no real I/O.
`compileall` passed. `scripts/prepare-arch.py` prepared a local checksummed source
archive with the new diagram assets and generator; nothing was installed.

## Ace68-II continuation, 2026-10-28

`Ace68Panel`, `Ace68Keyboard`, `Ace68Assignments` and `Ace68Advanced` now use
the existing controller/executor with native layer/color/advanced banks and
performance flags. Drafts include device/profile/layer/key context; selected
trigger writes are batched by parameter. Unknown actions/records remain intact,
Fn access is protected and stale bank baselines reject writes. No firmware or
manual calibration command was added. Runtime modules/resources are included
by installer, CI and Arch checks. See [Ace68 evidence and remaining gaps](ace68-editor.md).

## G515 reference UI continuation, 2026-10-28

Dedicated G515 LIGHTSYNC/Freestyle/settings UI reuses the shared control service,
DraftStore and guarded executor. Added parameterized native effects and scoped
per-key color plans (saved known zones only), no new HID protocol. Animation and
assignment tabs explain missing backend support. Mock interaction screenshots
and the precise G HUB coverage matrix are in [g515-editor.md](g515-editor.md).
Physical G515 behavior, autonomy after exit and additional effect enumeration
remain gates; the G502 physical confirmation does not apply to this keyboard.
