# G502 HERO SVG proposal

The user approved this candidate. Its production copy is now
`qml_ui/assets/devices/exact/g502-hero.svg`; this proposal remains as the
review and rollback source. The previous editor diagram and generic Dashboard
PNG remain in the repository. The SVG is an editable master; it contains paths and
gradients only, no embedded bitmap or external references. The accompanying
JSON records its viewBox, body bounds and the existing editor anchor source.

The editor already uses an original project SVG exported from `mouse_art.py` in
a 480×440 frame. Its 11 numbered targets and selected-button leader line are
QML overlays driven by `mouse_models.G502` and `editor_callouts`; the artwork
does not draw or own these controls. The proposed SVG keeps that coordinate
frame and the recognizable asymmetric shell, thumb shelf, scroll wheel, upper
DPI switches and side switches. It removes the schematic's invented-looking
palm symbol and neutralizes the fixed colored DPI indicators. No manufacturer
logo or photograph is embedded.

The Dashboard selects the approved SVG only for the G502 HERO USB product ID.
This is a product-level illustration, not a claim about a hardware revision.
Other mice keep the generated class image. A user-selected image retains
absolute priority.

## Shared integration

1. The approved SVG is copied to `qml_ui/assets/devices/exact/`; `models.json`
   registers its product ID and visual geometry. Device records remain separate.
2. The Dashboard loads this SVG with the recorded visual bounds and native
   480:440 aspect. Its scene scales those bounds into the current device stage
   without stretching. Qt Quick can render the SVG directly; no runtime Cairo.
3. `MouseButtons.qml` points at the same master. Independent QML
   numbered targets, focus, selection and connectors, using the existing
   480×440 anchors. Do not bake hitboxes into the picture.
4. If a later revision needs different artwork or button geometry, add a
   revision-specific entry and anchors after confirming that revision. A generic
   class PNG remains the fallback for other product IDs.

## Future device workflow

Identify the exact VID/PID and confirmed revision; obtain a reference with a
clear right to inspect; check existing project artwork; optionally use imagegen
for a concept, never for unverified button geometry; draw a clean SVG master;
record its viewBox, visual bounds and any anchors in metadata; render it in Qt
Quick at card/editor sizes; compare every interactive anchor and callout with
the actual hardware before registering the asset. Keep sources and license in
`SOURCES.md`. Do not automatically create images for detected devices.

The [Logitech product page](https://www.logitechg.com/en-us/products/gaming-mice/g502-hero-gaming-mouse.html)
confirms the wired G502 HERO's 11 programmable buttons and one LIGHTSYNC zone.
The product imagery was used only to understand the overall arrangement; the
geometry remains a project-authored schematic study. The exact silhouette and
button coordinates have **not** been checked against the user's physical mouse
or a redistribution-cleared orthographic reference photo.
