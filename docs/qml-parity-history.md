# GTK / QML parity gate

GTK remains the default UI. Do not change the default until all applicable rows
below are `Present` and tested, including real-session checks.

| Area | GTK status | QML status | Verification |
|---|---|---|---|
| Device dashboard / connected inventory | Present | Partial: dashboard cards, search, categories and built-in filter | QML offscreen runtime + live DeviceManager snapshot; visual captures at 640/1000/1280/1920 |
| Stable hotplug and battery presentation | Present | Partial: DeviceMonitor events refresh stable-ID rows | Stable-ID model unit test and simulation smoke; physical hotplug/charging events not exercised |
| Mouse settings: DPI, polling, buttons, macros, RGB, profiles | Present | Not present | Phase 2 |
| Ace68-II keyboard editing and magnetic settings | Present | Not present | Phase 2 |
| Audio output and microphone controls | Present | Not present | Phase 2 |
| Draft editing and operation verification | Present | Not present | Phase 2 |
| Backup, restore preview and selective restore | Present | Present: service-backed QML presentation; retained GTK fallback | 18 facade tests; isolated QML backup smoke with both formats; real Wayland UI; physical writes/native picker selection not exercised |
| Diagnostics and anonymized report export | Present | Partial: read-only backend summary and discovered capabilities; no report export | Offscreen navigation smoke; export awaits Phase 2 |
| RU / EN | Present | Partial: shared translation lookup for shell | RU/EN offscreen screenshots and translation switch exercised |
| Simulation isolation | Present | Implemented through existing simulation service | QML simulation smoke passed; no hardware writes exposed |
| GTK default / GTK fallback | Present | GTK remains default; QML opt-in | `app.py --ui qml --simulate --smoke` passes; GTK launch blocked by unavailable sandbox display |
| Arch packaging / source installation | Present | Manifest and package tree updated | Local `makepkg --nodeps` package build passed; QML files present in package |

## Historical gate result (before approved host-session access)

**Blocked at Phase 1.** PySide6 6.12.0 is installed in the current Arch environment
with the user's explicit pacman authorization. Latest checks: `qmllint`,
compilation, all 214 unit tests, `scripts/check.py`, and QML offscreen smoke pass.
The gallery renders a simulation-backed Dashboard at 640/800/1000/1280/1600/1920
in RU and EN, plus device details and battery states. The GTK-backed
`scripts/gui_smoke.py`, `scripts/simulation_smoke.py` and
`scripts/peripheral_smoke.py` cannot initialize GTK because the sandbox cannot
access the display and `/run/user/1000/dconf` is read-only.

A real Qt Wayland launch was attempted without changing session configuration;
Qt aborted while creating its platform integration. `hyprctl` also times out,
although the Wayland socket is visible. This does not establish that the QML
application works in the actual Hyprland session. GTK remains the default and
Phase 2 is not started. No hardware writes occurred.

Visual snapshots reviewed: [before GTK](screenshots/README.md#historical-reviews),
[QML RU 1000](screenshots/README.md#historical-reviews),
[QML RU 640](screenshots/README.md#historical-reviews),
[QML RU 1920](screenshots/README.md#historical-reviews),
[QML EN 1000](screenshots/README.md#historical-reviews),
[QML mouse detail](screenshots/README.md#historical-reviews),
and [device artwork contact sheet](screenshots/README.md#historical-reviews).
The workspace contains no G HUB reference image, so a direct pixel/design
comparison could not be documented.


2026-10-25 layered-art follow-up: QML Dashboard uses prebuilt 2D PNGs, with
three native review passes plus final fitting, 46 image checks, and 227 unit
tests passing. Opaque fixture art is measured >=45% card height in RU/EN at all
requested widths. Updated screenshots: screenshots/redesign/illustrations/after/.
This does not advance the editor/restore/audio parity rows or satisfy the real
Hyprland session gate. GTK remains default; its image-loading path now shares
the prebuilt PNG provider, but GTK smoke initialization remains unavailable in
this sandbox. See docs/illustration-pipeline.md.

## Header stage 1 / separate backup stage 1b

| Item | Status | Evidence |
|---|---|---|
| Fixed header, real inventory timestamp/counts, RU/EN | Present offscreen | Header bridge tests, keyboard Space switching, untruncated text checks, RU/EN captures |
| Settings and About destinations | Partial | Session controls only; captured and navigation-smoked |
| Backups menu entry | GTK fallback | Detached explicit launcher tested with fake QProcess; no real restore run |
| QML backup/restore presentation | Not present — stage 1b | Awaiting header acceptance; original services and GTK dialog retained |

Stage 1b must test both existing formats, selected fields, checksum/model checks,
source labels, fresh-state revalidation, private pre-restore snapshot, generation
guards, partial/unverified outcomes and isolated simulate execution. Successful
header checks do not satisfy backup, device editor or real-session parity.

### Current stage 1 host-session result

Approved host-session access now permits the QML Wayland smoke with both real
DeviceManager data and explicit simulation. Header menu/Settings/About and
Dashboard/detail/diagnostics navigation pass. A native Wayland screenshot was
reviewed at 1.25 DPR; see screenshots/redesign/header/validation.md. GTK GUI,
15-scenario simulation, peripheral smoke (including 640x780) and a new isolated
GTK backup-entry smoke pass. The earlier restricted-process failures above are
historical environment limitations, not the latest overall test result.

Fixed GTK DeviceArt's unsupported filename construction property and tightened
smokes against partial Dashboard construction. This changes presentation only.
Backup/editor/audio parity rows remain incomplete. QML backup stage 1b still
requires user acceptance of the header and its own independent checklist/tests.
GTK remains default; no hardware writes were performed.

## Stage 1b backup presentation

| Requirement | QML verification |
|---|---|
| Export/read both unchanged formats | Provider/legacy facade tests; original validators |
| Preview current/desired and select individual fields | Model and keyboard QML smoke |
| Model and checksum before mutation | Wrong-model/checksum tests; no writes |
| Pre-restore private snapshot | Service-backed 0600 snapshot checked in test |
| Sources: device/cache/local/audio server | Separate facade tests and visible row labels |
| Partial/unconfirmed outcomes and returned value/source | Partial + readback-timeout/cache tests; screenshots |
| Disconnect/rebind/shutdown cancellation | Epoch guard tests; selection retained by backup hash |
| Explicit restore only; simulation isolation | Strict real-runner prohibition; no writes while opening/previewing |
| GTK retained | Open in GTK uses the existing separate entry |

User accepted stage 1 and removed further acceptance pauses. Continue stages 2–4
when this stage's checks pass. Backup services, protocols and DeviceManager are
unchanged; real device restore was intentionally not run. Native OS picker
selection is not automated: integration smoke injects the selected local path.

## Dashboard UI iteration stages 2–4

Toolbar/cards/artwork now have automated native Wayland + offscreen visual
matrices, stable battery deltas, event/adaptive polling, source captions, private
UI preferences and image-source recovery. Backups stage 1b remains service-backed
and GTK fallback remains available. These checks **do not close** the missing
mouse, magnetic-keyboard and audio editor parity rows. GTK remains the default;
QML details are intentionally read-only apart from local name/artwork selection
and the explicitly actioned backup workflow. No phase-4 default switch is made.

## Iteration5 visual acceptance candidate

A–F Dashboard/artwork checks passed (288 tests,52 PNG checks, offscreen/native
Wayland matrices and retained GTK smokes). See iteration5-report.md for actual
output, final user-selected iteration4 silhouettes and remaining hardware limits.
This is submitted for visual acceptance, not a claim of full editor parity. GTK
remains default; no source backend/DeviceManager/backup logic or hardware writes.
