# Optional backend integration, 2026-10-23

The installed backend and the individual device's reported features decide which editors appear. A brand in an upstream compatibility list does not establish compatibility with Logi Center. Physical setting-write checks are limited to the exact MCHOSE units and parameters listed below; other providers/models are not newly hardware-certified by this release.

| Provider | Implemented in this app | Provenance and limitations |
|---|---|---|
| libratbag/ratbagd | Existing DPI, rates, profiles, buttons/macros, lighting, granular backup | Generic ratbag device support retained. Values can be daemon cache. G502/G305 are existing model illustrations, not newly tested hardware. |
| Solaar | Existing saved-device inventory, explicit single-feature probes, supported scalar edits, G515 controls | Saved history stays local; live probes are explicit. No full startup enumeration. |
| MCHOSE K7 Ultra (exact 3837:1001 identity) | Descriptor + identity/config validation; DPI, six stored stage values, enabled-stage selection, rate, profile, debounce, sleep; battery and performance-flag reads; scalar backup/restore | Direct configuration readback. DPI 400→450→400 physically write/readback tested on the attached unit; other writes remain unverified. LOD and combined flag writes unavailable. See the [hardware report](mchose-devices-progress.md). |
| MCHOSE Ace68-II (exact 41e4:2116, firmware code 121) | Active profile, polling, brightness, supported global RGB, selected-key actuation/Rapid Trigger/dead zones, capability backup/restore | Reversible physical write/readback checks on the attached unit. Advanced-key formats and other revisions unavailable; see [hardware report](mchose-devices-progress.md). |
| OpenRGB SDK | Loopback-only discovery, mode selection, uniform device/zone color, mode-dependent brightness, scalar backup/restore | SDK 0–4 negotiation delegated to openrgb-python; mode/zone features checked at runtime. Mixed/nonuniform palettes are not exported as a single color. Server cache is never hardware proof. No animation streaming, zone resizing, firmware or saved controller-profile writes. |
| OpenRazer | Detected features, independent DPI X/Y, model-reported DPI choices/max, reported polling-rate choices, brightness, battery, scalar backup/restore | Public Python API in worker process; daemon must already own its bus name. No forced service start. Driver/daemon values conservatively treated as cache. RGB effects and macro/profile editing not implemented here. |
| rivalcfg | Supported-profile discovery by exact HID interface; safe choice/range subset: sensitivity/sensitivity1/sensitivity2, polling rate, angle snapping where provided | Write-only API, no invented current values. No full multistage replacement, macros, LED effects, persistent save/reset, firmware or backup. Multiple identical factory targets disable writes. |
| ckb-next | Daemon device metadata, reported feature list | **Detection only**. No command FIFO writes: activation/profile ownership and GUI contention need a dedicated integration. Lighting may separately be available via OpenRGB. |
| HeadsetControl | Existing per-device capability inventory, battery and sidetone where supported | Other advertised features remain diagnostic-only. Duplicate VID/PID selectors disable hardware writes. |
| PulseAudio-compatible PipeWire / PulseAudio | Existing all-vendor output/input volume/mute, audio backup, explicit temporary microphone test | Audio-server confirmation, not headset hardware verification. EasyEffects presets remain software settings. |
| Linux input/udev | Existing generic mouse/keyboard discovery, USB parent identity, hotplug, standard-input status | Standard input does not imply configurable vendor settings. |

## MCHOSE audit and current machine

Audited [mchose-linux](https://github.com/alexfrih/mchose-linux) commit `75204cc`, including `README.md`, `PROTOCOL.md`, `src/{main,proto,hidraw,device,preset,log}.rs` and `install.sh`. MIT; newly published small project; upstream physically tests primarily L7 Pro. K7 support is a protocol-family claim.

Upstream `Config::read` may issue `set_profile(0)` after empty replies. Thus its `show`/backup path is unsuitable for this app's automatic non-mutating discovery. The small built-in protocol subset sends only documented identity/config requests during discovery; it rejects empty/malformed config without reselecting profiles. No CLI install script was executed and no extra Rust toolchain is required.

Historical first discovery of **RealTek MCHOSE K7 Ultra, 3837:1001** returned permission denied on the configuration node. This was later resolved for the exact configuration interface; the resulting identity and physical checks are recorded in [the subsequent MCHOSE report](mchose-devices-progress.md). Do not treat this as support for every MCHOSE model.

Writes are available only after a valid identity/config read, identity agreement with USB, and live setting validation. Every mutation saves a private raw pre-write snapshot, preserves unknown config bytes, checks unrelated-byte changes, and uses readback. No blind write retries. Profile switching deliberately changes the whole active configuration and does not imply a full-profile backup. Selectors include the current HID instance so reused `/dev/hidrawN` names do not authorize stale operations. There is no raw report console, factory reset or firmware path.

## Identity and ownership

Records merge through an exact physical USB parent or the existing conservatively guarded unique-candidate mapping. OpenRazer/OpenRGB can resolve an exact nontrivial serial to a **unique** local USB parent privately; serials are never in public reports. Names alone do not merge records. When identity cannot be established, separate records are safer than controlling the wrong unit.

OpenRGB owns RGB on a confidently merged device. Competing brightness/lighting capabilities are disabled; legacy mouse LED editors and restore writes are guarded too. No automatic fallback write is broadcast. An independently running vendor GUI can still overwrite a setting; this app cannot arbitrate another process's policies. A disappeared/reappeared local OpenRGB server triggers refresh via a bounded 15-second socket availability check, idle while jobs are active or the window is hidden. Each actual SDK operation uses a fresh connection; no persistent per-backend workers.

## Backups and drafts

Existing ratbag/G515/audio format is unchanged. New `logi-center-capability-backup` v1 exports freshly read supported fields from MCHOSE/OpenRGB/OpenRazer and stores per-field provenance. It excludes raw config and unexposed fields. SHA-256 is an integrity check, not authentication. Writes are atomic/private; model/type/VID/PID, version, size, choices and ranges are checked. Preview supports individual selection. Restore re-reads state, refuses stale previews, saves an independent pre-restore copy, derives plans from live capabilities and stops on the first failure. Unsupported/read-only fields are listed as skipped. Automatic rollback is not promised. Conflicting-owner fields cannot be restored through another provider.

Common scalar/color editors use the existing persistent draft store, so refresh does not promote a desired color or write-only default to observed hardware state. Public diagnostics contain feature metadata, not values, raw buffers, serials, paths, macros, drafts or recordings; export is explicit with a preview.

## Arch setup

All new providers are optional. No package was installed by this development session.

- OpenRGB: `openrgb` from Arch; `python-openrgb` from AUR supplies the Python binding. Start/configure the SDK server yourself, listening only on `127.0.0.1:6742`. The app never starts a server or enables external access. Audited binding source `7b23654` (0.3.8); AUR currently packages 0.3.6, which needs integration testing with a real server.
- OpenRazer: Arch `python-openrazer` depends on its daemon/driver stack. Follow [upstream setup](https://openrazer.github.io/); kernel headers/groups may be needed. The app does not change groups or load drivers. Audited source `477f4d6` (pylib reports 3.12.1); installed-version behavior still requires testing.
- rivalcfg: AUR `rivalcfg`; the adapter imports its Python package, so a standalone CLI alone is insufficient. Audited `779ea52`, 4.17.0 family. Follow its packaged access rules; no service required.
- ckb-next: Arch `ckb-next`, daemon metadata under `/dev/input/ckb*`. Audited `e22eaf2`; [upstream installation](https://github.com/ckb-next/ckb-next/wiki/Installation). Read-only integration needs permission to those metadata files.
- MCHOSE: built-in subset needs access to its exact hidraw interface. Consult the audited backend's rules; an administrator must explicitly approve any system change. Running the whole GUI as root is not a workaround.

The local Arch source builder includes all runtime modules and tests; it neither installs the generated package nor publishes to AUR. See [packaging instructions](../packaging/arch/README.md).

## Broader manufacturer research

Use these upstream compatibility lists for **exact models and revisions**, then verify runtime capability detection. Their wider feature coverage is not all implemented here:

- [libratbag device files](https://github.com/libratbag/libratbag/tree/master/data/devices): Logitech, specific ROCCAT/SteelSeries and other listed mice. MIT, maintained DBus service. No inference that an absent Pulsar/Lamzu/Endgame model shares another model's protocol.
- [OpenRGB SDK](https://openrgb.org/sdk.html) and [current device list](https://openrgb.org/devices.html): RGB route for listed HyperX, ASUS, Corsair, ROCCAT, Keychron, Glorious, Redragon, Cooler Master and other controllers. OpenRGB GPL-2.0; Python client GPL-3.0. Neither provides universal DPI/button control. The app does not perform OpenRGB hardware scans itself.
- [OpenRazer model list](https://openrazer.github.io/#devices): exact Razer mice/keyboards/accessories and feature introspection. GPL-2.0-or-later, kernel modules + session daemon + DBus API. May overlap OpenRGB RGB ownership.
- [rivalcfg profiles](https://github.com/flozz/rivalcfg/tree/master/rivalcfg/devices): specific Rival, Sensei, Aerox and Prime revisions. WTFPL, Python/hidapi, no daemon, mostly write-only settings. Maintained with 2026 releases.
- [HeadsetControl compatibility table](https://github.com/Sapd/HeadsetControl#supported-devices): exact Logitech, HyperX, Corsair, SteelSeries and other headsets; HID access, CLI/JSON, no daemon. GPL-3.0. Installed version's capabilities are authoritative; newer upstream ANC/EQ features are not automatically enabled here.
- [VIA supported keyboards](https://caniusevia.com/docs/supported_keyboards/) and [VIA firmware requirements](https://github.com/the-via/website/blob/master/docs/configuring_qmk.md): firmware/keymap support is required, not merely a Keychron/Glorious brand. No automatic VIA/Vial packet probe, flashing, keymap/macro writes or new integration claimed.

No suitable safely audited additional settings API was integrated for unlisted Pulsar/Lamzu/Endgame/Redragon revisions. They retain generic Linux input and any independently discovered OpenRGB functionality. A diagnostic report can establish what is actually present; it is not a device driver.

2026-10-23/24, subsequent MCHOSE cycle: see [mouse/keyboard progress and current hardware evidence](mchose-devices-progress.md). This supersedes the earlier denied-access status for the local K7; Ace68-II uses an independent keyboard adapter.
