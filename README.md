<p align="center">
  <img src="docs/hero.svg" alt="Logi Center — one Linux app for many peripherals" width="100%">
</p>

<p align="center">
  <a href="https://github.com/Mirox921/logi-center/releases/latest"><img src="https://img.shields.io/github/v/release/Mirox921/logi-center?style=for-the-badge&color=6c8cff" alt="Latest release"></a>
  <a href="https://github.com/Mirox921/logi-center/stargazers"><img src="https://img.shields.io/github/stars/Mirox921/logi-center?style=for-the-badge&logo=github&color=f0b84b" alt="GitHub stars"></a>
  <a href="https://github.com/Mirox921/logi-center/releases"><img src="https://img.shields.io/github/downloads/Mirox921/logi-center/total?style=for-the-badge&label=release%20downloads&color=58c99b" alt="Release asset downloads"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-58c99b?style=for-the-badge" alt="MIT license"></a>
</p>

<p align="center"><b>One Linux app. Many peripheral backends.</b><br>
Mouse, keyboard and audio controls in a GTK4/libadwaita desktop app.<br>
<a href="README.ru.md">Русская версия</a> · <a href="https://github.com/Mirox921/logi-center/releases/latest">Download</a> · <a href="https://github.com/Mirox921/logi-center/issues">Report a problem</a></p>

> **Logi Center is no longer Logitech-only.** It combines capabilities from Linux device services and vendor-focused open-source backends. What appears in the app depends on the exact device, its firmware, the installed backend and access permissions. A brand appearing in an upstream project does not mean every model from that brand is supported here.

## At a glance

| | |
|---|---|
| **Device categories** | Mice · keyboards · headsets and system audio |
| **Verified on physical hardware** | MCHOSE K7 Ultra mouse · MCHOSE Ace68-II keyboard · Logitech G502 HERO read-only discovery/backup |
| **Backends** | libratbag, Solaar, MCHOSE adapters, OpenRGB, OpenRazer, rivalcfg, ckb-next, HeadsetControl, PipeWire/PulseAudio and Linux input/udev |
| **Desktop** | GTK 4.10+ · libadwaita · Python · Russian and English |
| **License** | MIT for Logi Center; backend projects keep their own licenses |

## See the app

<table>
  <tr>
    <td width="50%"><a href="docs/screenshots/current-mouse.png"><img src="docs/screenshots/current-mouse.png" alt="Mouse page with a connected MCHOSE K7 Ultra and its available controls" width="100%"></a><br><sub>Mouse page — capabilities come from the selected device and backend.</sub></td>
    <td width="50%"><a href="docs/screenshots/current-keyboard.png"><img src="docs/screenshots/current-keyboard.png" alt="Keyboard page with the MCHOSE Ace68-II key editor" width="100%"></a><br><sub>Keyboard page — Ace68-II key selection and supported actuation controls.</sub></td>
  </tr>
  <tr>
    <td width="50%"><a href="docs/screenshots/current-devices.png"><img src="docs/screenshots/current-devices.png" alt="Device inventory with expandable device and backend diagnostics" width="100%"></a><br><sub>Devices — expandable device cards and backend diagnostics.</sub></td>
    <td width="50%"><a href="docs/screenshots/current-audio.png"><img src="docs/screenshots/current-audio.png" alt="Full-screen audio page with system outputs and headset controls" width="100%"></a><br><sub>Audio — full-screen view of Linux audio devices and headset controls.</sub></td>
  </tr>
</table>

These are real GTK screenshots from the current app. The K7 charge shown is a live read at capture time. The keyboard diagram represents the supported Ace68-II layout; it does not imply that all displayed keys have every possible function.

## What works, and how well it is verified

### Confirmed on physical devices

| Device | Verified in this project | Still not established |
|---|---|---|
| **MCHOSE K7 Ultra** · USB `3837:1001` | Device identity/config reads, DPI and stages, polling, profile and selected flags, debounce/sleep, battery read. DPI was changed `400 → 450 → 400` and confirmed by fresh device reads; the original config was restored. The app displays it in **Mice** and shows the reported battery state. | Other MCHOSE revisions; writes for DPI stages, polling, profile, sleep/debounce; LOD; mouse-protocol RGB; buttons/macros; charging indication on this physical unit. |
| **MCHOSE Ace68-II** · USB `41e4:2116`, firmware code `121` | Active profile, brightness, RGB palette/color/effect/speed, polling, selected-key actuation, Rapid Trigger mode/press/release, dead zones and profile selection. Reversible changes were read back and restored. Selective backup/restore was exercised. | Other Ace68 revisions/firmware, power-cycle persistence, all-profile backup, per-key RGB, SOCD/Snap Tap, DKS, Mod Tap, Toggle Key, remapping and macros. |
| **Logitech G502 HERO** · USB `046d:c08b` | Physical read-only discovery: five profiles, eleven buttons and two lighting zones; JSON backup validation/preview. | Physical setting writes and optical RGB verification. libratbag values may be daemon cache, not proof of the visible device state. |

Only these checks are claimed as hardware validation. The Ace68-II name refers to the detected device/revision represented by the tested USB identity; it does not certify every product sold as “Ace 68”.

### Backend integrations

| Backend | What this app can use | Evidence and boundary |
|---|---|---|
| **libratbag / ratbagd** | Reported mouse DPI, polling, profiles, buttons/macros and lighting controls | Existing generic provider; availability follows ratbag's exact device database. Values can be daemon cache. |
| **Solaar** | Saved Logitech device inventory and explicit supported scalar probes/controls | Uses Solaar's supported devices and settings. Saved history alone is not an active connection. |
| **MCHOSE** | Separate K7 mouse and Ace68-II keyboard adapters | Documented, revision-scoped protocol subset; physical checks above apply only to the named units. |
| **OpenRGB SDK** | Local RGB device/zone/mode discovery, color, and reported brightness | Connects to a user-configured loopback SDK server; no server is started and no external listener is enabled. A cached server value is not optical proof. |
| **OpenRazer** | Features exposed by installed OpenRazer API, including supported DPI/rate/brightness/battery fields | Requires its own driver and daemon. Only runtime-reported capabilities appear; cache provenance is retained. |
| **rivalcfg** | Exact supported SteelSeries HID profiles and a limited set of scalar settings | Mostly write-only; the app does not invent current values or unsupported effects. |
| **ckb-next** | Corsair device metadata and feature discovery | Detection only in this app; no profile or lighting writes are integrated. |
| **HeadsetControl** | Battery and sidetone where the installed version/device supports them | Exact model support is determined by HeadsetControl. |
| **PipeWire / PulseAudio** | System audio device selection, volume, mute and explicit microphone tests | These are sound-server controls, not proof of headset firmware/DSP settings. EasyEffects presets are software processing. |
| **Linux input / udev** | Current mouse/keyboard presence and hotplug signals | Standard input detection does not itself make vendor settings configurable. |

See [backend support, dependencies and limitations](docs/backend-support.md) and the detailed [MCHOSE hardware report](docs/mchose-devices-progress.md). The project does **not** claim universal support for Logitech, Razer, Corsair, SteelSeries or any other manufacturer.

## What changed in v0.4.0

- Reframed the app around physical device categories and discovered capabilities rather than a fixed Logitech-only view.
- Added separate MCHOSE K7 Ultra mouse and Ace68-II keyboard adapters and a shared capability-driven control/backup path.
- Added provider discovery for OpenRGB, OpenRazer, rivalcfg and ckb-next alongside existing libratbag, Solaar, HeadsetControl and Linux audio/input integration.
- Routed connected mice and keyboards to their own pages; separated active devices from saved history and simulation records; retained conservative identity matching to avoid merging identical units by name alone.
- Added device provenance and charging states, compact expandable diagnostic cards, name search and refreshed mouse/keyboard interfaces.
- Expanded mock and hardware-free regression coverage, GTK smoke checks, simulation scenarios and Arch packaging instructions.

Full details and caveats: [v0.4.0 release notes](docs/RELEASE-v0.4.0.md), [implementation progress](docs/implementation-progress.md) and [category/UI verification](docs/category-ui-progress.md).

## Download and install

**Latest stable version: [v0.4.0](https://github.com/Mirox921/logi-center/releases/tag/v0.4.0).** The release page contains the source archive and downloadable assets when published. The project is also prepared for a local Arch Linux package; see [Arch build instructions](packaging/arch/README.md).

For a user-local installation from source:

```sh
git clone https://github.com/Mirox921/logi-center.git
cd logi-center
python install.py
```

The installer places the app under `~/.local/share/logi-center`, adds `~/.local/bin/logi-center` and a desktop entry. It does not need root. Install only the optional backends you need; Logi Center does not install or reconfigure system services, drivers, groups or udev rules automatically.

### Base desktop dependencies (Arch Linux)

```sh
sudo pacman -S --needed python python-gobject python-cairo python-yaml gtk4 libadwaita
```

Backend tools are optional and model-specific. See [the full Arch dependency list](packaging/arch/PKGBUILD) and [backend setup notes](docs/backend-support.md). Do not run the whole GUI as root to work around device permissions.

## Safety and data

- Settings show whether a value came from the device, a backend cache, application storage or an unsaved draft. A write without readback is not reported as device-confirmed.
- Versioned backups contain supported fields, not complete firmware or every setting in device memory. Preview and select fields before restore; some backends cannot roll back a partial restore automatically.
- Diagnostics export is explicit and redacted; there is no automatic upload. Macro contents and device serials are not included by default.
- No firmware flashing, factory reset, speculative HID command or automatic backend installation is performed.
- OpenRGB connects to the local SDK endpoint only; configure/start the SDK server yourself if you use it.

## Build, checks and simulation

```sh
python -m unittest -q
python scripts/check.py
python scripts/gui_smoke.py
python scripts/simulation_smoke.py
python app.py --simulate
```

The hardware-free suite and GTK/simulation smoke tests do not replace physical device testing. The specific hardware checks are listed above and in the device report. To prepare an Arch build without installing it, follow [packaging/arch/README.md](packaging/arch/README.md).

## Known limits

- Hardware feature coverage depends on the installed provider and exact device/firmware revision; unlisted devices may appear only as standard input or diagnostic inventory.
- Some backends expose cached state or write-only controls. Those operations remain labelled accordingly and are not presented as readback confirmation.
- ckb-next currently provides detection only. OpenRGB, OpenRazer and rivalcfg integrations are provider/API integrations, not physical certification of every listed model.
- Advanced Ace68-II key features (SOCD/Snap Tap, DKS, Mod Tap, Toggle Key, remapping and macros) are not editable because safe write formats are not confirmed.
- Bluetooth sleep, broad unplug/reconnect behavior, clean-system installation and power-cycle persistence need additional hardware/environment testing.

## Contributing

Issues and pull requests are welcome. For a new device, include its model and connection type, backend/version, capabilities discovered and a redacted diagnostic report. Never publish serial numbers, personal paths, private macros or raw configuration reports. See [`AGENTS.md`](AGENTS.md) for the project workflow.

## License

Logi Center is MIT licensed. Third-party backends and device names remain under their respective licenses and trademarks.
