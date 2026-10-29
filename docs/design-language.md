# Logi Center design language

## Concept

Logi Center presents each peripheral as an instrument with a small passport plate. The layout combines a cut-corner frame, measurement stage, indexed sections and aligned technical values. Device type and state remain the content; line work is used only to mark boundaries, focus and measurement areas.

## Palette

The application uses warm, neutral graphite rather than a blue or violet base. `#171713` is the canvas; `#211f1a`, `#292720`, `#343129` and `#3e3a31` step through surfaces. Borders use `#514c41` and `#756d5d`. Main text is `#f4f0e7`; secondary text is `#c3bcad` / `#a39b8c`.

The chosen accent is signal amber `#f3aa32`. It reads as a measurement cursor and hardware activity mark, and is intentionally limited to selected controls, focus, section indices, positive non-zero settings and charging. Its contrast against the canvas is above WCAG AA for normal text. Success, warning, error and charging use separate semantic tokens. An isolated lime preview was captured for comparison; amber was retained because it gives clearer hierarchy without turning the whole interface into status color. Lime is not a runtime option and is not present in the production theme.

## Shape and spacing

- Primary frames cut the top-right and bottom-left corners at 45°; `Theme.cut` is 11 px and `Theme.cutSmall` is 6 px. Small controls use the same cut proportion. Other edges stay square or use at most 2–3 px for keycaps.
- Cards use a 1 px hairline, layered surface colors and small corner registration marks. No blurred shadow or glow is used.
- Sections begin with a two-digit index, slash, uppercase mono label, rule and count.
- Device artwork sits on a bounded measurement scene with a very faint grid. The rest of the canvas is unpatterned.
- Use the spacing tokens in `qml_ui/qml/Theme/Theme.qml`; do not introduce unrelated radii or arbitrary spacing scales.

## Typography

- UI headings and device names: **Noto Sans** (Noto Project, Apache 2.0), regular/bold. It replaces the previous high-contrast serif display face, which was difficult to read at compact card sizes. Latin and Russian Cyrillic glyph sets are checked at startup and with `scripts/check_fonts.py`.
- Measurements, section labels, connection and status codes: **JetBrains Mono Nerd Font** (SIL OFL 1.1). It includes Cyrillic and Latin.
- Noto Serif Display remains bundled as a legacy face but is not selected by the current QML theme. Runtime checks register Noto Sans regular/bold and the mono family, verify Cyrillic А–я and Ё/ё plus Latin A–Z/a–z, and print the actual selected family. `python scripts/check_fonts.py` repeats the coverage test.
- Use size contrast to establish hierarchy: large display name/measurement first, compact mono captions second. Avoid applying one face and size to every label.

Font sources and license notices are in [`assets/fonts/SOURCES.md`](../assets/fonts/SOURCES.md). Font binaries are not modified.

## Signature components

- **Segmented battery:** 12 outlined cells and a monospaced value. Unknown supported charge uses dotted empty cells with “Заряд: нет данных”; a charge value is segmented only when fresh device/kernel data is available. Charging animation and label require an explicit positive charging capability.
- **Status LED:** a small square lamp plus a short mono state label. It is not a capsule badge.
- **Connection tag:** compact mono label in a clipped-corner outline (`USB`, `2.4G`, `BLUETOOTH`, `I²C`, or `—`). The device category remains below the name and is not repeated in this tag.
- **Device passport:** image on a measurement stage, readable model name, one category line, status/transport row and a compact settings count. A zero count is shown as a muted dash.
- **Brand mark:** a solid graphite instrument plate with opposing 45-degree corner cuts and three amber measurement bars. The same SVG is used by the header, About and application icon; it contains no letter or camera crosshair.
- **Empty/error states:** a dashed cut frame with direct text, no stock illustration or decorative glow.
- **Motion:** restrained 170 ms hover/focus transitions; image offset is at most 5 px. Reduced-motion behavior is respected by avoiding indefinite motion. The battery animation runs only while the device explicitly reports charging.

## Can / cannot

| Can | Cannot |
|---|---|
| Use a cut frame to group a real device or operation. | Use a row of capsule filters/status pills as the primary visual pattern. |
| Use amber for a selected state, focus, a real non-zero value or explicit charging state. | Flood the screen with accent, add cyan/blue-purple gradients or glow. |
| Put a faint grid behind an illustration that is being measured/inspected. | Put a decorative grid, palm, blur or unrelated background image across the whole page. |
| Use mono text for values, IDs in diagnostics, timestamps and short transport codes. | Use raw backend IDs or paths as device names. |
| Use an exact model image only when the revision and license are documented. | Substitute a similar-looking model or imply that a generated illustration is an exact product render. |
| Keep an incomplete last row aligned to the left at a fixed card width. | Stretch a small number of cards into giant empty panels. |

## Explicitly avoided patterns

No cyan on navy, blue-to-violet/green gradients, universal glow, glass blur, rounded capsule UI, repeated 12–20 px rounded rectangles, generic centered colored-square icons, rounded-square “L” logo, decorative palm, uniform centered symmetry, emoji or decoration without information.

## K7 dock editor

The user-provided M HUB reference informs only the dock editor's composition:
a product preview on the left and grouped effects/parameters on the right.
`K7DockPanel` uses the existing graphite/chamfered components and mono values.
An original editable SVG shows the rounded physical dock inside the application's
cut frames. Colored light and the battery gradient convey device settings;
they are labeled as previews, not ambient decoration or measured LED state.
Narrow layouts put the settings and lighting switch first. Only this dock page
uses a compact device passport; other device pages retain their existing layout.

## Screenshot review

Screenshots and the palette comparison are generated by `python scripts/design_gallery.py` from the QML app in explicitly labeled simulation mode. The icon contact sheets come from `python scripts/icon_gallery.py`. The current after set is under `docs/screenshots/redesign/design-language/after/`; its matching before set is under `before/`. It includes 640, 800, 1000, 1280, 1600 and 1920 px widths, RU and EN, dashboard, focused card, empty state and device/diagnostics pages.

Checklist (reviewed against those images after the latest capture):

1. **Logo test:** the symbol is a crosshair/registration mark, not an initial; the cut geometry, specimen scene and indexed meter labels provide the identity if the wordmark is covered.
2. **Squint test:** the device/model name and large illustration dominate; amber appears on only a few focus/index/value marks per viewport.
3. **Pattern test:** no capsule status or filter pills, cyan/navy pairing, glass, glow, centered colored-square icon or rounded L mark appears in the QML design.
4. **Substitution test:** the scene, transport tag, battery cells, model sheet and device-type illustration encode peripheral hardware; the same composition does not transfer unchanged to an unrelated product.

## Scope and current limits

The QML surface currently contains the Dashboard, read-only device detail, and read-only diagnostics. GTK remains the default interface and is intentionally retained as the functional fallback. Backups, restore dialogs, device editors and full-settings pages have not yet reached QML parity; their GTK implementations were not restyled in this visual identity pass. Apply these tokens/components when those pages are migrated, but do not claim they already use this theme.

## Layered artwork follow-up

Current class illustrations use the offline Cairo 2D pipeline described in [illustration-pipeline.md](illustration-pipeline.md). Mouse/keyboard/touchpad/receiver views are straight from above, audio is frontal; depth is layered lighting, not perspective. New comparison captures are in [illustrations/comparison.md](screenshots/README.md#historical-reviews). Cards are 260 px high, use width-aware aspect-preserving PNG framing, and the capture checks the opaque device bounds (>=45% height), while the source PNGs keep their full transparent padding. A single viewport layer bounds Qt Quick Shape backgrounds on the software renderer; it is not a shadow effect.

## Header iteration — stage 1

The header is fixed at 68 px with a one-pixel lower boundary. At widths below
1000 px, the Tools button uses an accessible menu glyph; the full label remains
in the tooltip. RU/EN use 40x38 px cut segments with unpadded, registered mono
text, so neither language label is elided. Header destinations are Settings,
Backups (retained GTK presentation), Diagnostics and About. Current QML settings
are session-scoped and say so; this is not full settings parity.

The mono status line counts the unfiltered external/built-in inventory and shows
the time of the last successful inventory snapshot. It does not claim that every
battery value was read at that time. Failed discovery retains the prior time.

Review: `python scripts/header_review.py`; logo contact sheet:
`QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=generic python scripts/header_review.py --logo`.
Matching snapshots are under `screenshots/redesign/header/{before,after}/`.
Toolbar/card/artwork changes belong to later stages and are not claimed here.
User acceptance of this header precedes the separate QML backup stage 1b.

## Compact toolbar — stage 2

The fixed 68 px header and 42 px toolbar place the first inventory section at
110 px (asserted by the QML smoke). Tabs use 13 px display text and 11 px mono
counts; active selection/focus uses a hairline. Search is 280 px at a 960 px
window and above; smaller windows use a cut popup. Ctrl+K and / focus search,
Escape closes the popup without leaving Dashboard, and filtering never launches
a discovery operation. Search/category state is owned by the bridge.

The built-in filter/language/reduced-motion preference is private QML UI state,
separate from device/profile settings. Normal explicit UI changes save locally;
simulation and --smoke never persist them. The GTK desktop animation preference
is read once on a worker if available, never changed. A local Reduce motion
control covers desktops without that preference. It cannot override a confirmed
system animation disable. Theme.motion becomes zero and charging/refresh motion
stops; progress text remains visible. Screenshot set: header/stage2/.

### Stage 3 card rhythm

Cards are 306 px high, scenes 164 px; a fixed battery slot prevents changing
artwork geometry when data/charging appears. Healthy connection is a bare LED;
transport is framed only if known. Type replaces the redundant external/built-in
caption. Footer uses “N settings” / Russian plural, or muted “No settings”.
Provider captions distinguish duplicate names without asserting shared identity.
Generated art uses offline opaque-bounds metadata and common family framing;
small devices get narrower scenes rather than independent normalization. No
second image shadow is drawn by QML. Segments are never filled with cached data.

### Stage 4 series and small-size review

The family scale is physical within each class family; the largest member fits
once. The QML scene may narrow for a short keyboard without rescaling its PNG.
Keycaps use neutral graphite with a restrained directional edge, dark facets and
8–12 mean L* separation from the case. Backlight comes through gaps; the laptop
plate has no perimeter light. The silhouette family distinguishes monitor/HDMI/
DP, touch surface, slim speaker grille, neutral radio disk and unknown instrument.
No exact-model photograph or manufacturer asset is claimed. Generic notes are
visible for unproven classes. Proven touchpads have no uncertainty note.

Current screenshot checklist (viewed PNGs, not a user-study claim):

- Logo hidden: cut passports, 12-cell meters, indexed rules and measurement scenes
  remain visible identifiers. The application is recognizable as a hardware tool;
  brand recall without a logo has not been tested with users.
- Squint: model titles and device silhouettes dominate; amber stays on the active
  filter, selected/focused edge, measured count or real charge. Unknown count/data
  remain muted. No decorative wallpaper or global gradient.
- Template: no capsule navigation, cyan/blue theme, glass, center icon tiles or
  blurred UI shadows. The images keep their own silhouette-based contact shadow.
- Replacement: subtype, transport, live battery and family-scale hardware bodies
  make this a peripheral passport composition, not a generic business dashboard.
- Form/data: consistent 11/6px opposing cuts, two registered families, mono values;
  plain readable names, provider source captions and collapsed local asset details.
- Density: 1/2/3/4 columns per available width; last row left-aligned; full bottom
  row reachable. Fixed 110px header/toolbar, 306px cards and 164px scenes.
- Accessibility: actual Ctrl+K typing, Escape, device focus and card keyboard entry
  exercised by smoke. Main-text contrast >=13.14:1 and amber >=7.55:1 on surfaces
  0–2; full screen-reader/a11y audit is not claimed. Reduced motion is respected.

Latest evidence: `screenshots/redesign/header/iteration4/` and
`screenshots/redesign/illustrations/iteration4/`. Full QML editor parity is a
separate open gate; the detail page still says it is read-only. GTK stays default.

## Iteration 5 / A — LC identity and counts

Compared three project-authored SVG candidates at16/24/32/40px on both backgrounds
(header/iteration5/logo-candidates.png). Selected the angular **LC** monogram:
its open C and extended L remain legible at16px; an independent amber square is
an activity indicator rather than a chart. Mouse/key alternatives lost their
interior details at small sizes. Muted #918a7d fill improves the chosen mark on
light backgrounds. Header/About/installed icon share the same SVG, MIT.

`dashboard_inventory()` is the sole filter/count pipeline: visible section/header
counts share their rows; tab counts describe available choices before applying
the chosen category; the built-in toggle counts available built-ins before hiding
them. Header explicitly includes audio and other records, never folds audio into
external peripherals. Successful discovery timestamp is independent of filtering.

Iteration5/B accent budget: <=5% of screenshot area (including artwork). Language
uses a thin outline; built-in uses a neutral surface/frame and small active mark.
Counts/settings are neutral; focus, real battery and sparse section cues retain
amber. Reproduce greyscale/mask with scripts/iteration5_review.py --accent <folder>.
B results:0.265–0.519% over eight RU/EN1000–1920 frames; see iteration5/accent/.

Iteration5/C: shared320x240 scenes; user explicitly chose **per-model fit**,
superseding previous physical family-scale presentation. Source PNG dimensions
remain physical; UI magnification is independent. Largest/compact variants can
occupy the same scene height without image deformation. Composite silhouette
including shadow is fitted inside8% vertical/12% horizontal margins (keyboards
~85% opaque width). No vertical hover motion consumes that reserve. Card labels
are12–13px, connection text inset14px horizontally. Battery slot is fixed but
hidden for proven wired/no-battery; wireless unknown gets “Charge: no data”.
Explicit battery capability overrides USB cable transport because charging a
wireless mouse must not hide its charge. Cells always floor(percentage*12/100),
including0%=0,1%=0,99%=11,100%=12; animation never fills an extra cell.

Iteration5 final: the user supplied iteration4 mouse shapes as the final contour
reference and requested clearer side controls. Stronger experimental curves were
rejected. Wireless/gaming controls are now10mm long, extend2.6mm inward and use
lighter neutral steel graphite; outward protrusion remains<=.6mm. Plain/compact
keep their earlier shapes. Generic art is labelled, not an exact-model promise.
The broad palm-rest fade was rejected; only faint dark physical corner traces
remain. Final alpha/composite review uses black and white backgrounds. Amber area
is0.2497–0.4763% in the eight reviewed top frames, including artwork. A pad-specific
hover limit preserves its horizontal margin. See docs/iteration5-report.md.

## Functional editor migration

Ace68-II editors retain the same cut controls, graphite/amber tokens and direct
QtRendering text. The original code-native 68-key diagram uses the shared
hardware layout, bounded to 42 px/key on desktop, with multi-selection and
separate desired-value/color previews. Preview stripes are not optical LED
measurements. Four layers and native banks stay in Python; QML only stages
actions. Vendor screenshots/assets are not copied into production resources.

Device, macro, key, audio and diagnostic pages now use the existing Theme and cut components; see qml-migration-progress.md. CutInput/CutCombo/CutSlider supply shared editor styling. Software-rendered cut frames use frame-only layers for reliable ScrollView clipping; glyphs remain direct QtRendering text. This migration adds no new visual palette or artwork.
