# Logi Center v0.4.0

**Stable release · 24 October 2026**

Logi Center now presents itself as a Linux peripheral manager rather than a Logitech-only control panel. It uses multiple existing Linux backends and displays only the capabilities those providers report. This is a meaningful expansion, not a claim of universal device support.

## Highlights

- MCHOSE K7 Ultra mouse and MCHOSE Ace68-II keyboard have separate, revision-scoped adapters and appear in the correct device categories.
- Physical read/write/readback checks were completed for the documented K7 DPI setting and the Ace68-II settings listed in [the hardware report](mchose-devices-progress.md). Tested original values were restored.
- Logitech G502 HERO keeps its existing libratbag controls; physical discovery, five profiles, eleven buttons, two lighting zones and backup preview were checked read-only.
- Common capability-based mouse and keyboard pages combine available provider features. Device inventory cards collapse, search by name and retain device-specific state.
- Battery values preserve provenance, charging state and unknown/error conditions instead of inventing a percentage.
- Optional OpenRGB, OpenRazer, rivalcfg and ckb-next providers join existing libratbag, Solaar, HeadsetControl, PipeWire/PulseAudio and Linux input support.
- Versioned capability backups include previews, selective restore and partial-operation reporting; diagnostic exports are explicit and redacted.
- English/Russian UI, mock scenarios, GTK smoke checks and local Arch packaging documentation are included.

## Device validation

Only the exact attached units named here were physically tested:

- **MCHOSE K7 Ultra**, USB `3837:1001`: configuration and battery reads; reversible DPI change `400 → 450 → 400` with fresh device readback.
- **MCHOSE Ace68-II**, USB `41e4:2116`, firmware code `121`: reversible readback checks for profile, polling, lighting, brightness, effects, selected-key actuation, Rapid Trigger and dead zones; selective backup/restore.
- **Logitech G502 HERO**, USB `046d:c08b`: physical read-only inventory and backup validation. Setting writes/visible RGB are not claimed as physically verified.

These checks do not certify other revisions or models. Full-profile firmware images are not backed up. Ace68-II SOCD/Snap Tap, DKS, Mod Tap, Toggle Key, remapping, macros and per-key RGB editing remain unavailable. See [backend support](backend-support.md) for provider-by-provider boundaries.

## Testing and packaging

The release source is checked with the repository's unittest, syntax/consistency, GTK smoke and isolated simulation workflows. Automated tests use mocks and do not count as hardware validation. A clean Arch installation and every optional-backend/device combination are not certified by this release.

Build a local Arch package from source using [these instructions](../packaging/arch/README.md). The build helper does not install the package, change permissions or enable udev rules.

## Upgrade

From a source checkout, pull the `v0.4.0` tag and rerun `python install.py`. Existing per-user preferences, drafts and backups are kept. If changing between a per-user install and a system package, choose one launcher intentionally; see the Arch packaging notes.

## Downloads and stars

GitHub updates the README badges with current repository stars and release-asset download counts. The count is for attached release assets; GitHub's automatically generated source archives are not included in that download counter.
