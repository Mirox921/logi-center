# G515 LIGHTSPEED TKL editor — 2026-10-28

The ten user-supplied G HUB screenshots were inspected. Their section structure
is adapted to the existing graphite/amber QML theme; screenshots/product imagery
are not bundled as application assets. GTK remains default.

## Implemented and checked with mocks

- `G515Panel.qml`: LIGHTSYNC, per-key colors, animations, assignments and keyboard
  settings; responsive ANSI/TKL diagram, 87 distinct **LED zone** IDs, Ctrl/Shift
  selection, keyboard activation, WASD/numbers/F-row/modifier/arrow groups,
  color picker/palette and per-color counts. The existing stable list model
  updates individual keys without recreating delegates or losing keyboard focus. Existing project ANSI geometry is
  reused; ISO variants and exact physical keycap legends are not claimed.
- Existing Solaar control/brightness/idle and lighting-off timers are grouped
  separately. These timers are **lighting** timers, not keyboard sleep timers.
  Observed values are local Solaar settings, not device readback.
- Static (1), off (0), breathing (10), cycle (21) retain the existing service path.
  Animated effects now send period/intensity together instead of always forcing
  3000 ms/100%. Parameters appear only for the selected animated effect. Missing
  timing after Static/Off uses clearly labeled proposed defaults, never a claimed
  device read. Period 1000–20000 ms and intensity 0–100 follow
  the installed Solaar `LEDZoneSetting` validator, not an assumed G HUB range.
  Effect-specific drafts survive switching effects.
- Freestyle writes use the **existing** `per-key-lighting` CLI setting, with native
  decimal RGB and canonical zone IDs. Only known zones with valid saved colors
  become selectable. Unknown IDs, malformed values and `-1`/NoChange are skipped.
  No keyboard keycode or Ace68 protocol is used. The installed Solaar CLI checks
  the connected keyboard's actual zone mask before writing each zone.
- Painting only stages per-device DraftStore changes. Explicit Apply claims RGB,
  selects the static effect, and sends changed keys sequentially. This effect
  change is disclosed in the panel. Solaar's existing frame sender reconstructs
  other saved key colors. No host animation loop or background service was added.
- Existing executor, cancellation, binding, partial-operation and DraftStore
  behavior is retained. Every G515 command additionally requires one unique
  connected G515 and the existing positive ROOT ping status. An ambiguous alias
  or disconnect stops subsequent commands. No unverified draft is discarded as
  hardware-confirmed. Refresh reads saved configuration; it cannot prove optical
  state or establish hardware color readback.

## Reference coverage / actual limitations

| G HUB reference | Logi Center status |
|---|---|
| Fixed, off, breathing, cycle | Service-backed existing native effect IDs; local metadata; target Solaar validates actual zone support on Apply. Physical G515 operation remains unverified. |
| Effect timing/intensity, overall brightness | Backend ranges; explicit Apply. No claim about persistence after closing the application. |
| Freestyle, groups and color counts | Implemented via saved known zones and existing 0x8081 setting; mock-tested. Requires a Solaar build providing `per-key-lighting` and an existing saved zone map. |
| Wave, Ripple | Exposed only when the initialized device-zone validator enumerates their IDs and parameters. Physical behavior remains pending remote verification. |
| Pulsar Point, Starlight, Echo Press | No verified device-specific implementation; not exposed as working presets. |
| Screen sampler, audio visualizer, custom animations / playback modes | Host effects/editor not implemented. Animation tab explains this; no decorative playback/speed controls. |
| BASE/FN/G-SHIFT; press/hold/release; action/command/key/macro/system assignment | No verified G515 mapping API in existing adapter. Clearly unavailable; LED zone IDs are never used to remap keys. |
| Onboard slot, startup/PC-state behavior, reset, firmware updates | No verified safe service in current G515 adapter. Saved startup/shutdown fields alone do not establish write support; installed persistent-animation allowlist does not establish G515 support. |
| Battery and charging | Existing device header uses available device evidence; no invented power estimate. |

Local evidence: installed `logitech_receiver/settings_templates.py`
(`LEDZoneSetting`, `RGBEffectSetting`, `RGBControl`, `PerKeyLighting`) and
`solaar/cli/config.py`. Factual LED IDs match the installed Solaar/OpenRGB ANSI
keyboard zone table (`solaar/ui/perkey/layouts/_keyboard_base.py`); application
layout code is project-authored. No installed backend files were modified.
No complete Solaar device enumeration or physical HID writes were performed.

## Verification

- `test_g515_editor.py`: native IDs, sentinels/invalid maps, parameter validation,
  per-effect drafts, selection/Cancel, fake Apply, missing readback, ambiguous
  devices, disconnect during Apply, partial failure, reload/selection retention.
- `scripts/g515_editor_smoke.py`: isolated `DeviceEditor` with mock G515 service;
  QTest key click, four staged WASD colors, Apply/dirty states, RU/EN, 1280×900
  and 640×780. Ten PNGs in `docs/screenshots/redesign/g515/`. Review opened the
  desktop/narrow lighting, freestyle, settings and unavailable-section images.
  Content below the viewport scrolls; footer stays available. One corrective
  pass centered the diagram and kept dark key colors from hiding their labels.
- QML/qmllint accepted. Tests/package results are recorded in the progress log.
- First standalone launch inherited a Wayland environment and aborted before
  QML load (no display access). Explicit offscreen fixed the test. System
  coredump access is unavailable; Qt's log identifies platform initialization
  failure. Native Wayland and physical G515 validation were **not** performed.

Next hardware validation needs the user's explicit action: record original
lighting, apply a single known key color, check unaffected keys and restore;
then check native effects/timers and closing behavior separately. Do not infer
success for G515 from the G502's physically confirmed RGB result.

Final results: 116 integration tests passed, then 55 affected tests passed after
the final focus/default-parameter changes (including the new missing-timing test).
`compileall`, QML smoke and qmllint passed. The isolated G515 smoke also tests
Space activation and actual QML palette clicks. The source archive was prepared
with checksums and checked for the new runtime/test/script resources; nothing
was installed. A native Wayland check and physical write validation remain open.

## Settings availability correction, 2026-10-29

The original ROOT-ping-only gate and cache-only G515 loader above are superseded
by [g515-settings-fix.md](g515-settings-fix.md). Scoped read-only Solaar getters
now take precedence, False RGB control does not hide settings, and local config
is a fallback. No additional hardware feature or physical confirmation is implied.

2026-10-29: scoped zone enumeration, Cycle saturation fix, LED Control verification,
accurate unconfirmed states and receiver identity handling: [hardware-read-diagnostics.md](hardware-read-diagnostics.md).
