"""Millimetre geometry, uniform fitting and explicit preview magnification."""
from dataclasses import dataclass

WIDTH, HEIGHT = 512, 320
MM_TO_PX = 1.3
MARGIN = .08


@dataclass(frozen=True)
class Placement:
    scale: float
    x: float = WIDTH / 2
    y: float = HEIGHT * .465
    origin_x: float = 0
    origin_y: float = 0

    @property
    def magnification(self):
        return self.scale / MM_TO_PX

    def point(self, x, y):
        return self.x + (x - self.origin_x) * self.scale, self.y + (y - self.origin_y) * self.scale


def fit(width_mm, height_mm, centre=(0, 0), family=''):
    """Fit the largest family member once; all variants keep their mm scale.

    The QML stage uses offline bounds to meet minimum visible size without
    independently re-normalizing each PNG. Other successful classes keep fit.
    """
    if family == 'mouse':width_mm,height_mm=70,124
    elif family == 'keyboard':width_mm,height_mm=440,140
    horizontal = WIDTH * (1 - 2 * MARGIN) / (width_mm * 1.03 + .14 * height_mm)
    if family == 'keyboard':horizontal=max(horizontal,WIDTH*.785/width_mm)
    scale = min(horizontal, HEIGHT * (1 - 2 * MARGIN) / (height_mm * 1.18))
    return Placement(scale, origin_x=centre[0], origin_y=centre[1])
