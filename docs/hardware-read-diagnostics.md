# S9 / G515: read-only hardware evidence

Status: 2026-10-29. The supplied `log.json` is evidence from the remote machine;
it is not a hardware test performed by this development session. It is not
committed to Git. Automated transports below are mocks, not physical devices.

## EWEADN S9 8K

The report contains real receiver `372e:1026`, an `eweadn: timeout` fault and
unavailable onboard configuration. The existing inner page reader raises that
component/code; an outer SDK deadline instead comes from execution.command
(the Python process). The old report cannot identify the page/chunk or explain
why the reply failed validation. Firmware/receiver compatibility and the exact
physical timeout remain **unresolved until a read trace is collected**.

The official ByteTech SDK/codec bytes still match the SHA-256 values in
[eweadn-s9.md](eweadn-s9.md). Static inspection confirms the existing main 79
read requests, encapsulation/offset increments, ten-byte response chunks and
63-byte request payload. No downloaded JavaScript was executed. There is no
verified reason to replace the protocol or simply increase timeouts.

Implemented:

- Instrument pages 128, 129, 64, 65 and 0, chunk/offset/attempt, ioctl start/end,
  elapsed time, reported ioctl count, response rejection category and public
  header counters. Do not export any payload, identity, hidraw path, serial,
  descriptor hash or button/macro contents.
- Keep the existing 20-second SDK deadline and three bounded protocol attempts.
  Diagnostic progress is flushed before ioctl so a killed/stalled worker still
  identifies its last operation. `worker_deadline` is distinct from an inner
  `protocol_timeout` event.
- Respect the actual HIDIOCGFEATURE byte count instead of parsing the allocated
  zero-filled tail. Accept real short terminal frames for documented 41-byte
  single-axis DPI and complete short key pages, then validate the configuration
  schema (a 41-byte page cannot enable independent axes). This avoids querying
  missing tail data after an explicit terminal frame. Reject other short chunks,
  ACKs, wrong report/command/encapsulation/offset and oversized payloads.
- If model page 128 is validated but a later page times out, expose only the
  successfully read model/status fields. Retain the configuration error. Full
  configuration controls and setters stay disabled; no partial state is used
  to construct a write or fingerprint. Unknown identity still blocks access.

Run from the updated source checkout, with the receiver connected, after moving
and clicking the mouse. Close the vendor browser tab before this exclusive read.
Do not run as root and do not pick a permanent hidraw number:

```sh
python scripts/eweadn_read_diagnostics.py --output ~/s9-read.json
```

If several **configuration interfaces matching all signatures** exist, select
one by the temporary 1-based index with `--device 2`. Unmatched interfaces are
never probed. One invocation stops at the first failed page and never issues a
configuration setter, reset, pairing, profile-switch or firmware command.
A HID feature SET ioctl here carries the known main-79 **read request**, not a
configuration write. Send `s9-read.json`; its last events identify whether the
next investigation concerns timing, an ioctl stall, the frame header, a chunk
length or a particular page. Do not send raw HID captures or private snapshots.

## Logitech G515 LIGHTSPEED TKL

Confirmed software findings:

1. `sent_unverified` intentionally retained drafts, but the card/footer called
   them simply “Not saved”. They now say “Sent, unconfirmed”. A failed command
   or mismatched readback remains an error; drafts are retained.
2. Cycle `0x15` omitted saturation. Solaar's LEDEffectSetting serializer fills
   omitted parameters with zero, while its effect table specifies saturation
   255. Zero desaturates the cycle and can make it appear static. The request
   now supplies saturation; actual physical animation still needs confirmation.
3. The installed 0x8071 RGBEffectSetting is built with **no read function**.
   Its validator is not readable even if the feature's general flags advertise
   read support. A scoped CLI echo or YAML/cache match is not effect readback.
   Merely adding rgb_zone_1 to LIVE_KEYS would invent hardware confirmation.
4. Scoped reads now export the initialized zone's actual effect enumeration,
   fields/defaults/ranges and getter availability. Additional Wave/Ripple controls appear only when this backend enumerates
   their IDs and fields. Existing Static/Off/Breathe/Cycle compatibility fallback
   is preserved for older builds without metadata; Solaar still validates zone
   commands. Unknown additional effects remain unavailable.
5. LED Control is explicitly enabled before an effect. Its scalar getter is
   checked before continuing; False/mismatch stops the effect write. Missing
   readback stays unverified. Per-effect period/intensity/saturation/direction
   are validated together. Ripple uses its native 2–200 range where reported,
   with no invented millisecond label. No host animation loop was introduced.
6. Read-only workers cannot persist configuration defaults to disk or invoke
   settings setters, RGB manager startup or shutdown animation. Normal explicit
   user-initiated Static/effect writes retain the existing backend path.

Collect from the **friend's machine with the G515**, from the updated checkout:

```sh
python scripts/g515_read_diagnostics.py --output ~/g515-read.json
```

For multiple keyboards provide the already known exact CLI selector using
`--target`; it is not exported. This command uses only six allowlisted scoped
getters, never full `solaar config/show`. Its `reads` entries record the setting,
elapsed time, returned stdout byte count or error code. `returned` only means
the CLI returned text; value provenance/getter metadata still determine whether
that text is device state or cache. It exports source/availability/effect
metadata, not palettes, serials, paths, macros or the original config. The
physical keyboard is unavailable locally. Native animation, emitted LED colors,
behavior after Logi Center exits and persistence remain **unverified**.

After reviewing that report, launch `python app.py` from that same updated
checkout (an older installed desktop launcher may still use older code).
The friend may explicitly test in the UI: record
current settings, choose a device-enumerated Cycle and Apply once, note whether
colors animate for at least ten seconds, then close the app and observe again.
Also note whether Solaar GUI or another RGB controller was running; this code
does not terminate competing services. Repeat for Breathe/Wave/Ripple only as
deliberate separate user actions. Do not
infer success from the label or from the saved YAML. Do not reset profiles.

## Discovery, provenance and reports

- Saved Solaar records remain disconnected/cache-only unless reliable evidence
  exists. A unique matching paired `_serial` and Linux input `uniq` allows
  association with the exact physical input function. Ambiguous/missing tokens
  do not merge, even if model names or VID/PID match. Receiver PID c547 remains
  the receiver PID; it is never relabeled as keyboard WPID 40B4.
- On editor read, actual scalar Solaar observations are published to inventory;
  cached LED effects retain cache provenance. Resolved paired serials route
  commands, with binding/generation checks and multiple-unit ambiguity guards.
- The report's `[identifier]` setting was the legitimate `rgb_zone_1` name,
  redacted by the generic alphanumeric-ID heuristic. Known numeric zone names
  now survive; arbitrary private identifiers remain redacted.
- PRO X `volume`/`mute` pairs belong to distinct output and microphone routes.
  They must not be merged by the shortened display name. Public reports now
  include anonymous per-device endpoint IDs and `scope`, without route names.
- Missing OpenRGB/OpenRazer/rivalcfg stay isolated provider faults and do not
  prevent unrelated devices from being discovered.

If the input driver exposes no reliable paired identifier, cache/physical rows
remain separate in advanced diagnostics. This is a known limitation, preferable
to joining unrelated units. A scoped live selector can still reach the one
unambiguous physical G515 editor. The new diagnostic commands and tests do not
establish physical write verification.
