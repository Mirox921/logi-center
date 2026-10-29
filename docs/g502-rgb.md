# Logitech G502 HERO RGB in QML

## Confirmed scope

The wired G502 HERO identifies as `usb:046d:c08b:0`. Logitech lists **one
LIGHTSYNC RGB zone** and up to five onboard profiles for this model ([product
specifications](https://www.logitechg.com/en-us/products/gaming-mice/g502-hero-gaming-mouse.html)).
The attached ratbagd 0.18 instance exposes **two LED records** and reports
`on`, `off`, `cycle` and `breathing` for each. The records are kept separate;
the physical role of the second record is not inferred from its index.

| QML effect | ratbagd mode | Parameters | Implementation | Evidence |
|---|---|---|---|---|
| Static color | `on` | RGB | Onboard profile | User confirmed visible color change on Profile 1. |
| Off | `off` | None | Onboard profile | Backend capability; physical test pending. |
| Color cycle | `cycle` | Period, brightness | Onboard profile | User physically verified LED 1 at 8000 ms / 255: continuous color changes persisted after closing Logi Center. |
| Breathing | `breathing` | RGB, period, brightness | Onboard profile | Backend capability; physical test pending. |

No host animation worker is installed. G HUB software effects driven by games,
audio or screen content are not exposed because this mouse's support for each
such effect and a safe direct RGB streaming path have not been verified. Newer
G502 variants are not assumed to have the same firmware. This does not claim
complete G HUB parity.

## Why the cycle looked static

The user observed one color change and then a static LED after selecting cycle.
The read-only `ratbagctl` snapshot of the currently active profile showed both
LED records at `mode: cycle, duration: 0, brightness: 0`. The old QML Apply
sent only `mode cycle`; it never supplied an animation period. This makes a
zero period the strongest current explanation. The user subsequently confirmed
that LED 1 continuously cycles at **8000 ms / 255** and keeps cycling after
Logi Center closes. This verifies that one nonzero-period configuration works;
it does not isolate zero duration as the sole cause of the old behavior.
No other RGB controller was running in the process check; only `ratbagd` was.

The [libratbag HID++ implementation](https://github.com/libratbag/libratbag/blob/master/src/hidpp20.c)
stores `cycle`/`breathing` and the period in the onboard profile. Its
[ratbagctl interface](https://github.com/libratbag/libratbag/blob/master/tools/ratbagctl.1)
commits changes through ratbagd. Public G502 HERO profiles reported to the
libratbag project include animated modes with **2600, 8000 and 9000 ms**
periods ([example 1](https://github.com/libratbag/libratbag/issues/1241),
[example 2](https://github.com/libratbag/libratbag/issues/983)). These are
evidence for plausible values, not proof that every intermediate period or
speed is accepted by this physical mouse.

## Apply behavior

- QML reads available modes per LED from ratbagd. For this exact USB model only,
  it shows period and brightness controls in `cycle` and `breathing`.
- The installed ratbagctl exposes duration in milliseconds from 0 to 10000 and
  brightness from 0 to 255. QML offers a conservative **1000–10000 ms** period
  range in 100 ms steps, and **1–255** for dynamic-effect brightness. Zero
  period is excluded because it did not animate in the reported scenario.
- Quick period choices are Fast 2600, Normal 5000 and Slow 8000 ms. These are
  UI presets within the backend's range; “Normal” is a midpoint, not a
  manufacturer-defined level. Smaller period means faster animation.
- Selecting a dynamic effect with missing/zero cached parameters stages 8000
  ms and 255 brightness in the draft. It does **not** write automatically.
  Changing speed on an already selected zero-period effect also stages 255.
- Apply sends period, brightness and mode in that order for one profile/LED;
  changing period or brightness re-sends the selected mode last. Each operation
  passes the existing exact-device, active-profile, ownership and cancellation
  guards. A failed step stops later steps. Other DPI/buttons/macros are not
  changed by Logi Center's plan. ratbagd's own commit mechanism may rewrite
  profile data from its cache; no rollback guarantee is claimed.
- Draft speed/brightness values use separate keys for `cycle` and `breathing`.
  Switching effects preserves the other effect's draft. Color is available
  only for static/breathing; cycle/off do not send a color command.
- Matching ratbagd readback is reported as **sent, unverified**. It is daemon
  cache evidence, not optical confirmation. A profile switched externally
  aborts the pending write and refreshes the editor while retaining its draft.

## Physical result and remaining checks

The user manually applied `Cycle colors` to LED 1 at 8000 ms and brightness
255, saw continuous changes on the physical G502 HERO, and confirmed that the
animation continued after completely closing Logi Center. This confirms an
autonomous effect for that configuration, not a host-driven RGB loop. Breathing,
LED 2, other periods/brightness values, reboot persistence and complete G HUB
feature parity remain unverified. The agent did not perform a physical write.

## Native profile versus daemon cache, 2026-10-28

An explicitly authorized read-only HID++ observation found onboard mode,
current sector 1 and directory index 0 (UI Profile 1). At the same time,
`ratbagctl profile active get` returned index 1 (UI Profile 2). The stored
records for index 0 contained `cycle` for both LEDs, while index 1 contained
`on`. This explains a cycling mouse paired with a static-mode editor. The
profile directory order is read, not inferred by subtracting one from sector.

The isolated optional Solaar API reader allows only GetMode, GetCurrentProfile
and profile-directory reads; it never enumerates settings or obtains RGB
ownership. It closes the transport handle without RGB cleanup callbacks.
Ambiguous identical physical units are rejected rather than chosen by model.
Missing API/access/directory mismatch leaves the source labelled daemon cache.

The editor follows the observed hardware profile, keeps LED values labelled
ratbagd cache, and offers explicit profile synchronization when the daemon
disagrees. Opening/refreshing the page does not switch a profile. Before writes
using live profile evidence, a fresh native read plus the existing daemon
profile check must agree. User-initiated synchronization uses the current
hardware index, with generation guards and ordinary serialized service plans.
No physical synchronization or new lighting write was performed in this cycle.

An open real-device editor refreshes in the background every 10 seconds,
pausing for writes/recording and retaining profile-scoped drafts. This is not a
physical LED readback or a hardware animation loop. Native firmware animation
confirmed above remains unchanged.
