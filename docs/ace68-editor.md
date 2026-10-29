# Ace68-II native QML editor — 2026-10-28

Exact target: USB 41e4:2116, configuration interface 01, firmware code 121.
GTK remains default. The supplied M HUB screenshots establish the requested
feature set, not physical verification of newly implemented writes.

## Reference mapping

| M HUB section / feature | Logi Center implementation | Evidence / remaining limit |
|---|---|---|
| Lighting: normal effects | 22 native effects, Off and Custom, effect-specific speed/brightness/direction/palette/RGB | Exact model layout and official channel definitions; memory transport tests. Only the previously documented subset was physically exercised. |
| Custom | Read 68 colors, multiselect, per-key RGB draft/Apply/Cancel | Native bank read physically confirmed; new writes tested with mocks. Apply Custom mode before editing its bank. Color-bank and other lighting drafts apply separately. |
| Cloud / music library | Unavailable | Vendor cloud/account and host effect lifecycle are not implemented. No fake cloud presets or background RGB loop. |
| Trigger | Original 68-key geometry, WASD/all/inverse/clear, actuation, RT mode, press/release distances, both dead zones | Existing exact-model validators/precision metadata; bulk writes tested, original per-key physical tests remain as documented in mchose-devices-progress.md. |
| Switch type / precision / manual calibration | Read metadata retained; no new mutating control | Safe switch/calibration sequencing and restoration not established for this unit. No firmware/reset/calibration command added. |
| Key config | Four independent Windows/Fn/Mac/Fn layers, basic keys/modifiers, mouse/wheel, media, lighting actions, shortcuts/search | All four layers physically read; writes mocked. Last base-layer Fn is protected. Unknown stored actions remain unchanged/read-only. |
| RS / SOCD / DKS / MT / TGL | Native firmware records, create/edit/remove, scoped drafts and readback | Banks physically read, no existing bindings observed. New writes are source-validated/mocked, not physically tested. |
| DKS phase editor | Four actions, press/release phase codes | Native phase packing tested. Travel points preserve the observed/native defaults; no guessed millimeter controls. UI is a numeric phase editor, not M HUB's graphical timeline. |
| SOCD | Last input / first key / second key / cancellation | Exact official priority codes 0/1/2/3. Partner priority inversion preserves the RT nibble. |
| MT / TGL | Tap/hold actions and 0–1000 ms in 10 ms steps; firmware toggle | No host key injection; physical behavior remains unverified. |
| Key test | Explicit focused key-down/key-up area; Esc stops | QML events only; does not measure Hall travel or capture global shortcuts. Smoke checks press/release/cancel without settings writes. |
| Performance | Polling 1/2/4/8 kHz, Win Lock, debounce optimization, stability, Mac/Windows, adaptive calibration flag | Exact native masks, unknown bits preserved. Mac clears Win Lock. Debounce ON is level **7**, not 1. Unknown levels stay read-only. New flags not physically changed. |
| Others | Existing enabled hardware profiles | Drafts for keys, lighting, performance, layers, advanced definitions and colors are profile-scoped. Old unscoped scalar drafts remain visible for manual review. |
| Onboard macros | Existing records preserved, not editable | Macro-bank capacity/header negotiation and safe shared allocation not yet validated. No guessed bank rewrite. |
| LT / firmware update / reset | Unavailable | LT model gate requires firmware ≥122; current unit is 121. No updater, reset or automatic profile repair. |

This stage does **not** establish complete M HUB parity.

## Native transaction rules

`ace68_bindings.py` and `ace68_advanced.py` are pure codecs/planners; actual I/O
stays in `ace68_adapter.hardware` through the existing SDK worker/executor.
No discovery/page-open operation changes configuration.

* Layer user/default banks: read 8/7, write 9, `(profile*4+layer)*512+key*3`.
* Per-key RGB: read 10, write 11, `profile*512+key*3`.
* DKS: read/write 162/163, profile area 768, record 24 bytes.
* MT/RS/SOCD: 164/165, profile area 256, record 6 bytes.
* TGL: 166/167, profile area 128, record 3 bytes.

Advanced definitions allocate only unreferenced **zero** records, without
compacting other definitions. SOCD priorities live in the profile's shared
trigger table: changing one is blocked when it would alter another layer's
SOCD binding, or when unknown priority bits are present. Data precedes binding
references. Old records
are cleared only after becoming unreferenced; unknown reserved bits/padding
are preserved or block editing. Removal restores firmware-default assignments
on affected keys, not an inferred earlier user assignment. Apply processes one
advanced definition at a time; other drafts remain. Disconnect/timeout can
leave an unused record; no automatic retry, compaction or blind rollback.

Each write requires a validated descriptor/identity, firmware, current profile,
private pre-write snapshot, serialization and final whole-block collateral
comparison. Layer/color/advanced writes additionally check their captured bank
baseline. Every subsequent frame checks the active profile. Existing binding
and Epoch guards prevent stale worker results from reaching another device.
OpenRGB ownership also disables newly loaded color/direction controls and is
checked again by the worker before any native RGB command.

## Source evidence

Primary sources: [official M HUB CZ](https://www.mchose.com.cn/cizhou) and its
[model/channel bundle](https://www.mchose.com.cn/cizhou/CZ_SHARED_DATA/main.7d734adfcc65efb81c4d.js).
The exact 41e4:2116 model identifies Ace68, firmware 121 and inherited Ace68_i
layout. Official code was inspected as a protocol reference, not executed or
bundled. UI geometry and codecs here are project-authored.

SHA-256 of inspected public bundles:

```text
cz-main.js 1f11d88aa4373b117ec56f6689a53ed30119f62374d4cec32860b544fb6b8463
2233-7547296881de80d2.js 9b643eab4a9f4f58b5f938c75993ada0c2b260ccfeb40fb4aaad04787065900d
2502-b93f88ce1ba6fb6d.js e5cc7a5aecfc60e89f81c1f93ad78b4875e3b3450202a4f0a11b2de7af8c481b
layout-ace68_i.344c52158c7dec6b0d6b.js 34434c634222821ec64a88a598901c0039b5814eeb09c05defb0b3bc12ee89a6
default-keys-ace68_i.90a2ebbfac36daac963c.js f2bfef749235f3fefd6a46a7a708547c716e9e1da7bda8fbb17238466ef0d530
1288-c36175f1f724fab8.js 75ec95014b2227de501779e02e31b6991e2c6fd93ffdfca436744bf6c778d5b8
```

Official `/cizhou/locales/en/common.json?v=1` confirms SOCD priority semantics.
The named action catalog confirms function codes 47 (next effect), 46 (previous
effect), 61 (next color), 50/51 (brightness), 54/55 (speed) and 53 (off).
These are key-action codes, independent of the lighting effect enumeration.
Physical key index 34 is Insert; the generic 65% dashboard artwork's grave key
is not used as an interactive hardware mapping.

## Verification

No physical setting write was performed in this stage. Host-session read-only
diagnostics returned firmware 121/profile 0; four layers ×68 positions; DKS
768 bytes, MT 256, TGL 128; zero existing advanced definitions; 68 RGB records.
Stability/adaptive-calibration flags were on, Win Lock off, debounce level 7.

Actual final outputs:

```text
python scripts/check.py   # includes compileall and the complete unit suite
Ran 427 tests in 27.792s
OK

python -m unittest -q test_ace68 test_ace68_bindings test_ace68_advanced test_qml_ace68 test_qml_editor test_qml_translations
Ran 98 tests in 0.711s
OK

python scripts/qml_smoke.py
PASS: qmllint accepted the QML pages and Theme module.
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.

python scripts/qml_functional_smoke.py --ace --output docs/screenshots/ace68-editor
PASS: mouse DPI/cache readback, macro, Ace68 selected key/device readback, audio/server readback, diagnostics; no real I/O.
PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.

python scripts/gui_smoke.py
GUI smoke: no writes/capture; editor, language, dialogs and cancellation passed

python scripts/simulation_smoke.py
Simulation GTK smoke: 15 scenarios; real CLI never called; no capture
```

The first full unit run found an outdated assertion equating a generic 65%
artwork label with the exact Ace hardware map. The assertion now explicitly
distinguishes those two labels; final full run passed. GTK simulation initially
could not access GDK display in sandbox; the host-session run passed. Peripheral
capture smoke was not repeated: the earlier null WidgetPaintable capture limit
is unchanged, and no GTK capture code changed.

After the full run, a final catalog audit corrected the next-effect/color
function codes and added regression tests for them, shared SOCD priorities and
OpenRGB ownership; the final 98-test relevant suite then passed. No hardware
key assignments were written by these checks. Focused G502/K7 functional
regression smoke also passed with the real runner prohibited.

Installer and Arch/CI manifests include both new Python modules and all four
Ace QML files. `scripts/prepare-arch.py` prepared a fresh checksummed source
archive; archive checks found all eight required runtime files. No package was
installed and a complete `makepkg` build was not performed in this stage.

Forty RU/EN offscreen captures at 640×780 and 1280×800 are in
`docs/screenshots/ace68-editor/`, including scrolled control views. Reviewed:
initial oversized desktop keyboard, clipped key-value padding, transient null
field bindings, stale busy/read messages and untranslated choice readouts.
The diagram was bounded to 42 px/key, text centered, null bindings guarded and
read messages corrected. Final captures are readable and scrollable; narrow
tab labels elide and the tab strip scrolls. No native compositor claim is made.

Required next hardware validation: one spare-key binding at a time, original
layer/bank snapshot, user-observed RS/SOCD/DKS/MT/TGL behavior, readback and
explicit restoration, followed separately by Custom RGB and performance flags.
Do not change calibration, switch type, profiles or other parameters as part
of those tests. Existing physical evidence remains limited to the earlier
documented exact settings.
