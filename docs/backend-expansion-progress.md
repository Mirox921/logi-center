# Backend expansion progress — 2026-10-23

Baseline: clean tree; 104 tests. Python GTK4/libadwaita; DeviceManager/Capability, provider Plan factories, cancellable serialized executor, private drafts, granular ratbag/audio/G515 backups, public-report allowlist and user/Arch installers already existed. Existing functionality was extended, not replaced.

## Implemented and checked

1. **Audit / optional API boundary:** audited five upstream trees (hashes and feature/license matrix in `backend-support.md`). Existing local skill reused and validated; no extra skills installed. `sdk_worker.py` and virtual `logi-sdk` argument vectors reuse bounded execution, process-group cancellation and typed faults. Optional libraries imported only in workers.
2. **MCHOSE documented subset:** `mchose_adapter.py` validates vendor usage/report descriptor, identity/config schema, rate table, supported ranges, exact USB/protocol IDs and current HID generation. No profile-switch recovery while reading. Explicit setting writes save private pre-write snapshots, preserve unknown bytes and detect collateral changes. DPI, enabled-stage selection, rate, profile, debounce/sleep; battery/performance reads. LOD/combined-flag writes and bulk stage replacement are intentionally not implemented.
3. **OpenRGB:** optional loopback SDK; modes (active index distinct from hardware ID), zones/colors, mode-dependent brightness and cache readback. Per-operation fresh client; idle 15-second local socket availability check refreshes after server changes. No server auto-start/network exposure. DeviceManager RGB ownership guards both normal UI and legacy restore writes. Merged provider/kernel input identities preserve distinct receiver slots.
4. **Other providers:** OpenRazer public API supports X/Y DPI, reported polling choices, brightness/battery; daemon bus owner required. rivalcfg profile-driven choice/range subset, no default-as-current values, ambiguous identical units read-only. ckb-next metadata detection only; no FIFO takeover. Existing Logitech/audio adapters preserved.
5. **Backup/UI/diagnostics:** `capability_backup.py` v1 adds checksummed, per-source snapshots, compatibility/range checks, selective current→backup preview, stale-state protection, private pre-restore copy, provider-generated Plans and stop-on-failure. Existing backup format unchanged. Common scalar/color controls keep drafts. Diagnostic window has readable component rows plus redacted JSON preview/export. `scripts/diagnose.py` includes new adapters. Simulation now has 14 explicitly labelled scenarios.
6. **Distribution:** runtime installer manifest includes every new module; PKGBUILD adds optional provider dependencies only. Removed unnecessary ownership preservation during documentation copy, which failed under constrained fakeroot. No system dependency installation, rules/groups changes or AUR publication.

## Evidence

- **132 unittest tests passed** (baseline 104 + 28 new), including malformed/empty configs, mismatch/cache readback, missing SDK, permission errors, exact identity and distinct receiver slots, reused HID names, duplicate controllers/devices, RGB ownership including legacy restore, staged restore/integrity/stale preview, independent Razer axes, OpenRGB active index/zones and preserved/unexpected MCHOSE config bytes.
- `compileall`, `git diff --check` and local skill validation passed.
- Live GTK smoke passed: existing mouse editor/language/audio cancellation/dialogs plus MCHOSE/OpenRGB scalar/color widgets and retained drafts; no setting writes or recording. Simulation GTK smoke passed for 14 devices with all real CLI calls forbidden.
- Real host: K7 Ultra 3837:1001 vendor configuration interface found and merged with its mouse input record; **permission denied** opening hidraw. No identity/config response could be obtained; no physical setting writes were performed. Composite keyboard input remains separately represented rather than guessing a receiver relationship.
- Optional OpenRGB/OpenRazer/rivalcfg Python bindings absent here. Missing-binding probes ~0.06 s each on this machine; this is a measurement, not an overall speedup claim. K7/input read-only discovery ~0.067 s. Existing mock benchmark still yields 1 lazy vs 151 eager transport calls for 50 mice; not real hardware performance.
- Final local Arch package built successfully with all 132 tests. The 29 packaged runtime modules were byte-checked against source. Artifact: `/tmp/logi-center-backends-verified-20261023/logi-center-0.4.0dev-1-any.pkg.tar.zst`; source SHA-256 `eea4b0b173d25f655cdb3e8d3bd3f8ff6e3ad8bac2abae8aa1e9003c06285a86`. `makepkg --nodeps` was used: this is not a clean-chroot dependency test. No package was installed. The existing per-user app was updated with install.py after preserving its 22 old Python modules privately; installed 29-module content matches source. An existing GUI process was not force-restarted.

## Limits / next physical validation

MCHOSE protocol-family support is not physically validated on K7. Current host permissions block all config I/O; do not change udev/groups without explicit permission. New provider writes require hardware testing. OpenRGB/OpenRazer are cache-sourced, not independent hardware proof. Exact matching may leave separate backend records when identity is insufficient. ckb-next is detection only; rivalcfg lacks full DPI-ladder/macros/profile/backup integration; Razer effects/macros/profiles remain unimplemented. Audio's additional upstream ANC/EQ features are diagnostic-only unless already supported by existing adapters. VIA/Vial/unknown HID protocols are not probed. No stable universal-public-release claim.

Remaining work is evidence-driven: approved device access and explicit hardware tests; tests with actual SDK/daemon versions and multiple real units; further vendor editors only with validated APIs. No random vendor commands, package/service installation or publication should be inferred.

## Changed files

- `.agents/skills/logi-hardware-validation/SKILL.md`
- `AGENTS.md`
- `README.md`
- `README.ru.md`
- `app.py`
- `backend.py`
- `capability_backup.py`
- `ckb_adapter.py`
- `device_ui.py`
- `devices.py`
- `diagnostics.py`
- `docs/backend-expansion-progress.md`
- `docs/backend-support.md`
- `docs/implementation-progress.md`
- `docs/third-party/mchose-linux-license.md`
- `docs/universal-progress.md`
- `i18n.py`
- `install.py`
- `mchose_adapter.py`
- `openrazer_adapter.py`
- `openrgb_adapter.py`
- `operations.py`
- `packaging/arch/PKGBUILD`
- `reports.py`
- `rivalcfg_adapter.py`
- `scripts/diagnose.py`
- `scripts/gui_smoke.py`
- `scripts/simulation_smoke.py`
- `sdk_worker.py`
- `simulation.py`
- `test_backend_expansion.py`
- `test_devices.py`
