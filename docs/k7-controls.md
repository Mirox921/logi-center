# K7 Ultra DPI, button and sensor editors — 2026-10-28

## Scope and evidence

User feedback, 2026-10-28: the newly added functions worked in the user's
preliminary physical tests, accompanied by a K7 button-editor screenshot.
Individual settings/values and test sequences were not specified, so this is
a preliminary user confirmation, not verification of every mode below.

The same feedback identified the editor's mouse silhouette as too narrow.
Its SVG is now 45% wider at the same height, approximately 0.54 width/length;
all five anchors follow the same centered transform. Native indices and
assignment/write behavior are unchanged. Reviewed Qt SVG before/after and
RU desktop/EN narrow QML captures under `screenshots/k7-button-proportions/`.
Fifteen targeted tests passed; focused RU/EN QML smoke at 640/1280 px clicked
all five labels and all five anchor hitboxes, without real hardware I/O.

The three user-supplied M HUB screenshots are implemented in the existing
graphite/amber QML editor. GTK remains the default. The dock editor and G502
RGB implementation are preserved.

Protocol evidence is the exact K7 Ultra panel in [official M HUB](https://www.mchose.com.cn/),
asset [`purify.es-D9IeuU3Y.js`](https://www.mchose.com.cn/assets/purify.es-D9IeuU3Y.js),
SHA-256 `2b223ad993a4da4694dce52e63ecbb28e6b57c7c7b0053224b182f91b6efcd27`.
Schemas `Zst`, `Sst`, `xst` and the K7-specific panel/model table were inspected;
vendor code/assets were not copied into the application. The earlier L7-only
finding that sensor flags cannot be cleared is superseded: native `0x42`
uses **0 = unchanged, 1 = enable, 2 = disable**. It is not a replacement
sensor byte. No unknown packed flag defaults are constructed.

`k7_settings.py` contains pure codecs/catalogs; `mchose_adapter.py` owns I/O
through the existing worker, descriptor/identity validation and transport.
Capabilities require logical `3837:4150`, not a similar mouse name. The UI
recognizes the existing receiver `3837:1001` and wired `3837:4150` identities;
wired access remains physically unverified and does not imply a dock. The
receiver association is unchanged. No startup setting reports were added.

## Implemented

| Editor | Controls / native operation | Verification |
|---|---|---|
| DPI | 1–6 enabled stages, active stage, six stored X/Y pairs, colored stage cues, numerical inputs, non-linear slider; one `0x12/0x40` | Mock transport and QML interactions; the older scalar 400→450→400 test used the previous path, not this packet. |
| Separate X/Y | Exposed only when configuration byte 50 advertises availability, as in M HUB; checkbox is a local editing preference | Mocked available/unavailable firmware. `diff=255` is transmitted as specified; it is not assumed to be byte-50 readback. |
| Buttons | Native indices left=0, middle=1, right=2, forward=3, back=4; `0x12/0x52` | Mocked command bytes, ordered writes, readback, preservation of underside record 5. |
| Actions | Original action, mouse clicks/wheel, DPI actions, profiles, keys, arbitrary modifier/key shortcuts, common media commands, disable | Allowlisted encodings. Existing complex macros and unrecognized assignments are read-only; their contents are never rewritten. |
| Sensor | Performance/Gaming/Extreme, LOD 0.7/1/2 mm, rotation −30…30°, Ripple, Angle Snapping, Motion Sync; `0x11/0x42` | Motion Sync physically tested as below. Other settings have source evidence and mock coverage, not physical validation. |
| Timers | Sleep in minutes (0=never), debounce 0–20 ms, using dedicated `0x11/0x0a` and `0x11/0x43` for exact K7 | Mocked. Sleep's 0–255 bound is the protocol byte range; every possible firmware value has not been validated. |
| Polling / profiles | Existing capability plans retained | Earlier status applies; no physical rate/profile changes in this stage. |

DPI entry follows M HUB's 200–42000 range and the existing adapter's 50-DPI
step. Older stored values down to 50 are preserved by the codec; unsupported
observations disable writes rather than substituting fabricated values.
The active stage/count/axes are composed together. Lowering the count moves an
out-of-range draft active stage into the enabled set. Changing a slider edits a
draft only. Drafts are isolated by physical identity, profile and indexed field.
`NumberInput.qml` preserves focused numeric input across telemetry updates;
DPI and generic numeric editors commit it only on editing completion.
Older scalar DPI/stage drafts remain visible with their saved profile/stage
for manual re-entry or explicit deletion; no context is guessed or draft lost. A QML
keyboard-input regression check reproduces the original reset and verifies
that a telemetry notification now preserves the typed number.

Buttons use an original SVG, separate anchors, callouts, clickable selection
and a searchable action library. Custom shortcuts use explicit modifiers and a
key selector, so no global keyboard grab or accidental Wayland shortcut capture
is needed. Applying a layout without any left-click assignment is blocked both
in QML/Python and the pure codec. A replacement left click is installed before
removing its previous assignment. Complex macro creation remains blocked until
the native macro-bank format and a safe preservation strategy are validated.

## Write safety and state

Apply uses the existing shared executor, DeviceManager route, cancellation and
connection guards. A native batch captures the complete original configuration
and connection mode. Both are re-read and checked before the first write.
Each actual write saves an independent private pre-write snapshot. The packet
changes only its documented fields. Readback compares every unrelated byte/bit,
including profiles, mouse assignments and unknown sensor bits; reserved dynamic
byte 3 is the sole general exception. Unexpected changes stop the operation.
Each button write is checked before the next one. There are no blind retries.

Confirmed fields clear their drafts. Mismatches, errors, stale contexts and
partial operations preserve drafts and report their real outcome. Successful
K7 Apply refreshes only the selected device; it does not rescan all devices.
Native effects/indicators and dock battery mode are unaffected by these editors.
A live-read failure is displayed above the custom panels, so it stays visible
without scrolling through all DPI stages. The focused QML check covers that
position and the older-draft notice.

## Physical Motion Sync test

The user explicitly approved the reversible Motion Sync test in this session.
Executed once on the attached K7 Ultra:

```text
python scripts/k7_sensor_trial.py --field motion_sync --confirm K7-SENSOR-RESTORE
{"field": "motion_sync", "original": false, "readback": true, "restored": true, "test": true}
```

The original flag was false; true read back after one native setting command,
then false read back after restoration. The complete original configuration
matched after restoration, excluding dynamic byte 3. Other sensor bits,
profile, button records and DPI values stayed unchanged. This verifies the
setting/readback/restore path on this unit, not perceived input latency,
cross-profile scope, power-cycle persistence or every firmware revision.
No other physical setting was changed in this stage.

An earlier read-only attempt received an empty identity response. It was not
recovered by switching profiles; the later user-assisted test succeeded.

## Verification and visual review

Actual outputs:

```text
python scripts/check.py
Ran 400 tests in 24.233s
OK

python -m unittest -q test_k7_settings test_qml_editor test_qml_translations test_k7_sensor_trial
Ran 60 tests in 0.276s
OK

python scripts/qml_smoke.py
PASS: qmllint accepted the QML pages and Theme module.
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.

Focused qml_functional_smoke.py --stabilization
PASS: mouse DPI/cache readback, macro, Ace68 selected key/device readback, audio/server readback, diagnostics; no real I/O.

python scripts/gui_smoke.py
GUI smoke: no writes/capture; editor, language, dialogs and cancellation passed

python scripts/simulation_smoke.py
Simulation GTK smoke: 15 scenarios; real CLI never called; no capture
```

The final full check includes the native codecs, guarded trial, custom
shortcuts, wired identity and legacy-draft regression tests.
Peripheral smoke was not repeated: its previously recorded null
WidgetPaintable dashboard-capture blocker is unchanged. It is not claimed
as passed for this stage. The final checksummed Arch source archive was prepared and its runtime/QML
resource manifest inspected; PKGBUILD syntax passed. No packages were installed.

Screenshots: [`screenshots/k7-controls/`](screenshots/README.md#historical-reviews), RU/EN at
640×780 and 1280×800, offscreen. The primary review found truncated middle-click
text and misplaced DPI tick captions. The corrective review enlarged callouts,
aligned ticks with the non-linear mapping and confirmed clear selection and
non-overlapping labels. Narrow layouts stack cards and provide scrolling to
the remaining stages/actions; the existing tab strip scrolls horizontally.
The final custom-shortcut form was also reviewed. Minor differences from the
reference's exact spacing do not block use.

Remaining hardware checks need explicit user participation: native multi-stage
DPI and X/Y, side-button assignments/shortcuts, Ripple, Angle Snapping, LOD,
mode, rotation, timers, cross-profile behavior and persistence. Their source
mapping/mock tests are not presented as physical confirmation. In particular,
rotation's native enable behavior must be evaluated before planning a guaranteed
rollback experiment; no guessed disable command is used.
