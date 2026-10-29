# K7 Ultra: read-only investigation and safe boundary

Update 2026-10-28: the user-observed test established the dock RGB target and
restoration; the implemented native dock backend/QML and current verification
are documented in [k7-dock-rgb.md](k7-dock-rgb.md). Earlier unknown-target
observations below describe the state before that test.

2026-10-27. This note concerns the K7 Ultra **mouse**, not the Ace68 keyboard.
No physical setting, onboard profile, indicator or dock mode was changed during
this investigation.

## Observed on the attached mouse

The existing MCHOSE adapter matched one receiver/configuration interface and
read the connected mouse's identity and configuration. It did not enumerate a
separate dock control device. The read returned active profile 1 (protocol
index 0), DPI 400, stage 1, 2000 Hz, battery 38%, and charging false. Motion
Sync, Jitter Reduction and Angle Snapping all read false. These are
point-in-time values, not proof of an LED's optical state. The user reports
that the dock's battery-level lighting already works autonomously on Linux;
Logi Center leaves it unchanged.

A documented RGB read on the validated receiver interface returned a stored
mode and color record. Its **physical target is unknown**: the receiver path
alone does not establish whether it controls the dock, the mouse, or an
indicator. It cannot safely be surfaced as a dock editor or used to overwrite
the existing battery-level mode. There was no separate dock state readback.

Neither configuration read nor identity read contains top charging-LED state,
bottom profile-LED state, profile colors or indicator-enable state. The
current Linux adapter has no code that disables either LED while reading.
The difference from the user's Windows observation therefore remains
unexplained; no initialization command is inferred.

## Protocol and safety boundary

The [upstream family protocol](https://github.com/alexfrih/mchose-linux/blob/main/PROTOCOL.md)
documents a combined performance-flags operation and an RGB record. Its
hardware research was on a different family member. It notes that setting
flag bits to zero does not reliably clear them, while a full configuration
clear is rejected. There is no verified reversible K7 Ultra write/clear
sequence preserving unrelated flags. Read capability is not write evidence.
The independent [OpenMouse support table](https://openmouse.app/supported)
also marks K7 Ultra's protocol unknown, despite testing other MCHOSE mice and
one different charging base. Its dock commands are not transferable to K7.

The existing adapter can decode the three sensor flags and already refuses
their writes. That boundary is retained. No dock/indicator write plan is
exposed. The QML editor now shows concise read-only sensor notes and separate
K7 indicator/dock sections that distinguish reported charging/profile data
from unobserved LED/dock state. Section navigation performs no hardware I/O.
The editor's explicit Refresh button now performs a targeted asynchronous
configuration read instead of a full discovery pass. It updates the active
profile and reported charging state with binding/epoch guards and preserves
drafts. As of 2026-10-28, an active K7 detail page also observes configuration
every five seconds through the shared executor. No physical DPI/profile-button
host notification is known; immediate event-driven synchronization is not claimed.

The [official MCHOSE HUB page](https://www.mchose.store/pages/mchose-hub)
lists the K7 Ultra, but does not publish the missing K7 indicator and dock
command mapping. Public family commands are not sufficient to claim support.
The [official K7 Ultra product page](https://www.mchose.store/products/mchose-k7-ultra-lightweight-wireless-gaming-mouse)
confirms a magnetic charging dock that also acts as an 8K receiver and has an
RGB light stripe. The [official K7 Ultra manual](https://cdn.shopify.com/s/files/1/0846/5727/5175/files/K7_Ultra-User_Manual.pdf?v=1752564264)
does not provide a Linux command mapping. A separate MCHOSE support article
for the **K7** tri-mode mouse is not treated as K7 Ultra protocol evidence.

## What remains blocked

### 2026-10-27: indicator identity and currently attached USB device

The [K7 Ultra manual](https://ae01.alicdn.com/kf/S15d107ae5541481baaacbba09ab5734ba.pdf)
labels the underside light next to the DPI switch **DPI Indicator Light**, not
profile LED. It assigns red/blue/green/yellow/cyan/purple to the six DPI
stages. The small light on the top shell is **Status Indicator Light**: blinking
red means low battery, solid red means charging, and solid green means fully
charged. The manual does not promise an always-on profile indicator. QML now
uses these names and does not infer optical state from reported DPI or charge.

The [official M HUB bundle](https://www.mchose.com.cn/) has **two distinct**
lighting implementations: K7 Ultra at USB `3837:1001` uses inverted report
`0x11`, command `0x1B` to read and `0x2B` to write its RGB record; a separately
listed `MCHOSE MagDock` at USB `3837:1012` uses `0xAA`/report-0 commands 7
and 39. The latter protocol must **not** be applied to the attached K7 receiver.
The K7 record might control the integrated dock's strip, but its physical
target still needs observation. M HUB maps K7 effect IDs 6=static, 2=breathing,
4=cycle and 0=host-driven music. These values come from its JavaScript, not a
physical K7 test.

On this host only `3837:1001` enumerated. Its link status read `connect=0`,
and the mouse identity read was empty. Its stored RGB record still read
successfully, so that record cannot establish the mouse's presence or the
dock's optical state. No write was sent. The next physical gate is to wake the
mouse in 2.4G mode and check charge/DPI indications while observing the dock.
The user was asked to do this; until then neither LED nor RGB target can be
optically verified.

### Detail-page charging state

On 2026-10-27 the user observed the mouse's upper indicator glowing **solid
red while seated on the magnetic dock**, and the running QML page displayed
"Charging". This matches the K7 Ultra manual's solid-red charging indication;
no Logi Center setting or HID write was used to turn on the light. The
observation confirms visible operation in this condition, not the cause of its
earlier absence or the behavior of the underside DPI light.

The user subsequently clarified that the mouse had been removed from the
charger **before** the read-only receiver samples. Three consecutive
`0x11/0x06` samples then returned battery 46%, mouse linked, and charge byte 0
(`charging=false`), as expected off the charger. These readings do not
contradict the earlier red LED and QML charging indication. They do not,
however, constitute a synchronized receiver read while charging; that state
still needs a paired observation before declaring the protocol readback
physically verified.

The user also confirms that the underside indicator beside the sensor now
lights. Its six nominal DPI-stage colors are shown next to the one-based stage
number in QML using the manual's red/blue/green/yellow/cyan/purple order. The
swatches are UI approximations, not colors read from the LED. Individual stage
colors and automatic synchronization after a physical DPI-button press have
not yet been optically verified. Focused simulated RU/EN QML captures at 640
and 1000 px are in `docs/screenshots/redesign/k7-dpi-indicator/`.

The user supplied a QML detail screenshot where the battery strip animated
while the indicator section still said "Not charging". The strip uses the
shared `battery_display()` result from the current presentation. The K7
indicator section had independently read a MCHOSE capability and lacked a
notify signal after battery polling. It now uses `battery_display()` as well,
and the bridge emits a lightweight editor notification after telemetry updates
without rebuilding controls or losing drafts. The offscreen QML smoke and
targeted state/signal tests pass. Simulated RU/EN screenshots showing the
charging strip and text together are in
`docs/screenshots/redesign/k7-charge-sync/after/`. A later one-shot receiver read returned
`charging=false`; it was taken after the screenshot and cannot establish the
earlier physical charging state or either LED's optical state.

`python scripts/k7_indicator_probe.py --samples 10 --interval 2` is a bounded,
read-only observer for that test. It prints mouse link, battery/charge, active
profile/DPI and the receiver RGB effect ID without serials or raw reports. It
does not claim an LED is lit. A live one-shot probe while the receiver was
temporarily held by another process returned `EAGAIN`; the earlier direct
reads above are the latest successful hardware observations.

For a user-observed RGB target test after the mouse reconnects,
`python scripts/k7_rgb_trial.py --confirm K7-STATIC-RED-RESTORE --seconds 3`
first validates the connected K7 identity and saves the complete current
configuration plus original 15-byte RGB record privately. It then requests
M HUB's native static red effect once, reads it back, and restores the exact
original record once. The user must observe **which** light becomes red and
whether the original dock battery behavior resumes. This trial has only been
tested with an in-memory transport; it was **not** run on physical hardware
while the mouse link was absent. A matching readback would confirm stored
settings, not visible illumination.

1. Top charging LED now lights red on the dock according to the user. The
   fully charged green indication and a synchronized charging report remain
   to be observed; no software LED-enable command has been identified or used.
2. The user confirms the underside DPI LED lights. Compare each stage's color
   with the manual and verify automatic QML state updates after a physical
   DPI-button press; determine whether the light is intentionally temporary.
3. Dock RGB: the 2026-10-28 observed static-red/restoration trial confirmed the
   integrated dock strip as the target and restored its existing battery mode.
   Other effects, brightness levels and persistence still need observation;
   see [k7-dock-rgb.md](k7-dock-rgb.md).
4. Sensor flags: establish a reversible K7 write-and-clear operation with
   readback that preserves all unrelated configuration fields.

Dock and sensor writes require the corresponding protocol/target evidence
above. Before a physical test, specify exact operation, scope, persistence,
possible side effects, rollback and uncertainty. Mock tests do not constitute
physical verification.

Two useful user-assisted checks need **no software write**: while charging,
compare the top LED with the app's reported charging value; after pressing the
physical DPI button, compare the reported DPI stage with the underside LED.
Record whether the mouse is wired, wireless or seated
on the dock for each observation. These observations can identify behavior,
but cannot by themselves authorize or validate an indicator write command.

## 2026-10-28: profile/stage guards and passive QML observation

Shared MCHOSE plans now carry the profile observed when the command was
prepared; DPI writes additionally carry its DPI stage. These are host-side
guards, removed before constructing the existing HID report. A changed
profile/stage blocks the write before the pre-write snapshot or setting
report. Readback from another context cannot confirm the requested value.
Discovery cannot silently substitute a new plan context into an already queued
QML operation. No physical configuration was written during this work.

MCHOSE drafts use separate profile keys and separate DPI-stage keys. Switching
hardware context preserves each draft. Legacy drafts without scope remain on
disk and are shown as read-only recovery text for manual review/re-entry; they
are not automatically assigned to a profile. The existing backup services are
unchanged. After restoring a different profile or stage, restore its settings
from a fresh preview; a plan prepared for the previous context safely stops
instead of writing into a newly selected slot.

While the QML window is active on the K7 device page, an existing read-only
configuration request runs at five-second intervals on the shared executor.
This updates profile, stage, DPI, nominal color and sensor observations without
locking the editor or resetting its model. Background pages, an inactive
window and simulation perform no such polling. Reads yield to active writes,
backups, discovery and battery reads. Epoch guards reject replies after
navigation, reconnection or a new operation; shutdown cancels observation.
On a read error, last values remain marked unconfirmed, a localized message is
shown and retries back off to 15 seconds. Normal battery polling remains the
lighter identity-only route. Physical button-to-QML latency remains unmeasured.

Verification: `scripts/check.py` passed 365 tests including compileall; QML
loading/qmllint and focused functional smoke passed with all real I/O forbidden.
Native GTK GUI smoke passed and GTK simulation passed 15 scenarios. Peripheral
smoke hit the previously documented GTK WidgetPaintable capture failure:
`Widget snapshot not ready: dashboard-1000` (mapped/realized 1000x780); it was
not retried; that run stopped before completing its peripheral checks.
Reviewed simulated RU 640 px and EN 1000 px error/recovery screenshots:
`docs/screenshots/redesign/k7-state-sync/`. No clipping or overlap was found
in the changed labels. Native physical DPI-button synchronization and dock RGB
target identification still require user observation.
# Current K7 editor status — 2026-10-28

The exact K7 M HUB settings schemas supersede the earlier L7-family write
restriction for the new native path. Motion Sync has now passed one explicitly
approved physical false→true→false/readback/restore test, with all unrelated
configuration preserved. DPI, button, LOD/mode/rotation and the other filter
codecs are implemented and mocked; their new write paths are not physically
verified. Dock behavior and the previously observed charging/DPI LEDs are
unchanged. See [k7-controls.md](k7-controls.md) for command provenance, UI,
safety guards, actual test output and remaining hardware checks.
