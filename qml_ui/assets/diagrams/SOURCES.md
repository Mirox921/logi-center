# Editor schematics

`g502.svg` and `generic.svg` are original project-authored schematic geometry
from `mouse_art.py` (MIT), exported by `scripts/generate_mouse_diagrams.py`.
They use the same 480×440 coordinate frame as `mouse_models.layout`.
These are button-location diagrams, not product photographs or live RGB views.
No manufacturer or store images are included. The generic diagram does not
claim an exact model or a known physical position for extra buttons.

`k7-dock.svg` is an original project-authored vector (MIT), drawn from the dock
outline visible in the user's 2026-10-28 M HUB reference screenshot. It contains
no copied bitmap, manufacturer logo or traced photo. QML adds a separate preview
strip; that preview does not measure the physical LEDs. See docs/k7-dock-rgb.md.

`k7-buttons.svg` is an original top-view K7 schematic (MIT), constructed from
the user's 2026-10-28 button-editor reference. It contains no bitmap, brand logo
or copied SVG paths. The five interactive anchors and native button indices are
separate in `k7_settings.py`; the underside DPI button is intentionally excluded.
On 2026-10-28 the narrow original drawing was widened by 1.45 about its center,
with identical mapping applied to the five anchors. The body width/length is
approximately 0.54; the original 400×600 frame and hardware button IDs remain.
