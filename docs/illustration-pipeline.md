# Layered 2D device artwork (offline)

The `illustrations/` package is developer tooling. Both Dashboard frontends load
prebuilt transparent PNGs; neither imports this package. `mouse_art.py` remains
an interactive GTK button-selection diagram, whose hit regions must remain
aligned with its callouts. It no longer supplies the GTK Dashboard artwork.
There are no meshes, cameras, perspective transforms, runtime generation,
manufacturer photo assets, or extra Python dependencies in this pipeline.

## Reproduce

Python 3 and pycairo are sufficient (`python-cairo` on Arch). No Pillow, numpy,
Qt, GTK, external converter, model download or system configuration is needed
for generation, the gallery or image checks.

```sh
python -c "import cairo; print(cairo.version)"
python -m illustrations.render_all
python -m illustrations.checks
python -m illustrations.checks --deterministic
python scripts/icon_gallery.py
python scripts/illustration_dashboard.py --stage after
```

The last command additionally needs the optional PySide6 frontend. It uses an
isolated simulation snapshot with seven devices, no real discovery, hardware
writes or audio capture. It captures RU/EN at 1000/1280/1600/1920 px, top/bottom,
built-in/audio sections, focus, empty and detail states. JSON measurements in
each language directory record the **opaque device height**, after scene
clipping, divided by card height. The script fails if any of the seven is below
45% or any opaque silhouette is clipped by its scene. The simulation label stays visible.

Single-class and native-size review:

```sh
python -m illustrations.render_all --only mouse_gaming keyboard_65 headset --output /tmp/logi-art
python -m illustrations.review --input /tmp/logi-art --output /tmp/logi-review
```

Local, private reference contour comparison (default output `/tmp`):

```sh
python -m illustrations.reference_review
```

Photos in `docs/k7-ultra-top.png`, `docs/ace68-ii-top.png`,
`docs/g502-hero-top.png`, and `docs/g-pro-x-front.png` were supplied in the
workspace. Their revisions and redistribution licenses are not verified. They
are inspected locally, excluded from source/package archives, and never
sampled, traced into a product asset or copied into generated art. The private
overlays show why the generic mouse/headset must not claim G502/G PRO X accuracy.

## Files and conventions

- `units.py`: millimetre dimensions, one isotropic fit and explicit preview
  magnification. Logical canvas 512×320; outputs 512×320 / 1024×640 RGBA8.
- `shapes.py`: Catmull–Rom/Bezier outlines, independent rounded corners and
  clipping-based inset/outset. Stroke erosion/dilation handles concave notches
  without parallel-edge intersection spikes.
- `palette.py`: a tested mirror of the existing QML Theme tokens. Hardware
  plastic uses neutral luminance derived from those tokens, avoiding brown
  surfaces. Amber is the exact Theme accent.
- `materials.py` / `light.py`: matte graphite, PBT, rubber, glass, metal and LED
  parameters; upper-left key / lower-right fill; cached gradient surfaces with
  deterministic ±0.5 LSB ordered dither. No noise texture or random seed.
- `render.py`: silhouette contact shadow, narrow AO pass, diagonal body fill,
  constant inset bevel, inner panel, clipped edge specular, detail seams and
  restrained amber LED/rim. Gaussian kernels are cached, separable and bounded
  to 2σ; faint tails are smoothly remapped to zero to preserve transparent
  margins. Main shadow σ=0.035H, AO σ=0.008H, with the specified directional
  offsets and 0.55/0.65 source opacities. Edges use premultiplied Cairo alpha.
- `layouts.py`: ANSI 60 (61), Ace68-II-compatible 65 (68), TKL (87), full (104),
  and a generic island laptop layout (78). Key rectangles are in u, include
  explicit spacing and never overlap. The 68 labels match the existing adapter.
- `models/`: top views for pointers/keyboards/touchpads/receivers, front views
  for audio. No object rotation, tilted case, feet or warped keyboard edge.
- `render_all.py`: stable ordered registry, canonical hyphenated filenames;
  for example `mouse-gaming@1x.png`, `keyboard-65@2x.png`. Runtime selection
  still understands the old underscore pack for upgrades. It also writes the
  independent neutral `fallback.png` / `fallback@2x.png` copies.
- `checks.py`: validates sizes/PNG format, transparent padding (>=8% per axis
  and >=6 px), mouse height >=70%, keyboard width >=78%, key/case Lab L* delta
  >=10, button-gap contrast, neutral matte-fringe proximity, expected core
  symmetry and sampled gradient levels/steps. A one-sided headset microphone
  is excluded from symmetry. Banding/halo checks are heuristics: native images
  on both backgrounds are also inspected.

The renderer uses a shared nominal mm→px scale, then uniform per-preview fit.
A literal shared final physical scale conflicts with the requested occupancies:
120 mm mouse at 70% canvas height requires >=1.867 px/mm, making a 315 mm
keyboard >=588 px wide on a 512 px canvas. Thus relative dimensions remain
correct **within** each illustration; isolated previews are magnified to fit,
not a physical-size comparison between cards. `Placement.magnification`
exposes that factor. No anisotropic stretching is used.

## Add a class, variant or layout

1. Describe physical bounds and closed outlines in mm in a model module. Return
   a `Model` with its silhouette union, draw callback and safe quality probes.
2. Reuse `Painter.object`, materials and light. Details have their own bevels;
   never add an arbitrary ellipse shadow or scene grid to a PNG.
3. Add a stable key to `ARTWORK_KEYS`. Add a metadata-based mapping in
   `device_artwork.artwork_key` only when that subtype/layout is actually known.
   Connection or a marketing name cannot establish a detailed physical model.
4. For a keyboard add `Layout`/`Key` data, declared unit extents, counts and
   special-key widths. Validate occupied intervals plus explicit empty space.
5. Render both densities, run checks, inspect native review pairs and gallery,
   and capture Dashboard. The installer already copies the asset tree; keep
   `illustrations/` out of the runtime module list.

## Source priority and user images

Selection remains user → confirmed exact revision → registered system asset →
class render → neutral module. No exact-revision or system registry entries are
currently bundled. Stock Bluetooth/USB/analog audio with no typed form metadata
uses a neutral module, not invented headphones/speakers. An untyped internal
pointer also uses a neutral module; a known touchpad has its own glass surface.

A user image can be chosen/previewed/reset on the QML device page. For manual
installation:

1. Photograph straight from above (mouse/keyboard/touchpad) or straight in front
   (audio), with soft side lighting. Keep all edges in frame.
2. Remove the background in an image editor supporting transparency. Save a
   transparent PNG or WebP; keep the original aspect ratio. SVG must have no
   scripts, external URLs, images, styles or entities.
3. Copy the selectable **Image slug / Код изображения** from the device page.
   It is a local stable physical-identity hash, not the model name or VID/PID.
4. Save `~/.local/share/logi-center/device-images/<slug>.png` (or `.webp`/`.svg`;
   `$XDG_DATA_HOME` is honored). Reopen/refresh discovery after a manual change.
   PNG is preferred if multiple manual extensions exist. Files are limited to
   8 MiB / 48 megapixels. GUI selection verifies decoding before saving.

Old managed `device-artwork/` preferences continue to be read without deleting
or rewriting those images. New choices are atomic writes into `device-images/`.
Invalid files fall back safely. No user image, raw device identity or local path
is included in public diagnostics or these screenshots. HiDPI PNG selection,
texture caching and aspect-preserving loading apply in QML; no second shadow
is attached to the image. GTK Dashboard uses the same provider and PNG pack.

## Visual iteration record

Native review pairs contain both backgrounds and both output densities under
`docs/screenshots/redesign/illustrations/iterations/01`, `02`, `03`; final
post-fit pairs are in `04`. They were opened with the image viewer.

| Class | Pass 1: defects → changes | Pass 2: defects → changes | Pass 3 and final verification |
|---|---|---|---|
| Mouse | Spline button tips formed ears; rear button edges were wavy; palm was flat → explicit Bezier panels, flat clean joint, controlled crown fill. | Central gap blended with the case; rear highlight showed concentric levels; button edges needed stronger separation → dark 1.2 mm seam, dithered material crown, individual panel edge masks. | Straight top-down silhouette, distinct ribbed wheel/DPI/side controls, no smile or clipped edge. Fit includes shadow. Generic / gaming / wireless / compact remain class art. |
| Keyboard 65 | Silver-like thick bevel; circular key dishes read as pillows; backlight disappeared → matte edge gain and gloss reduced, backlight confined to slots. | Spacebar still had a circular spot; 4:3 framing wasted card space; image remained too small → vertical dish shading, 8:5 canvases and width-aware scene composition. | 68 keys match adapter labels; 16u rows; straight case; visible gaps. Lab contrast is tested for every cap. Cards reduced to 260 px and occupancy measured, preserving aspect ratio. |
| Headset | Narrow tall cups looked like capsules; boom narrowed at its vertical join; silhouette was below center → wider cups, normal-offset ribbon and bounds-centered placement. | Inner straight mark looked like a scratch; pivots were plain stubs; boom had no socket → scratch removed, metal pivot details and attached socket added. | Joined front-view headband/cups/boom, symmetric core, consistent upper-left edges. No G PRO X model claim or fabricated fabric texture. |

The final pass also shortened faint shadow tails and refit wide devices so the
shadow stays inside an 8% margin while keyboard width remains >=78%. A single
opaque Dashboard viewport layer fixes Qt software Shape backgrounds leaking
above the scroll clip; no per-card shadow/layer effect was added. Focus testing
now searches the visual tree, so it actually exercises Repeater delegates.

Other class review: touchpad has a glass plane/button divider rather than a
mouse face; USB plug slots remain distinct; monitor has an attached stand and
connector glyph; microphone grille/yoke/base and speaker driver rings are
visible at 1x/2x. Unknown audio/internal pointers use the neutral module.

## Evidence and remaining limits

- [Before / after Dashboard matrix](screenshots/README.md#historical-reviews)
- [Dark contact sheet](screenshots/README.md#historical-reviews),
  [light](screenshots/README.md#historical-reviews), each also at `@2x`.
- [Class → file → source table](screenshots/README.md#historical-reviews).
- [Review log](screenshots/README.md#historical-reviews).

These are authored class illustrations, not photographs. Headset padding and
speaker mesh have less fine texture than the mouse controls and keyboard caps;
their silhouettes are readable, so they are not replaced by a misleading model
asset. Untyped Bluetooth/audio and unknown internal pointers intentionally stay
on a neutral module. Real model-specific photos with confirmed revision and
permission could improve those matches later. No release or hardware writes
are part of this change. QML captures are offscreen simulations, not a claim of
real Hyprland verification or full frontend parity.

Final Dashboard correction: the first compact-card capture exposed a clipped
keyboard lip, despite the visible-area ratio being large enough. The PNG's
above-center composition was explicitly compensated in the card and the wide
image bounds reduced. Captures now assert both >=45% opaque height and complete
silhouette fit. All seven fixtures are unclipped at all four widths; the final
range is 45.4%–47.9%. Source PNGs were not cropped or distorted to pass this check.

## Current stage 4: common family scale and graphite series (2026-10-25)

This section supersedes the historical per-variant 78%/70% canvas fitting and
260px-card occupancy notes above. Canvas remains 512x320 / 1024x640. The largest
member is fitted **once per family**: mouse reference 70x124 mm, keyboard reference
440x140 mm. Compact is 55x103, generic/wireless 66x120, gaming 70x124. Keyboard
width order is 295 / 315 / 360 / 440 mm. Variants keep the same isotropic mm scale.
All source PNGs and shadows retain >=6 px margin (actual minimum is larger).
A single physical scale across unrelated device classes is not claimed.

`python -m illustrations.render_all` writes PNGs and `geometry.json` opaque
bounds. The runtime reads this bounded JSON and uses a stable family transform;
it never imports Cairo or the renderer. Scenes are 164px high; narrow mouse and
compact-keyboard stages avoid large empty sides. The latest minimum gate measures
actual opaque pixels projected through QML: mouse >=60% scene height, keyboard
>=70% scene width. This replaces the incompatible old per-card opaque-height gate
for very wide keyboards. The scene itself occupies 53.6% of card height. No image
stretching/cropping or second QML/CSS shadow is used.

Regenerate a subset with `python -m illustrations.render_all --only keyboard_65
keyboard_full`; metadata is rewritten over all existing outputs. Custom output:
`--output /tmp/logi-art-review`. Keyboard API `build('65', backlight=.55)` accepts
0..1; zero disables gap/perimeter light. Laptop uses one-quarter of that light
and no perimeter glow. PBT facet is darker than its face, matte top uses neutral
Theme-derived graphite; mean sampled top/body contrast must stay 8–12 L*, minimum
>=6. Laptop body probe is the actual flat panel above the left arrow, not the
bright plate-edge specular. No legends, perspective or curved chassis edges.

TKL87 / Full104 use 0.5u Esc/function-group, functional/main, main/navigation and
navigation/numpad gaps. ANSI empty navigation cells and the area above numpad are
intentional physical gaps, not missing keys. All main/function rows are 1u;
only numpad Enter/+ span rows. Data declares row occupancy plus intentional gaps.
Laptop78 has a .7u function row and half-height left/right plus stacked up/down.

Artwork selection requires typed evidence: ID_INPUT_TOUCHPAD/input_subtype ->
touchpad without caveat; internal pointer without that proof -> neutral with
“Type unknown” + “Generic illustration”. Unknown BT audio -> neutral round radio
module. A typed BT speaker can use speakers. HDMI/DP connector glyph is 44/270
(16.3%) of screen width, chosen by typed subtype or explicit backend route; no
connector is guessed from a display title. Generic monitor keeps an audio glyph.
Touchpad is matte with microtexture, thin rim, 17% button zone and central divider;
no power indicator. Different neutral classes are checked at 64px using alpha-core
Jaccard distance >=0.12; identical intentional aliases are exempt.

Reproduce QA:

```
python -m illustrations.checks --deterministic
python scripts/icon_gallery.py --output docs/screenshots/redesign/illustrations/iteration4/after
python scripts/ui_iteration_smoke.py --stage cards --matrix --output docs/screenshots/redesign/header/iteration4/after
python scripts/illustration_dashboard.py --stage after
```

The gallery adds dark/light 1x/2x full/series/neutral sheets, 64px neutral sheet,
and an actual relative filename + SHA-256 table. The Dashboard fixture uses ten
explicit mock devices over real DeviceManager and a forbidden real runner. QML
render failure is handled asynchronously and advances the file-signature source
chain; hash query invalidates replaced textures. User artwork stays isolated in
simulation. GTK and QML load the same committed outputs.

## Iteration5: latest reference decisions supersede historical fitting notes

The user chose per-model scene fitting and subsequently supplied iteration4
mouse images as the authoritative silhouette. Models retain iteration4 dimensions;
C2 periodic Bezier spans smooth the waist. Mouse buttons are clipped light zones
inside one body, with proportional wheel, .8–1mm seams and a <=2% class mark.
Wireless/gaming side controls were explicitly requested by the user: outlines
follow the actual edge, centre distance13mm, protrusion<=.6mm. They are illustration
features, not backend capabilities. Plain/compact stay side-button-free.

Rejected intermediate shape-cycle2 curves and broad faded palm-rest are kept only
in review screenshots. Final touchpad has no broad panel mask; thin source-dark
palm-rest corner traces remain, both1x/2x. Confirmed variant115x74 has click zone
at83.5% and low-contrast microtexture; pointer_generic105x75 has neither. Legacy
mouse_builtin loads the neutral generic surface. Type is established only by
positive metadata; unknown pointer stays labelled Type unknown/generalized.

New geometry checks verify C2 continuity, iteration4 reference silhouette IoU>=.97,
wheel/seam/side-control bounds, generic-vs-confirmed data and64px silhouette
separation. Use scripts/iteration5_review.py --compare-source <reference-folder>
--crops <PNG-folder> --output <folder> for black/white1x/2x4x crops and side-by-side
before/after sheets. All source assets remain offline/project-authored MIT.

## G502 supplied SVG transport variants

Use `exact/models.json` for Dashboard selection, `mouse_models.G502_ART` for
shared canvas/anchor data, and `EditorController.g502Canvas` for top/side and
connection selection. Keep overlays separate and preserve uploaded SVG bytes.
Read the native viewBox, fit with PreserveAspectFit, and scale normalized
anchors using the same painted image rectangle. Add future devices by exact
verified product IDs, never by a guessed display name. Verify each visible
button label and anchor through fake-I/O QML clicks at narrow/desktop sizes.
Raster concepts do not establish button geometry. See g502-workflow.md.
