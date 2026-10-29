# Current UI iteration checkpoint

Worktree: `logi-center-ui-iteration`, branch `ui/dashboard-iteration`.
Original dirty tree is preserved; baseline checkpoint c01b543. Stage 1 header
commit 348177e is accepted. User explicitly requests autonomous continuation:
**do not ask for intermediate design acceptance again.** No hardware writes,
backend/service changes, release, install or permission/config changes.

## Stage order

1. Header: complete and accepted; source counters/time, RU/EN, Tools, mark.
1b. QML backups: complete presentation over unchanged backups.py /
    capability_backup.py; tests/Wayland screenshots passed, commit ebc85de.
2. Compact Dashboard toolbar: implemented; 255 tests and offscreen keyboard/layout
   smoke and real Wayland keyboard/layout checks pass; commit e62cf64.
3. Fixed cards, separate battery row, subtype/provider labels: implemented;
   273 tests, QML/card/backup offscreen and native Wayland card checks pass; c5c9738.
4. Artwork provenance, graphite keyboard series, corrected TKL/Full spacing,
   distinct evidence-based variants, family scaling and final visuals: complete.
   Final 281 tests, 50 deterministic PNG checks and all GUI/simulation smokes pass.

## Current implementation and validation

Stage 1b adds qml_ui/bridge/backups.py, backup_simulation.py,
BackupsPage.qml and DisclosureItem.qml; opens from Tools. 18 facade/model tests
cover provider/legacy/cache/local/audio sources, checksums/model, private safety
snapshot, selection/re-preview, hotplug/generation, partial/unconfirmed results,
cancel and no real I/O. Native file-picker path slots are validated; the smoke
injects fixture file paths, not OS picker interaction. scripts/qml_backup_smoke.py
uses unchanged services + memory transport, strict backend.run prohibition,
keyboard popup/Escape/field selection, RU/EN/640/1000 captures, selective restore
and partial failure. Offscreen and real Wayland smoke passed; no physical writes.
Full check (249 tests), QML/qmllint and backup offscreen smoke pass; final host-session run is recorded in the stage validation.

Screenshots: docs/screenshots/redesign/backups/after/. Initial visual defects:
ComboBox implicit size loop (fixed by bounded dimensions); raw debounce label
(fixed); disabled restore affordance (fixed); pre-operation values labelled as
current after restore (fixed: Before restore). Paths remain in collapsed private
safety details, never public reports/captures. Same backup checksum/device scope
retains field choices on re-preview; new unseen fields stay unselected.

Host GUI needs tools.exec_command sandbox_permissions=require_escalated (normal
user session, no sudo). In the restricted namespace Qt Wayland aborts / GTK
cannot initialize. Approved host launch works. Screenshots on workspace 6 use
only our window; temporarily focus 6 for GTK frames and restore previous workspace
in finally. No idle/lock/config changes. Stage 1 full GTK/gui/simulation/peripheral
and QML real/simulated Wayland smokes passed. Use omarchy skill for desktop work;
its guides were read. Offscreen wrappers set QT_QPA_PLATFORMTHEME=generic.

## Remaining explicit requirements

- Toolbar: 68px header +42px toolbar; tabs 13–14px+counts, search280px at>=960,
  compact expandable search below, Ctrl+K and slash, cut built-in toggle/count,
  refresh/progress and reduced-motion. Preserve scroll/filter state.
- Cards: constant scene/card/battery region sizes, charge>=16px, explicit charging
  only, unknown dotted meter, subtype once, healthy LED without repeated text,
  hide framed unknown connection, text setting count, muted provider directly on
  uncertain duplicate records. Do NOT merge/change DeviceManager. Live G502 has
  two provider records; root incomplete identity cannot be guessed.
- Artwork: fresh asset path/source/hash, actual file+hash gallery, class selection
  only positive metadata. Confirmed touchpad -> touchpad without caveat; unknown
  pointer -> neutral + generalized art + type unknown. Untyped Bluetooth ->
  neutral Bluetooth audio, never a speaker. Typed BT speaker may use speaker.
- Keyboards: graphite top-vs-case mean L* delta8–12, beveled keys, moderate gap
  backlight parameter, 65%reference, laptop distinct .7function row +compact
  arrows. TKL87/Full104 block gaps .25–.5u, same row height, correct sums and
  no overlaps. Keep unaffected successful classes stable.
- Families: compact mouse physically smaller; 60<65<TKL<Full. Fit biggest once
  per family with>=6px margin. GUI mouse body>=60%scene height, keyboard>=70%
  scene width. Resolve with per-family scene framing, not re-normalizing every
  source PNG. Neutral placeholder silhouettes must differ at64px (intentional
  aliases exempt). Touchpad button zone/matte texture/noLED; HDMI/DP connector
  14–18%screenwidth; distinct built-in/BT/unknown audio/instrument silhouettes.
- Before/after 800/1000/1280/1600/1920 RU/EN +search/focus/tabs/built-in, dark/light
  1x2x sheets, series and neutral sheet,>=2 review rounds for keyboard/neutral.
- Each stage tested, screens reviewed, logical local commit. Update docs,
  installer/CI/Arch. GTK remains default; editor parity is not claimed.

## Final status

Accepted UI iteration stages 1/1b/2/3/4 are complete in this isolated worktree.
Final checks and screenshot review: header/iteration4/validation.md; paired
captures: header/iteration4/comparison.md; image review and source hashes:
illustrations/iteration4/{review.md,after/}. Extra regressions cover family
scale/geometry consistency, TKL/Full/laptop data, backlight, 64px silhouette
difference, display route proof and QML/pure-label translation completeness.
No hardware/backup service/DeviceManager changes. Shared battery read service
also rejects malformed responses before they can become a GUI exception.

This is not the full Qt editor migration: docs/qml-parity.md still blocks changing
the default. Mouse/magnetic-keyboard/audio editor controls remain in working GTK.
Backups QML presentation is service-backed with a GTK fallback. Native file-picker
interaction and physical charging transitions are not claimed. No release/install.

## Iteration5 / acceptance candidate

A de50ba6; B1437d67; C944efdf; D6883959; E93c7117; F current following commit.
All requested QA passed; final output and links are in docs/iteration5-report.md.
Latest steering: iteration4 mouse contours + slightly larger/light steel side
buttons on wireless/gaming; no broad palm-rest glow. Earlier stronger curves
and faded panel are review history only. Source model/backend/DeviceManager stays
unchanged. Ready for the user's visual review, not declared approved or released.
