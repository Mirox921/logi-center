# GTK / QML functional parity

QML is the sole in-tree GUI following the explicit user-authorized cutover on
2026-10-29. The complete GTK baseline is archived separately. Software parity,
regression and native Wayland mock checks passed before removal; current
cutover evidence and recovery instructions: [qml-cutover.md](qml-cutover.md).
Hardware write verification remains parameter/device-specific below; this is
not a declaration of universal hardware certification.
Status vocabulary: Not started; Implemented; Tested with simulation; Tested with real read-only hardware; Hardware write verified; Blocked; Not applicable.

This inventory describes actual GTK actions, including legacy ratbag/G515 paths. Unsupported vendor features have no writable QML control. Historical visual gates are in [qml-parity-history.md](qml-parity-history.md).

| GTK section | Action | Python API | Backend | Devices | Read | Write | Confirmation | QML destination | Status | Verification / limits |
|---|---|---|---|---|---|---|---|---|---|---|
| Mouse | DPI / active DPI stage / rate | backend.read_mouse; operations.plan_for | ratbagctl | mouse | cache | yes | cache only | DeviceEditor / ControlEditor | Tested with real read-only hardware | Native Wayland read of G502/Ace68; mock writes and readback only. |
| Mouse | Profiles | operations.plan_for; adapter capability.plan | ratbagctl, MCHOSE | mouse | yes | yes | backend-dependent | DeviceEditor / profiles | Tested with simulation | Shared control/plan tests and QML functional smoke; real setting writes not run. |
| Mouse | Button assignment / keyboard shortcuts | mouse_models.action_allowed; operations.plan_for | ratbagctl | mouse | cache | yes | cache only | MouseButtons | Tested with real read-only hardware | Native Wayland read of G502/Ace68; mock writes and readback only. |
| Mouse | Record/edit/reset macro draft and named library | mouse_models.MacroDraft; macro_library; drafts.DraftStore | ratbagctl | mouse | cache / private draft | keyboard events; mouse-event playback unverified | cache only | G502ButtonPanel / MacroWindow; generic fallback | Tested with simulation | QTest captures keys and mouse clicks without activating controls; library roundtrip, Apply guards, all 11 G502 IDs. Mouse clicks stay local; unverified native playback is blocked. |
| Mouse | LED zone mode / color / dynamic period and brightness | operations.plan_for; DeviceManager.guard_command | ratbagctl | mouse | cache | yes | cache only | DeviceEditor / lighting | Hardware write verified | User confirmed static color on active G502 HERO Profile 1 and continuous autonomous cycle for LED 1 at 8000 ms / brightness 255. See [g502-rgb.md](g502-rgb.md); other zones/modes/speeds remain unverified. |
| Mouse | DPI / stage / rate / debounce / sleep | MchoseAdapter; capability.plan | MCHOSE | mouse | device | yes | device | DeviceEditor | Tested with real read-only hardware | Attached K7 configuration was read on 2026-10-27. Only the earlier DPI 400→450→400 write is physically verified; other setting writes remain unverified. |
| Mouse | K7 stored DPI stages / X/Y / native buttons / sensor settings | k7_settings; MchoseAdapter.k7_setting_plan | MCHOSE K7 Ultra | exact-model device read | native commands | field readback + unrelated-bit guard | K7DpiPanel / K7ButtonPanel / K7PerformancePanel | Tested with simulation | Exact K7 M HUB schemas, scoped drafts, Apply/Cancel, stale guards and RU/EN responsive mock interactions. Complex macros/unrecognized bindings stay read-only. Most new writes remain physically unverified; see [k7-controls.md](k7-controls.md). |
| Mouse | K7 Motion Sync | native 0x11/0x42, tri-state field | MCHOSE K7 Ultra | device | yes | device + restoration comparison | K7PerformancePanel | Hardware write verified | Explicitly approved false→true→false test on attached unit, with original config restored and unrelated settings unchanged. No claim about perceived latency, persistence or every firmware revision. |
| Mouse | K7 charging / active DPI stage / indicator color cues | MchoseAdapter identity/config read; EditorController passive observation | MCHOSE | K7 Ultra | device | no LED writes | state read, no optical readback | DeviceEditor / pointer, indicators | Tested with simulation | User confirms solid red while charging and that the underside DPI LED lights. Manual color cues are displayed; the active detail page polls state every 5 s with cancellation/draft guards. Automatic physical-button synchronization remains to be observed. See [K7 investigation](k7-ultra-investigation.md). |
| Mouse | K7 dock RGB | MchoseAdapter dock_setting_plan; native RGB record | MCHOSE | K7 Ultra dock | device record | seven native effects, off, effect-specific fields | record readback, no optical readback | K7DockPanel / existing editor Apply | Hardware write verified | User accepted the working dock editor on 2026-10-28. Detailed optical evidence covers static red and restoration to the original Battery mode; separate per-mode/parameter and post-exit persistence results were not recorded. Composite Apply, drafts, Cancel and conflicts also pass with mocks. See [dock details](k7-dock-rgb.md). |
| Mouse/keyboard | Provider scalar / RGB zone / brightness / effect | capability.plan; DeviceManager.route | OpenRGB, OpenRazer, rivalcfg | mouse,keyboard | provider-dependent | supported subset | provider-dependent | DeviceEditor | Implemented | Capability-driven bridge plus existing provider tests. OpenRGB/OpenRazer/rivalcfg hardware unavailable. |
| Keyboard | Ace68 multiselect / actuation / RT / dead zones | ace68_protocol.validate_key_value; setting_plan | MCHOSE Ace68 fw121 | keyboard | device | yes | device | Ace68Panel / Ace68Keyboard | Tested with simulation | WASD/all/inverse, grouped selected-key writes, scoped drafts; earlier physical subset documented separately. |
| Keyboard | Profile / rate / 22 native effects / Off / palette / brightness / speed / direction | capability.plan | MCHOSE Ace68 fw121 | keyboard | device | yes | device | Ace68Panel | Tested with simulation | Effect-specific controls, native firmware effects; no host animation loop. |
| Keyboard | Four layers / key, mouse, media, lighting and shortcut assignments | ace68_bindings; binding_capability | MCHOSE Ace68 fw121 | keyboard | device | yes | device | Ace68Assignments | Tested with real read-only hardware | 272 positions physically read; writes mocked, Fn protected. |
| Keyboard | RS / SOCD / DKS / MT / TGL | ace68_advanced; advanced_capability | MCHOSE Ace68 fw121 | keyboard | device | yes | device | Ace68Advanced | Tested with real read-only hardware | Native banks physically read; new writes/behavior mocked only. No compaction/unknown-bit replacement. |
| Keyboard | Custom per-key RGB | read_colors; color_capability | MCHOSE Ace68 fw121 | keyboard | device | yes | device | Ace68Panel / Custom | Tested with real read-only hardware | 68 colors read; writes mocked. Native Custom mode must be applied first. |
| Keyboard | Win Lock / debounce / stability / OS mode / adaptive-calibration flag | setting_plan | MCHOSE Ace68 fw121 | keyboard | device | yes | device | Ace68Panel / performance | Tested with real read-only hardware | Exact masks, debounce 0/7 and Mac/Win interaction tested with memory transport; no physical changes this stage. |
| Keyboard | Macros / cloud effects / switch/precision calibration / firmware | existing records preserved | MCHOSE Ace68 | keyboard | partial metadata | no | N/A | Concise unavailable state / diagnostics | Blocked | Macro-bank negotiation, vendor cloud and safe calibration/update lifecycle remain unvalidated; see ace68-editor.md. |
| Keyboard | G515 native RGB / period / intensity / brightness / lighting idle timers / per-key colors | control_service.g515_controls; g515_lighting_plans; existing Solaar CLI | Solaar | G515 | local saved settings | yes, known zones | brightness probe only; RGB/per-key unverified | G515Panel | Tested with simulation | 87 ANSI LED IDs; draft/Cancel/fake Apply/disconnect tests and RU/EN 640/1280 screenshots. Single keyboard + ROOT ping required. No physical confirmation; [G HUB gaps](g515-editor.md). |
| Keyboard | Reference keyboard layouts / Solaar launcher | keyboard_ui.KeyboardDiagram; subprocess launch | Linux input / Solaar | keyboard | reference | no | N/A | KeyboardEditor / tools | Tested with simulation | Shared ANSI TKL/full/60/laptop layouts; Solaar launcher is explicit. Legacy illustrative ISO preview is not presented as detected hardware. |
| Inventory | Explicit individual Solaar scalar probes | solaar_adapter.probe; choice_plan | Solaar | saved records | device | enumerated safe values | device | Diagnostics / inspect | Implemented | Existing scoped probe/choice_plan service and tests; explicit QML diagnostic action. No full startup enumeration. |
| Audio | Endpoint selection / default output and microphone | pactl via operations.plan_for | PipeWire/PulseAudio | audio | server | yes | server | AudioPage | Tested with simulation | Shared control/plan tests and QML functional smoke; real setting writes not run. |
| Audio | Output/input volume and mute | operations.plan_for | PipeWire/PulseAudio | audio | server | yes | server | AudioPage | Tested with simulation | Shared control/plan tests and QML functional smoke; real setting writes not run. |
| Audio | Sidetone | HeadsetAdapter capability.plan | HeadsetControl | audio | no getter | yes | unverified | DeviceEditor / AudioPage | Tested with real read-only hardware | Native PRO X capabilities and generic numeric editor; sidetone has no getter. No write executed. |
| Audio | Explicit live meter | AudioSession.meter; processed_route | parec | microphone | stream | no setting write | N/A | MicrophoneTest | Tested with simulation | AudioSession + fake-session bridge tests: opt-in, cancel before preparation completes, source removal, cleanup. No real microphone capture. |
| Audio | Record <=8s / stop / playback / delete original+processed | AudioSession.record/play/stop; processed_route | parec/paplay | microphone | stream | temporary file | N/A | MicrophoneTest | Tested with simulation | AudioSession + fake-session bridge tests: opt-in, cancel before preparation completes, source removal, cleanup. No real microphone capture. |
| Audio | Direction-specific presets / import / bypass / effects launch | audio_pipeline.load_preset; backend.import_preset; operations.plan_for | EasyEffects | audio | cache | software | cache | AudioPage / effects | Implemented | Existing direction-safe preset/import services; audio service tests and QML controls. Live effect changes not run. |
| Shared | Persistent drafts / conflicts / discard / submission states | DraftStore; operations.perform | all supported | all | yes | explicit apply | backend-dependent | EditorController | Tested with simulation | Shared control/plan tests and QML functional smoke; real setting writes not run. |
| Backups | Create/read both formats / model+checksum / preview fields | backups; capability_backup | existing providers | supported | yes | local file | N/A | BackupsPage | Tested with simulation | Existing backup facade tests; no real restore. |
| Backups | Selective restore / private snapshot / partial result / cancel | backups.restore; capability_backup.restore | existing providers | supported | yes | explicit restore | backend-dependent | BackupsPage | Tested with simulation | Existing backup facade tests; no real restore. |
| Diagnostics | Inventory / capabilities / faults / component versions | diagnostics.collect; reports.build_report | all | all | yes | no | N/A | DiagnosticsPage | Tested with simulation | QML inventory and explicit component collection; optional dependencies remain independent. |
| Diagnostics | Preview / copy / export anonymized JSON | reports.build_report; drafts.atomic_json | none | all | yes | local file | N/A | DiagnosticsPage | Tested with simulation | Existing allowlisted reports; QML JSON preview and temporary-file export test. Native picker/clipboard interaction is manual. |
| Shell | RU/EN / reduce motion / builtin filter / name and artwork | i18n; GuiPreferences; DeviceArtworkProvider | none | all | yes | local only | N/A | SettingsPage / DevicePage | Tested with real read-only hardware | Hardware writes are not authorized for this migration. |
| Shared | Hotplug / battery / charging / connection state | DeviceMonitor; battery_service | existing readers | all | yes | no | device/cache distinguished | DeviceBridge | Tested with real read-only hardware | Hardware writes are not authorized for this migration. |

## Migration checkpoint — 2026-10-26

The QML editors now use `control_service.py`, the original adapter plans, `operations.perform`, `DraftStore`, `AudioSession`, backup services and public report builder. `DeviceManager` and hardware protocols were not rewritten. GTK uses the extracted control labels, mouse actions and result wording too. The root `keyboard_layouts.py` holds data shared with the offline illustration renderer; no renderer is imported at runtime.

Completed software paths: mouse DPI/stage/rate/profiles/ratbag buttons and macros/LED zones; generic provider scalars and RGB; Ace68 key selection, six validated key parameters, profiles and global lighting; scoped G515 saved controls; audio endpoints/default/volume/mute; opt-in microphone resources; EasyEffects controls; diagnostics and export. Existing QML backup presentation and GTK fallback remain.

Safety: one existing shared executor serializes device operations; active restore/editor/audio writes cannot queue conflicting writes. Device binding and Epoch checks guard queued commands and readback. Mode/profile/stage changes run separately before remaining drafts. For ratbag RGB the color-capable mode precedes color; color is not sent for off/cycle. If `cycle` reports no color, switching to `on`/`breathing` requires an explicitly selected color. Confirmed fields alone clear drafts; sent/unverified results retain them. User edits after matching cache readback start from the displayed observation, without upgrading cache to hardware truth. Audio property events refresh data without cancelling their own write; endpoint removal/rebind invalidates the operation and closes test resources.

## Verification and remaining gate

- `scripts/check.py`: full suite and compilation; final results recorded in [qml-migration-progress.md](qml-migration-progress.md).
- `scripts/qml_functional_smoke.py`: real service plans with in-memory transports, keyboard input and Apply click, DPI/rate/profile/macro/LED/Ace68/audio/report paths; real runner forbidden. RU/EN at 640×780, 800×780, 1000×780, 1280×800, 1600×900, 1920×1080.
- `scripts/qml_readonly_smoke.py --wayland`: G502, K7, Ace68 and PRO X navigation with a write/capture prohibition. The earlier K7 configuration failure was followed by a successful validated read-only configuration probe on 2026-10-27. This does not validate K7 writes or indicator behavior.
- GTK GUI and 15-scenario simulation smoke pass. The pre-existing GTK `peripheral_smoke.py` null WidgetPaintable snapshot after a page transition remains an unresolved capture gate; unchanged repeated retries were intentionally avoided.
- No real setting write, restore, microphone recording, firmware/reset/calibration or permission change was performed. G515 and other optional providers lack current physical coverage. Native file-picker selection and clipboard copy still need a manual pass.
- Generic keyboard previews now use shared accurate ANSI layouts; the old manual ISO illustration is a documented presentation difference, with no hardware programming claim.

**Historical pre-cutover gate:** the later user-authorized cutover and software checks are recorded in [qml-cutover.md](qml-cutover.md). Outstanding hardware/manual checks remain device-specific limitations, not proof of a missing GTK-only software action.

Stabilization after `86bd4f9`: QML mouse callouts now use the canonical GTK
schematic coordinates and preserve interactive selection at 640/1000 px.
Lighting labels distinguish daemon cache from device verification; actual G502
cache read reported `000000` for both LED zones, without physical readback.
Audio selectors show separate server endpoint descriptions and track default
changes while retaining an explicit preview selection. Empty/missing/error
preset states block Apply. See `docs/qml-migration-progress.md` for screenshot
and test evidence. None of these changes upgrades the hardware-write or
EasyEffects rows to verified status; the GTK default gate remains open.

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

G515 availability correction (2026-10-29): the former positive name-only ROOT
ping prerequisite is superseded by scoped read-only Solaar queries, cache
fallback and device-bound command guards. RGB control Off does not hide the
editor. Details and validation limits: [g515-settings-fix.md](g515-settings-fix.md).

## EWEADN S9 extension, 2026-10-29

This extends the former read-only manufacturer identification; it does not
upgrade the overall GTK/QML release gate. See [S9 evidence/limitations](eweadn-s9.md).

| Action | Shared API / backend | QML | Status / verification | Limitation |
|---|---|---|---|---|
| Read device configuration | `EweadnAdapter` / ByteTech pages | `EweadnPanel` | Tested with simulation | No physical S9 available |
| DPI stages/colors/count/active | `setting_plan`, `dpi_config` | DPI cards | Tested with simulation, full mock readback | X/Y enable not exposed |
| Polling/performance/sensor | `setting_plan`, `sensor_config` | Performance / Sensor | Tested with simulation, unknown bits preserved | Wired mode firmware-controlled; native limits |
| Mouse/key/media assignment | `setting_plan`, `button_bindings` | 5 interactive markers + action chooser | Tested with simulation and QTest | Only device-observed slots; keep working LMB |
| Macro capture/library | Existing `DraftStore` / `macro_library` | `MacroWindow` | Tested with simulation and QTest | Native bank upload blocked, OTA format risk |
| Factory reset | `reset_plan` | Explicit confirmation dialog | Tested with simulation | Sent/unverified, macro bank not backed up |
| Battery/profile/FW observation | SDK `status` / guarded `read` | Header / Other | Tested with simulation | Native profile index read-only |
| Artwork | `DeviceArtworkProvider` | Dashboard / editor | Qt/librsvg, QML 1×/2× | Supplied visual, no CAD accuracy claim |
| Application scale | Existing GUI preferences | Settings | Tested with simulation | Requires QML restart; GTK unchanged |

GTK retains its generic read-only S9 overview and points to the QML editor.
Neither simulated writes nor SDK code inspection are hardware verification.
