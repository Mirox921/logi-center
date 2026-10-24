# MCHOSE mouse and keyboard integration — 2026-10-23

This continues the backend-expansion cycle; its earlier permission-denied hardware status is superseded below. The two protocols and settings remain separate. No firmware, reset, calibration, keyboard-input capture or software Rapid Trigger emulation was performed.

## Hardware identification and access

| Device | USB identity | Configuration interface | Protocol identity |
|---|---|---|---|
| K7 Ultra mouse | RealTek MCHOSE K7 Ultra, 3837:1001, USB release 1432 | interface 02, vendor FF01 feature reports 11/12; ready notifications 13/14 | logical mouse 3837:4150, firmware code 0x5051c |
| Ace 68 keyboard | MCHOSE Ace68-II, 41e4:2116, USB release 0121 | interface 01, exact 64-byte unnumbered input/output descriptor | CZ channel firmware code 121 |

USB release is not proof of PCB, switch revision or firmware. Exact PCB/switch revision remains unknown. Ace68-III 3837:3003 is a different device; its compatibility is not claimed.

Initially both configuration nodes were root-only. The user explicitly approved an interface-scoped udev rule, installed as `/etc/udev/rules.d/70-logi-center-mchose.rules` through graphical administrator authentication. Rules were reloaded and only the two configuration nodes retriggered. Active local user access now works. No blanket hidraw permissions, input-group membership or backend-package changes were made. The example is shipped as documentation, never enabled by an installer automatically.

## Implemented

- `mchose_adapter.py`: wait for inverted ready notifications before GET_FEATURE; bounded legacy fallback, read-only retries, no profile repair. Accept the observed K7 transport/logical identity pair only for that exact receiver identity. DPI up to 42000 for logical PID 4150. Existing private snapshots, unrelated-byte checks and field-specific readback retained.
- `ace68_protocol.py`: independent bounded 55/AA protocol, checksums, offsets, short info replies, chunked reads and per-command deadlines. Read firmware, profile table, active profile config and 128-record trigger table. Decode 68 known keys; preserve switch and precision bits. No mouse reports are used.
- `ace68_adapter.py`: strict VID/PID, configuration-interface descriptor and connection-generation selector; writes restricted to observed firmware 121. Active profile, polling, brightness, supported global RGB modes/palette/color/speed; per-key actuation, RT mode/press/release distances and upper/lower dead zones. Validate an entire selected-key request before writing; private observed pre-write snapshot; compare all observed configuration bytes after writing. No blind write retries.
- Common DeviceManager registry, worker isolation, RGB ownership and operation-result/readback path reused. Collapse only known wired Ace68 composite input siblings; identical units on different ports stay separate. Profile-scoped commands reject stale profiles before writes; per-key results merge into full observed maps.
- `keyboard_ui.py`: selectable 68-key Ace layout, separate observed/draft values, six selected-key controls, explicit Apply and Discard. Draft keys include device/profile/key/field. Selection/drafts survive editor rebuilds; no key input is captured.
- Capability backups: provenance, JSON checksum, atomic writes, active-profile scope, per-key comparison/selection, independent pre-restore snapshot and stop on failure. A backup from another Ace profile first offers profile selection; reopen preview after switching to compare actual destination settings. No incorrect comparison across two profiles.
- RGB color and random-color palette are independent: editing stored RGB never silently disables random colors. RGB readback confirms stored device configuration, not optical appearance.
- Shared inventory labels, keyboard scalar controls, diagnostics, translations, installer and Arch manifest updated. Optional rule packaged under documentation, not `/usr/lib/udev/rules.d`.

## Protocol sources / audit

- [alexfrih/mchose-linux](https://github.com/alexfrih/mchose-linux), MIT, audited commit 75204cc: PROTOCOL.md and CLI. Its `Config::read` may select profile zero; that recovery is deliberately not used. Original testing mainly L7 Pro; do not extrapolate hardware validation to all MCHOSE models.
- [Official MCHOSE HUB](https://www.mchose.store/pages/mchose-hub), linked [M HUB](https://www.mchose.com.cn): audited public CZ channel device table, request/reply classes, Ace68 Pro/II layout mapping, trigger decoding, precision constants and frontend ranges. The exact 41e4:2116 entry and firmware 121 govern this integration. Independently implemented bounded subset; no vendor bundles are distributed.
- [erikenz/mchose-adv](https://github.com/erikenz/mchose-adv), MIT: Ace68-III hidraw-to-uinput advanced-key bridge, not a keyboard configuration API. Not installed or attached to Ace68-II.
- [Luk-Krn/mchose_ace68](https://github.com/Luk-Krn/mchose_ace68): exact-II SignalRGB discovery/layout corroboration. No license file; plugin code not copied. Per-key streaming RGB is not integrated.

Temporary official Babel/Prettier tooling was used under `/tmp` with install scripts disabled and decoder filesystem permissions restricted to temporary assets. No new runtime dependencies or system packages.

## Validation and remaining work

Software: 158 unit tests pass, including notification ordering, logical mouse identity, keyboard packet/checksum/schema, ranges, reserved-bit preservation, unsupported firmware, wrong selectors, stale profiles, mismatch/disconnect, keyboard/mouse backup incompatibility, per-key restoration and cross-profile preview. GTK smoke checks 68 selectable keys, preserved drafts/selection, dialogs, languages and cancellation without writes/capture. Existing 14-scenario GUI simulation smoke passes without real CLI calls. The sandbox cannot access the desktop; GUI checks run on the host session.

Physical tests are recorded separately below. A successful readback proves stored device values, not latency, key travel measured with instruments, RGB optical accuracy or persistence across power loss. No physical unplug/session reboot was performed.

Limitations:

- Ace SOCD/Snap Tap, DKS, Mod Tap, Toggle Key, key remapping, macros and extra layers are diagnostic-only: their stored editing formats have not been validated. No enabled placebo controls.
- Per-key RGB and changing switch type/precision, sensor calibration and firmware updates are unavailable. Conservative actuation range 0.10–3.30 mm; RT uses the current key precision; dead zones 0–0.50 mm. These do not claim the entire vendor marketing range.
- Backup covers readable capabilities of the active profile; not all profiles, macros, full flash or firmware. Private raw pre-write snapshots are safety evidence, not an exposed arbitrary-memory restore facility. Automatic blind rollback after connection loss is deliberately unavailable; partial failure retains the snapshot and stops.
- K7 LOD and performance-flag writes are unavailable. Other MCHOSE models and firmware revisions need their own hardware validation. Mouse RGB is not implemented through the mouse protocol.
- Existing OpenRGB/OpenRazer cache provenance, ckb-next read-only discovery and other backend limits remain in `backend-support.md`.

Release boundary: this report documents the tested subset included in v0.4.0. Persistence after a user-controlled restart/power cycle and the unavailable advanced-key formats remain unverified; the release does not claim a complete Ace68 editor.

### Physical evidence (explicitly approved reversible writes)

- K7: successfully read firmware, DPI/stages, polling, profile, flags, sleep/debounce and battery. DPI 400 → 450 → 400 confirmed by fresh reads; X/Y checked equal before test. Original raw config restored (excluding volatile counter/status bytes). No physical writes of mouse stages, polling, sleep, debounce or profile were tested.
- Ace68-II: firmware 121 and enabled profiles 0/1/2 read. Same-value brightness and Esc actuation writes left all observed raw bytes unchanged.
- Ace: brightness 100 → 99 → 100; Esc actuation 0.30 → 0.31 → 0.30 mm; Esc RT press/release 0.30 → 0.31 → 0.30 mm; RT mode 1 → 2 → 1; upper/lower dead zones 0.15 → 0.16 → 0.15 mm. All changed values confirmed and originals restored.
- Ace: polling 8000 → 4000 → 8000 Hz, effect speed 1 → 2 → 1, random palette → single color → random, stored RGB [255,0,0] → [254,0,0] → [255,0,0], Wave → Static → Wave, profile 0 → 1 → 0. Every change/readback/restore confirmed; each final observed raw base/config/trigger block equals its pre-test state.
- Ace: real JSON export/import, one-step brightness modification, fresh preview and selective restoration through the common backup manager returned `confirmed`; all exported observed settings equal the original afterward. Independent private pre-write/pre-restore snapshots were retained; temporary test export removed.

These are direct hardware protocol checks on these two attached units only. Other keys, other firmware, full-profile restoration, unplug during write and persistence across power cycles remain unverified on hardware. Mock tests cover relevant failure paths without unplugging real devices.

### Integration verification and changed files

`python -m unittest -q`: 158 passed; compileall and git diff whitespace checks passed. Desktop GTK smoke and 14-scenario simulation passed. A local Arch package was built without installation; the optional rule stays under documentation. Runtime installer copies 31 modules, compared byte-for-byte to source. Previous installed Python code was preserved in a private timestamped state-directory backup. No existing GUI process was forcibly restarted; reopen the application to load the new modules.

New: `ace68_adapter.py`, `ace68_protocol.py`, `test_ace68.py`, `packaging/udev/70-logi-center-mchose.rules`, this progress file.

Changed: `app.py`, `devices.py`, `device_ui.py`, `keyboard_ui.py`, `mchose_adapter.py`, `sdk_worker.py`, `capability_backup.py`, `diagnostics.py`, `i18n.py`, `install.py`, `test_backend_expansion.py`, `scripts/gui_smoke.py`, `scripts/diagnose.py`, `scripts/prepare-arch.py`, `packaging/arch/PKGBUILD`, `AGENTS.md`, both READMEs and the three existing progress/support documents linked above.

Public-release blockers: unavailable advanced-key editing, incomplete all-profile/macro backup, power-cycle persistence not checked, and wider revision/model testing. The implemented subset on these two units is physically exercised as documented; the application is still a prerelease, not complete universal hardware support.

Packaging note: the final makepkg run exited successfully but emitted `libfakeroot internal error: payload not recognized!` during tidying. Archive inspection found all owners/groups 0:0, correct launcher permissions, 31 modules and the rule only under documentation. No package was installed. A clean Arch build environment should reproduce packaging before publication.
