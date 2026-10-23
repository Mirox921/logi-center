# Logi Center v0.1.0 — first public preview

Common Logitech controls in one Linux desktop window, with English and Russian interfaces.

## Included

- G305 mouse DPI, polling rate and common button assignments.
- G515 LIGHTSPEED TKL brightness, visual color selection, lighting effects and idle timers.
- Wireless battery indicators, without inventing exact percentages for coarse readings.
- Wired G PRO X USB audio output/microphone volume and sidetone controls when supported.
- EasyEffects preset selection, JSON import, effects bypass and a community preset link.
- Per-user installer, bilingual documentation and screenshots.

## Install

This is a **source release**, not a standalone binary. It has been tested on Arch Linux with Wayland. Install the backend dependencies listed in the README, download and extract `logi-center-0.1.0.tar.gz`, enter its directory and run:

```sh
python install.py
```

Open **Logi Center** from your application menu. `SHA256SUMS` verifies the attached source archive; GitHub's automatically generated source archives are separate files.

## Preview limitations

This is an independent community app, not an official Logitech product or a full G HUB replacement. Original Blue VO!CE/DTS processing, firmware updates and automatic per-game profiles are not included. Advanced editing opens the existing backend apps. G515 lighting writes and G PRO X sidetone need additional physical testing across firmware versions. Initialize new G515 settings in Solaar first. Other distributions and hardware models are not yet verified.

## Validation

Fourteen unit tests pass, including translation coverage, saved preferences, preset import, battery parsing and read-only keyboard connection checks. The English/Russian language switch was checked in a running GTK window. Hardware interaction coverage is still limited; please report issues with your device model, connection type, distro and backend versions, with private identifiers removed.

## Screenshots

[Headset volume and microphone](https://github.com/Mirox921/logi-center/blob/main/docs/screenshots/audio-devices.png) · 
[Saved keyboard lighting (device offline)](https://github.com/Mirox921/logi-center/blob/main/docs/screenshots/keyboard.png) · [Audio effects](https://github.com/Mirox921/logi-center/blob/main/docs/screenshots/audio.png)
