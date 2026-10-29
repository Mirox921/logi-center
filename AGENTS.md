# Working on Logi Center

Repository layout: production code is under `src/logi_center`; canonical assets
are in `assets`. See docs/development/architecture.md for module ownership,
source/installed launch paths and tests/unit, tests/integration, tests/hardware.
Bare module names in historical notes below refer to their corresponding
package modules; do not recreate flat runtime copies. `app.py` is a launch shim.
Offline artwork tools now live in scripts/artwork/illustrations and run as
`python -m scripts.artwork.illustrations.checks`; they are never shipped at runtime.

Python 3 / Qt6 / QML Linux desktop application. `app.py` launches QML; `backend.py` contains legacy CLI/read adapters. New operation/backup/discovery/audio modules separate hardware work from widgets. `i18n.py` contains Russian → English translations. `install.py` copies runtime modules into the user's data directory. Tests run without hardware using injectable runners/transports.

- Read `docs/implementation-progress.md` when continuing; inspect only affected code and diffs.
- Run `python -m unittest -v`; syntax: `python -m compileall -q .`. GUI smoke requires a live desktop: `python app.py --smoke` (no writes or recording).
- Changes to runtime modules require updating the installer and CI checks. Keep Russian and English UI usable.
- All hardware writes require explicit UI action. Exit code zero means sent, not verified. Readback needs backend/parameter-specific support; cached libratbag/Solaar values are not optical RGB confirmation.
- Never use full `solaar config/show` enumeration on app startup: this build may trigger RGB shutdown cleanup. G515 uses scoped allowlisted single-setting reads through the guarded `solaar_write.py --read-only` process, with cache fallback. The name-only sysfs ROOT ping is advisory, not a gate for receiver-connected G515. Do not modify installed backend packages.
- Do not change udev rules, global configuration or permissions. Do not record audio without explicit user action; test clips must be temporary and cleaned up.
- Backups must label device reads vs daemon cache vs local preferences, validate device model and checksum before writing, save pre-restore state, and report partial/unverified outcomes honestly.
- Serialize writes; use generation/cancellation guards for disconnects, rebinds and shutdown. No subprocess waits on GTK's main thread.
- Keep raw HID identifiers, user paths, tokens and recordings out of diagnostic reports/repository. Existing private backups are outside the project.
- No new release or external publication is implied by a code change. Keep logical local commits; preserve unrelated working changes.

Universal architecture: `devices.py` adapter registry/capability inventory; `device_ui.py` shared presentation; `drafts.py` private base/desired state; `reports.py` allowlisted public JSON; `solaar_adapter.py` explicit scalar probes. Read `docs/universal-progress.md` for this cycle. `--simulate` must stay isolated from real command execution. Never merge units by model/VID/PID alone; require exact physical identity or unique candidates/selectors. Drafts and submitted-unverified values must survive refresh. Arch recipe is local; `scripts/prepare-arch.py` supplies a checksummed source archive, never installs.

Backend expansion: read `docs/backend-expansion-progress.md` and `docs/backend-support.md`. `sdk_worker.py` isolates optional Python APIs/HID ioctls with existing execution deadlines. Missing bindings never become mandatory imports. MCHOSE upstream `Config::read` can switch profiles: do not invoke its `show` automatically. Built-in reads never recover by setting a profile. Writes require validated descriptors/identity, HID-instance selector, private pre-write snapshot and field-specific readback; no blind retries. OpenRGB/OpenRazer are conservatively cache-sourced; ckb-next detection is read-only. DeviceManager owns RGB routing, including legacy restore guards. `capability_backup.py` is a separate v1 format; never execute commands from files. The earlier denied K7 access status is superseded by docs/mchose-devices-progress.md: approved interface-scoped udev access and reversible writes/readback. Use `python -m unittest -q`, `scripts/gui_smoke.py`, and `scripts/simulation_smoke.py` (14 scenarios; no real I/O) and prepare a fresh Arch source package after runtime-manifest changes.

MCHOSE keyboard cycle: read `docs/mchose-devices-progress.md`. `ace68_protocol.py` / `ace68_adapter.py` are separate from the mouse protocol; exact 41e4:2116 interface 01, firmware 121 writes only. Never send mouse reports to Ace68. Profile-scoped key drafts and commands must remain separate; cross-profile backup comparison requires a new preview after profile switching. RGB palette must stay independent from stored color. Example udev rule ships as documentation only. User explicitly approved the installed narrow rule and reversible hardware tests in this session; no firmware/reset/calibration authorization is inferred.

Category/UI cycle: read docs/category-ui-progress.md. Main control pages use DeviceManager.active and peripheral_ui.py, not a backend-specific inventory. device_status.py must stay GTK-free for CI. Never reintroduce history-only G515 cards or mouse receiver auxiliary keyboards. Battery refresh must update observed capabilities/labels without rebuilding editors. scripts/peripheral_smoke.py captures only its own GTK window and does not write device settings.

Inventory detail rows use Adw.ExpanderRow, collapsed by default; preserve expanded state by stable device ID. Keep pseudo HID `interface` records out of user-facing inventory. Battery icons derive from an explicit positive charging capability; never imply charging from percent alone.

Current GUI policy (user-authorized QML cutover, 2026-10-29): Qt6/QML is the
only in-tree interface and the default for `python app.py` / desktop launch.
The pre-cutover GTK tree is archived separately; see docs/qml-cutover.md for
its commit/checksum and restoration instructions. Do not reintroduce GTK UI
imports, GTK package dependencies or a secondary GTK backup window. Native
BackupsPage uses the unchanged backup services. `--ui qml` remains compatible;
`--ui gtk` explains that the archived version must be restored. PySide6,
Qt Quick/Controls and SVG are required GUI dependencies. Gio/GLib in the shared
D-Bus readers are independent of GTK and remain available through PyGObject.
Shared services remain GUI-independent. Missing Qt must give an actionable
error, never silently choose another interface. `--simulate` stays isolated.
Earlier GTK-default/fallback and GTK-smoke notes below describe historical
iterations and are superseded by this policy. Hardware validation limits
remain in force; software cutover does not certify every device/firmware.
Qt bridge is presentation-only: use DeviceManager, existing adapters, guarded
plans and the shared executor. Update list rows by stable device ID. Do not
install system packages or alter desktop settings just to pass GUI checks.

QML artwork/design iteration: use `illustrations/` and `scripts/generate_device_artwork.py` for project-authored generic class illustrations; preserve class and revision accuracy. Review `scripts/icon_gallery.py` and `scripts/design_gallery.py` outputs before claiming visual fixes. The renderer is offline only; the QML frontend loads committed transparent PNGs and never imports Cairo or renders at startup. QML is the default; the GTK baseline is archived. Both Dashboards use committed layered 2D PNGs; mouse_art.py is retained only for the interactive GTK button diagram. Keep illustrations/ offline and out of install.py runtime modules. No exact-model product art is claimed. Fonts are bundled with license/source notices; `scripts/check_fonts.py` verifies Qt family registration and Cyrillic/Latin glyph coverage. See `docs/illustration-pipeline.md`, `docs/design-language.md` and latest visual notes in `docs/implementation-progress.md`.

Layered 2D art: canvas 512x320 / 1024x640; canonical hyphenated PNG filenames, neutral materials derived from Theme tokens. Run python -m illustrations.checks and scripts/illustration_dashboard.py --stage after for image quality and actual silhouette measurements, not just widget size. Latest gate:320x240 shared scenes, mouse75–84% height / keyboard~85% width; user explicitly chose independent per-model fitting. Preserve before screenshots. Class/variant selection uses typed metadata and backend routes, not display-name guesses. User images now go to device-images/<local identity hash>.*; keep old device-artwork preferences readable. Never package unlicensed workspace reference photos.

Header stage 1 is accepted. Stage 1b uses the QML backup facade over unchanged
services, with explicit restore, selected-field preview, private pre-restore
snapshot and Epoch cancellation guards. The GTK entry remains an independent
fallback; closing QML must not kill an active GTK restore. Do not change backups.py/capability_backup.py. Runtime
QML/brand resources are copied recursively; check required files in installer
and Arch tests. Stage screenshots: docs/screenshots/redesign/header/.

User approved autonomous continuation after stage 1: do not request intermediate
design acceptance for stages 1b–4. Test and commit each stage before continuing.
Backup GUI smoke: scripts/qml_backup_smoke.py (isolated memory I/O); --wayland
requires host-session access. Preserve selection by stable binding + backup hash
on re-preview; cached/local/server/device sources and unconfirmed results remain
distinct. No backup service or hardware backend changes are authorized here.

Stage 3: battery_service.py shares existing read-only GTK polling with QML;
battery_presentation.py is pure evidence/TTL display logic. Never promote a
backend cache to a physical read. Simulated bridge poll timers stay stopped.
Generated geometry.json is offline metadata, not runtime Cairo work; update it
when regenerating PNGs. Duplicate names get source captions, never guessed merges.

Iteration5: read docs/iteration5-report.md before further visual edits. Latest
user reference is iteration4 mouse shapes; stronger shape-cycle2 curves are
rejected. Wireless/gaming have slightly larger lighter integrated side controls.
Broad fading palm-rest rectangle is rejected: pointer_generic is a neutral
touch surface, touchpad requires positive evidence. Submit visuals for acceptance;
do not infer user approval or switch GTK default.

QML typography: see docs/typography-render.md. The QML launcher selects grayscale
distance-field AA before importing Qt; preserve `StyledText` and the existing Qt rendering policy. Use --debug-text for family/DPR diagnostics and
scripts/text_render_check.py for nearest-neighbour Wayland comparisons.

## Repository and screenshot hygiene

Keep runtime code/assets/licenses, tests/fixtures and protocol evidence in Git.
Only curated English release screenshots belong in docs/screenshots/releases/;
generated visual reviews, local reference captures, caches, agent tooling and
built archives/packages stay ignored or outside the repository. Four canonical
mouse silhouette fixtures live in tests/fixtures/artwork/iteration4. Historical
screenshot links may use immutable pre-cleanup commits; do not regenerate or
recommit the old review trees. Release archives include only the curated gallery.

## Definition of Done and efficient verification

A task is complete when its explicitly requested functional requirements are implemented, relevant targeted tests pass, no known critical regression remains, required hardware/data safeguards hold, the change fits the existing architecture, and any remaining noncritical limitations are documented. Do not add acceptance criteria after these requirements are met. Subjective perfection is not required: minor spacing, proportion, typography or decorative differences do not block a functionally correct, visually acceptable result unless the task explicitly makes them measurable requirements.

Stop when the Definition of Done is satisfied. Do not continue improving something only because it could theoretically be better. For the same noncritical issue, allow an initial implementation and verification plus at most two corrective iterations. If it is acceptable, finish; otherwise document it and finish the stage. If it blocks required functionality, report the blocker. Do not alternate nearly identical edits and checks, or polish without a measurable acceptance criterion. These limits never relax safety requirements.

Use verification proportionate to the change:

- **Targeted:** run only relevant tests after a localized change (for example, mouse, keyboard, audio, backend, or focused QML loading/rendering checks). Do not run the full suite after every small edit.
- **Integration:** broaden checks when shared interfaces, DeviceManager behavior, multiple subsystems, hardware command execution, serialization or backup/restore behavior change.
- **Stage completion:** run the complete relevant suite once at the end of a major implementation stage. Repeat only if later changes could invalidate the result or a failure needs revalidation. Never rerun unchanged successful tests without a concrete reason.

Smoke-test selection:

- `python scripts/peripheral_smoke.py`: peripheral functionality, backend behavior or device integration changes; not cosmetic QML-only changes.
- `python scripts/gui_smoke.py`: meaningful GUI integration changes. For isolated visual edits, use a focused check and avoid restarting the whole GUI for insignificant styling changes.
- `python scripts/simulation_smoke.py`: simulation behavior or relevant shared logic changes; not unrelated changes.

Investigate a smoke failure before retrying. Do not blindly extend timeouts or repeat the same failure. Distinguish application defects from environment limits; after repeated identical environment failures, stop unless a concrete change can address them.

For GTK, Qt/QML, SVG and compositor rendering, use one primary visual verification, a representative viewport during development, and at most two corrective rendering iterations for each noncritical issue. Prefer offscreen QML checks for routine validation; use native Wayland/Hyprland only when compositor behavior is part of the requirement. Reuse screenshots/findings while inputs remain unchanged. Check broader responsive behavior at major UI stage completion when required, rather than after every minor edit. Prioritize broken behavior, inaccessible controls, essential content that overlaps/clips/is unreadable, incorrect device information, then significant responsive failures. Minor polish is nonblocking unless explicitly required; do not chase pixel-perfect alignment after acceptance.

Reduce context overhead: use targeted searches and `git diff`; read only needed file sections. Before rereading guidance or large modules, check whether relevant contents are already known and unchanged. Re-read when they changed or new information is needed. Avoid repeated repository-wide exploration, duplicate environment checks, repeated launches and large output dumps without a concrete reason. Batch independent read-only diagnostics where practical. Keep progress and completion reports concise.

Keep scope focused. Do not add unrelated refactors, redesigns, abstraction layers, dependencies or file reorganizations. Record unrelated opportunities as follow-ups; expand only when needed to satisfy the requested behavior safely.

All existing hardware/data safety requirements remain mandatory regardless of verification limits: explicit user confirmation before hardware writes; required sequential command execution; identity/connection validation and stale-operation protection; supported readback; safe unsupported-capability handling; accurate device/battery state; draft/backup integrity; partial-operation error handling; no fabricated support; and the archived GTK recovery baseline. For a critical failure, stop the affected operation, preserve a safe state and report the blocker. Never claim success without sufficient evidence.

At the end of each substantial task, report implemented changes, checks run and results, known limitations and unresolved blockers, plus a suggested next step only when one is needed.

Functional QML migration: control_service.py and keyboard_layouts.py are toolkit-free shared data/planning helpers. qml_ui/bridge/editor.py, audio.py and diagnostics.py delegate to existing services; keep their shared-executor, binding/Epoch, draft and provenance guards. Current tests, native screenshots and remaining gates (including the K7 read failure) are in docs/qml-migration-progress.md and docs/qml-parity.md. QML is the sole in-tree GUI. Use scripts/qml_functional_smoke.py for isolated fake writes and scripts/qml_readonly_smoke.py only for explicitly read-only live navigation.
