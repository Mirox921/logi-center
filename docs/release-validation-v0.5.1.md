# v0.5.1 validation — 29 October 2026

## Checks performed on the release worktree

| Check | Result |
|---|---|
| `python scripts/check.py` | 499 tests passed; compileall passed |
| Targeted release/launcher/header/artwork tests | 30 passed |
| Dashboard fixture callback regression | Passed with the current two-argument discovery callback |
| `python scripts/gui_smoke.py` | Default QML launcher/navigation and qmllint passed |
| `python scripts/simulation_smoke.py` | Shared DPI/profile/macro/key/audio/diagnostic paths passed with mock transports; no hardware I/O |
| `python scripts/check_release.py` | Runtime version, package/readme metadata, local README links and curated gallery passed |
| `scripts/check_g502_svg.py` | Wired/wireless Qt contours, transparency and gradients passed against independent fixtures; outside/missing pixels 0/0 |
| English gallery | Nine live Wayland captures on workspace 9, inspected; workspace checked before each shot and original workspace restored |

The capture helper originally rejected a positional timeout argument in its
read-only guard; this was corrected and the final gallery shows real audio
endpoints. The mouse editor was captured in a maximized native window without
changing user desktop rules or device settings. G502's genuine onboard/daemon
profile warning remains visible; it was not hidden for marketing images.

## Repository and archive scope

Removed 2241 historical generated captures from the release tree, preserving
the full local development history and a separate external archive. Four
canonical mouse silhouettes and two G502 renderer references moved unchanged
to `tests/fixtures/artwork/`; their regression checks remain active. The curated
release gallery is the only screenshot collection shipped.

The public release is a clean snapshot commit parented to the previously
published `main`, so development-only screenshot blobs are not uploaded through
intermediate commits. Public history is not rewritten. Application code,
assets/licenses, tests, fixtures, CI and technical evidence remain in Git;
personal tooling, build products, caches and private reports do not.

## Packaging procedure

`scripts/prepare-arch.py` uses the runtime version, creates a checksummed
source archive and a matching PKGBUILD. It includes all installed runtime
modules/QML/assets plus tests and fixtures; ignored historical captures are
explicitly excluded. Local Arch packaging uses:

```sh
makepkg --nodeps --nocheck --noconfirm
```

Tests are performed separately, not silently counted as part of this skipped
makepkg check. Attached assets use `SHA256SUMS`. The package is staged and
tested without system installation; dependencies and hardware access on a
clean target machine still require the normal installation steps.

## Hardware boundaries

Release preparation performed no physical setting writes, restores, firmware
changes, resets, microphone recordings or pairing/permission changes. The
gallery queries real devices read-only. Earlier hardware observations retain
their exact scope in [G502 RGB](g502-rgb.md), [K7 controls](k7-controls.md),
[K7 dock](k7-dock-rgb.md) and [MCHOSE progress](mchose-devices-progress.md).
S9/G515 and unverified device-bank operations are not promoted to physically
verified status by passing mocks or publishing this release.
