"""Layered 2D materials; roughness controls edge-highlight width and gain."""
from dataclasses import dataclass
from .palette import AMBER, neutral


@dataclass(frozen=True)
class Material:
    base: tuple
    roughness: float = .75
    edge_gloss: float = .18
    rim_colour: tuple = AMBER
    rim_intensity: float = .28


MATERIALS = {
    'graphite_matte': Material(neutral('surface4'), .85, .20),
    'keycap_pbt': Material(neutral('surface4', .09), .86, .18, rim_intensity=.06),
    'rubber_dark': Material(neutral('surface1', -.018), .94, .08, rim_intensity=.03),
    'glass_dark': Material(neutral('surface2', -.025), .30, .46, rim_intensity=.15),
    'led_amber': Material(AMBER, .35, .25, rim_intensity=.30),
    'metal_dark': Material(neutral('border', .055), .40, .31, rim_intensity=.14),
    'side_control': Material(neutral('border', .02), .82, .18, rim_intensity=.02),
    'touch_surface': Material(neutral('surface3', .01), .91, .08, rim_intensity=.02),
    'panel': Material(neutral('surface3', -.02), .88, .12, rim_intensity=.08),
    'speaker_cone': Material(neutral('surface2'), .80, .12, rim_intensity=.02),
}
