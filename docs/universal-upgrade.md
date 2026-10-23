# Universal peripheral manager: implementation and readiness

This development cycle extends v0.3.0 in place. It does not claim support for every Linux peripheral or physical verification of unavailable devices. No firmware/reset, system permission/configuration changes, package installation, audio capture, forced unplug/session restart, external publication or AUR upload was performed.

## Stage results

| Requested stage | Result and practical scope |
| --- | --- |
| 1. Audit | Completed. Existing CLI/verification/backup/audio/event integrations retained. Hardcoded G515 path, fixed batteries, overwritten audio names, missing drafts and missing package were identified. |
| 2. Universal devices | Extensible adapter registry, capability/evidence inventory, conservative identity merge, per-backend selectors, common provider-owned scalar control plans. Input keyboards/mice, ratbag mice, PulseAudio/PipeWire endpoints, HeadsetControl and saved Solaar records. Hardware-specific feature coverage remains partial. |
| 3. Reliable operations | Typed local/unsupported/access results added; cached/device/server observations remain distinct. Existing deadlines/cancellation/serialized writes retained. Ratbag writes recheck an exact unique selector; ambiguous/missing selectors cannot fall back to a model name. No blind retry/fan-out. |
| 4. Draft retention | Private atomic persistent drafts with base/desired/submission state, conflict markers and explicit current-value reset. Choices, microphone/output volume, G515/mouse RGB and visual assignment/macro drafts retained. Signatures rebuild changed pages rather than every page. Tab/scroll/mouse selection retained; a changed page still rebuilds its widget subtree. |
| 5. Editors | Existing mouse editors extended with persistent state/type checks and neutral unknown-model rendering. Generic keyboard reference diagram offers manual ANSI/ISO/TKL/full-size views; it does not pretend to detect physical layout or provide unsupported per-key programming. Audio testing remains opt-in, with real route checks and temporary files; leaving the audio tab stops capture/playback. |
| 6. Backups | Existing version-1 mouse/audio/G515 backups remain compatible. Added old/new/action comparison and individual setting selection, retaining integrity/model checks, pre-restore snapshots and partial-stop results. Arbitrary keyboard maps, all headset hardware settings and full firmware images remain unavailable. |
| 7. Diagnostics | Capability details, sources/timestamps/evidence and operation state. Preview/copy/export allowlisted JSON; no automatic sending. Missing/unavailable backend, permissions and other typed faults retained. Public exports exclude values/macros/drafts/serials/physical paths/endpoint IDs; review before sharing. |
| 8. Tests | 103 hardware-free tests plus real-session GTK smoke and isolated simulation checks. No new physical setting-write, restore, actual unplug/reconnect or microphone capture test is claimed. |
| 9. Arch | PKGBUILD, required/optional dependencies, desktop entry and original SVG icon. Local source builder generates a checksum; package built with makepkg without installing it. Dependency checks were deliberately skipped in this build; namcap unavailable. |
| 10. Skills/context | Official catalog reviewed; no directly useful additional GTK/HID skill was installed. Existing project skill updated/validated, AGENTS retained and universal-progress added. |
| 11. UI polish | Neutral Devices/Keyboards/Audio tabs, real audio names, dynamic kernel battery indicators across manufacturers, capability-driven editors, unavailable controls and draft conflicts. Very large device sets and varied desktop scaling still need wider testing. |

## Architecture and adding an adapter

`devices.py` defines Device, Capability, Adapter and DeviceManager. Adapters discover records and capabilities; writable common scalar settings expose a provider-owned `Plan` factory. `device_ui.py` builds the common editors from choices/ranges and re-resolves the current capability before applying. Unknown and unsupported are separate. Additional complex editors require a parameter-specific adapter/UI component; a generic API name never enables an unsupported control.

`operations.py` still owns write/readback comparison and result provenance; `execution.py` owns bounded cancellation-aware subprocesses. Cached ratbag matching remains sent/unverified; server volume confirmation is explicitly labelled audio-server confirmation. Device readback is provided only for verified parameter policies, including explicitly probed Solaar boolean/choice settings.

Identity uses resolved physical paths. CLI records lacking a path can link only when the resolved candidate and backend selector are both unique; two identical units are never merged by name or VID/PID alone. Ambiguous records remain separate/diagnosed. Merged records preserve per-backend targets. A conflicting setting requires a selected backend; the same write is never broadcast. Raw identity paths stay internal. There is no automatic write retry or unsafe cross-backend fallback after partial execution.

DeviceManager can reuse detailed, explicitly cached observations when lazy discovery did not query them; timestamps/sources remain unchanged. Physical unplug/replacement validation remains pending. Old task generations are cancelled; the underlying CLI/USB protocol still limits what can be proven atomically about the physical device.

`drafts.py` stores application drafts separately from hardware profiles, EasyEffects presets and backups. It uses 0600 temporary files, fsync and atomic replacement. Unverified submissions retain the desired value; confirmed scalar submissions clear their own draft. A visual editor submission does not discard drafts on other buttons. Drafts may contain sensitive macros and are never included in diagnostic exports.

## Supported categories, without invented model certification

- **Mice:** models supported by the installed libratbag backend, across its supported vendors. DPI/rates/profiles/LED modes are shown only when reported; per-button ActionTypes gate actions/macros. G502/G305 retain specialized artwork; unknown models have neutral reference artwork and no Logitech mark. Unknown capability data stays read-only/diagnostic.
- **Keyboards/input:** standard devices recognized from Linux input key masks, without a guessed hardware control protocol. Saved Solaar records are explicitly local history. Users can request individual scalar probes: backend-enumerated boolean/choice fields become writable with uncached readback. Complex mappings, per-key RGB and non-enumerated ranges stay read-only; dangerous/reset/profile-mode fields cannot be written through this path. The existing isolated G515 lighting path is retained.
- **Headphones/headsets:** standard sound-server volume/mute/default operations for any reported vendor; HeadsetControl capabilities/valid battery values and sidetone when the selector is unambiguous. Hardware EQ/lighting and other advertised HeadsetControl fields are diagnostic-only until parameter-specific plans exist. EasyEffects provides separate software input/output presets, not hardware Blue VO!CE/DTS.
- **Wireless batteries:** kernel Device-scope power supplies without a Logitech manufacturer filter. Kernel reporting quality/connectivity remains a backend limitation.

## Simulation

Run `python app.py --simulate`. Simulated devices are labelled and never mixed with real inventory. The eight scenarios cover basic/gaming mice, RGB/plain keyboards, USB/wireless headsets, a partial backend and disconnect on write. Common capability presentation, actual MouseEditor widgets and operation results are reused. Simulated results are never hardware confirmation; the simulation smoke forbids real CLI calls. Keyboard diagrams are reference layouts even in simulation, and real audio capture is unavailable in this mode.

## Verification and performance

- `python -m unittest -q`: **103 tests pass**; syntax compilation and `git diff --check` pass.
- New tests cover identity/selector collisions, two identical devices, missing capabilities/partial JSON, word-aligned input masks, draft restart/conflict/submission state, individual backup selection, permission/unsupported/local results, explicit Solaar choice probes and dangerous-setting rejection, public report redaction, simulation disconnects and failed backends.
- `python scripts/gui_smoke.py`: independent live GTK instance; fixture-based full generic mouse page/RGB controls, macro draft selection/restoration, dynamic offline header, language switch, diagnostic and restore dialogs, and cancelled recording preparation. No device setting write/capture.
- `python scripts/simulation_smoke.py`: eight simulation scenarios, shared editors, report evidence, zero real CLI calls/capture.
- Read-only host discovery completed without faults at measurement time. G502 had been unplugged, so current mouse application/restore cannot be tested physically. G305/G515 are unavailable. G PRO X sound-server readout is not proof of DSP, playback or capture correctness.
- Reproducible mock benchmark: `python scripts/benchmark_discovery.py`; 50 mice required 151 eager transport calls versus one lazy inventory call (~2.46 ms vs ~0.08 ms locally, mocked transport). Selected-mouse detail is read later. Real-host legacy CLI batch was ~0.127 s; extra inventory/identity using those cached outputs was ~0.020 s. These observations do not establish universal performance improvements or large-scale CPU/memory guarantees.
- Arch: local source/checksum validation, makepkg check() and package() succeed; desktop-file validation succeeds. Package was not installed. First build ran 88 tests at its source revision; final rebuilt snapshot and manifest are recorded in universal-progress.

## Files

New: `devices.py`, `device_ui.py`, `drafts.py`, `keyboard_ui.py`, `reports.py`, `simulation.py`, `solaar_adapter.py`; `test_devices.py`, `test_drafts.py`, `test_reports.py`, `test_solaar_adapter.py`; `scripts/simulation_smoke.py`, `scripts/benchmark_discovery.py`, `scripts/prepare-arch.py`; `packaging/arch/PKGBUILD`, packaging instructions, desktop entry/icon; this report and `docs/universal-progress.md`.

Updated: `app.py`, `backend.py`, `backups.py`, `operations.py`, `execution.py`, `diagnostics.py`, `mouse_editor.py`, `mouse_models.py`, `mouse_art.py`, `i18n.py`, `install.py`, existing backend/backup/operation/i18n tests, diagnostic/GUI scripts, README files, AGENTS and the existing local skill.

## Readiness and stable-release blockers

- **Operations:** stronger software checks and explicit provenance; actual writes, async ratbag commit/resync behavior, hardware readback/restore and USB error recovery still need physical checks.
- **Compatibility/extensibility:** generic backend coverage and registry/common control plans work; no certification of additional physical models. Complex keyboard mappings/RGB and additional headset functions need documented adapters and tests.
- **Performance:** lazy queries and changed-page refresh are measured/covered; large real inventories, CPU/RSS and long-duration use remain unmeasured.
- **UX:** common editors and retained drafts work in smoke tests; narrow/scaled displays, multiple identical physical devices and backend conflicts need user validation. Keyboard geometry is manually selected reference information.
- **Storage/diagnostics:** atomic private drafts/preferences/backups and allowlisted reports are tested. Public reports exclude configuration values by design and require user review; no uploader exists.
- **Packaging:** build and layout are checked; a clean Arch install, upgrades/removal, optional-dependency combinations and namcap are still pending. Existing per-user installs may override a system package; switching methods must be deliberate.

The application is suitable for an expanded **development preview**, not yet a fully verified stable universal hardware manager. The concrete blockers are physical operation/recovery validation, complex keyboard/headset adapter coverage and clean-system installation testing. No unrelated new feature is required just to prolong development.
