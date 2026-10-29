"""Offline Cairo layer compositor. No meshes, camera, or perspective transform."""
from dataclasses import dataclass, field
from functools import lru_cache
import math
from pathlib import Path
import cairo
from .light import multiply, set_gradient
from .materials import MATERIALS
from .palette import AMBER
from .shapes import Outline, offset_fill
from .units import WIDTH, HEIGHT, fit


@dataclass
class Model:
    key: str
    width_mm: float
    height_mm: float
    outlines: tuple
    draw: object
    checks: dict = field(default_factory=dict)
    symmetry_outlines: tuple = ()

    @property
    def centre(self):
        xs, ys = zip(*(point for outline in self.outlines for point in outline.points))
        return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2

    @property
    def placement(self):
        return fit(self.width_mm, self.height_mm, self.centre, self.checks.get('family', ''))


class Painter:
    def __init__(self, context, pixel_scale):
        self.ctx = context
        self.pixel_scale = pixel_scale

    def fill(self, shape, colour, alpha=1):
        shape.path(self.ctx)
        self.ctx.set_source_rgba(*colour, alpha)
        self.ctx.fill()

    def line(self, points, colour, width=.4, alpha=1):
        ctx = self.ctx
        ctx.new_path()
        ctx.move_to(*points[0])
        for point in points[1:]:
            ctx.line_to(*point)
        ctx.set_source_rgba(*colour, alpha)
        ctx.set_line_width(width)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()

    def detail_shadow(self, shape, amount=.6):
        for i, opacity in ((3, .08), (2, .13), (1, .28)):
            self.fill(shape.moved(amount * .28 * i, amount * .6 * i), (0, 0, 0), opacity)

    def object(self, shape, material='graphite_matte', bevel=None, panel=True, rim=False, shadow=False):
        ctx = self.ctx
        mat = MATERIALS[material]
        x, y, w, h = shape.bounds
        minor = min(w, h)
        b = bevel if bevel is not None else minor * .018
        if shadow:
            self.detail_shadow(shape, max(.3, b * .5))
        led = material == 'led_amber'
        # 2: body; 3: edge ring; 4: inner panel. Every fill stays clipped.
        shape.path(ctx)
        set_gradient(ctx, shape.bounds, multiply(mat.base, 1.0 if led else 1.10), multiply(mat.base, .89), self.pixel_scale)
        ctx.fill()
        ctx.save()
        shape.path(ctx)
        ctx.clip()
        shape.path(ctx)
        set_gradient(ctx, shape.bounds, multiply(mat.base, 1.0 if led else 1.28), multiply(mat.base, .77), self.pixel_scale)
        ctx.set_line_width(b * 2)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
        ctx.restore()
        if panel:
            def paint_panel():
                set_gradient(ctx, shape.bounds, multiply(mat.base, 1.06), multiply(mat.base, .92), self.pixel_scale)
            offset_fill(ctx, shape, b * 1.5, paint_panel)
        # 5: directional edge specular, stronger on glass, no external halo.
        ctx.save()
        shape.path(ctx)
        ctx.clip()
        specular = cairo.LinearGradient(x, y, x + w * .8, y + h * .9)
        specular.add_color_stop_rgba(0, 1, 1, 1, 0 if led else min(.5, mat.edge_gloss))
        specular.add_color_stop_rgba(.55, 1, 1, 1, 0 if led else mat.edge_gloss * .22)
        specular.add_color_stop_rgba(1, 1, 1, 1, 0)
        shape.path(ctx)
        ctx.set_source(specular)
        ctx.set_line_width(max(.35 / self.pixel_scale, minor * (.006 + .006 * (1 - mat.roughness))))
        ctx.stroke()
        if material == 'glass_dark':
            glass = cairo.LinearGradient(x, y, x + w, y + h)
            for position, alpha in ((0, .035), (.22, .12), (.40, .02), (.58, 0), (1, 0)):
                glass.add_color_stop_rgba(position, 1, 1, 1, alpha)
            ctx.set_source(glass)
            ctx.paint()
        if rim:
            edge = cairo.LinearGradient(x, y, x + w * .65, y + h)
            edge.add_color_stop_rgba(0, *AMBER, mat.rim_intensity)
            edge.add_color_stop_rgba(.45, *AMBER, 0)
            edge.add_color_stop_rgba(.85, *AMBER, 0)
            edge.add_color_stop_rgba(1, *AMBER, mat.rim_intensity * .65)
            shape.path(ctx)
            ctx.set_source(edge)
            ctx.set_line_width(1. / self.pixel_scale)
            ctx.stroke()
        ctx.restore()

    def glow(self, shape, intensity=.30):
        # Bounded layered silhouette dilation; only LEDs have this halo.
        for radius, opacity in ((2.6, .025), (1.6, .045), (.8, .08)):
            offset_fill(self.ctx, shape, -radius / self.pixel_scale,
                        lambda a=opacity: self.ctx.set_source_rgba(*AMBER, a * intensity / .30))
        self.object(shape, 'led_amber', bevel=.15, panel=False)


@lru_cache(maxsize=32)
def gaussian_kernel(sigma):
    radius = max(1, math.ceil(2 * sigma))
    weights = [math.exp(-x * x / (2 * sigma * sigma)) for x in range(-radius, radius + 1)]
    total = sum(weights)
    return tuple(weight / total for weight in weights)


def blur_mask(surface, sigma):
    surface.flush()
    width, height, stride = surface.get_width(), surface.get_height(), surface.get_stride()
    source = memoryview(surface.get_data())
    kernel = gaussian_kernel(round(max(.5, sigma), 3))
    radius = len(kernel) // 2
    temp = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            temp[y * width + x] = round(sum(source[y * stride + xx] * weight
                for offset, weight in enumerate(kernel) if 0 <= (xx := x + offset - radius) < width))
    output = cairo.ImageSurface(cairo.FORMAT_A8, width, height)
    data = output.get_data()
    stride_out = output.get_stride()
    for y in range(height):
        for x in range(width):
            value = round(sum(temp[yy * width + x] * weight
                for offset, weight in enumerate(kernel) if 0 <= (yy := y + offset - radius) < height))
            # Smoothly remap the faint Gaussian tails to zero. This preserves
            # the 0..255 range/core opacity and avoids a barely visible haze
            # extending into the required transparent composition padding.
            data[y * stride_out + x] = round(max(0, value - 16) * 255 / 239)
    output.mark_dirty()
    return output


def silhouette(model, density=1, outlines=None, dx=0, dy=0):
    surface = cairo.ImageSurface(cairo.FORMAT_A8, int(WIDTH * density), int(HEIGHT * density))
    ctx = cairo.Context(surface)
    placement = model.placement
    ctx.scale(density, density)
    ctx.translate(placement.x + dx, placement.y + dy)
    ctx.scale(placement.scale, placement.scale)
    ctx.translate(-placement.origin_x, -placement.origin_y)
    ctx.set_source_rgba(1, 1, 1, 1)
    for shape in outlines if outlines is not None else model.outlines:
        shape.path(ctx)
        ctx.fill()
    surface.flush()
    return surface


def contact_shadow(ctx, model, placement):
    # Low-frequency masks at half resolution are independent of output density.
    # The narrow AO pass uses full logical resolution to keep the edge attached.
    object_w, object_h = model.width_mm * placement.scale, model.height_mm * placement.scale
    for density, dx, dy, sigma, alpha in ((.5, .015 * object_w, .045 * object_h, .035 * object_h, .55),
                                          (1, 0, .012 * object_h, .008 * object_h, .65)):
        mask = silhouette(model, density, dx=dx, dy=dy)
        blurred = blur_mask(mask, sigma * density)
        ctx.save()
        ctx.scale(1 / density, 1 / density)
        ctx.set_source_rgba(0, 0, 0, alpha)
        ctx.mask_surface(blurred, 0, 0)
        ctx.restore()


def render(model, density=1):
    if density not in (1, 2):
        raise ValueError('Artwork density must be 1 or 2')
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH * density, HEIGHT * density)
    ctx = cairo.Context(surface)
    ctx.set_antialias(cairo.ANTIALIAS_BEST)
    ctx.scale(density, density)
    placement = model.placement
    contact_shadow(ctx, model, placement)
    ctx.translate(placement.x, placement.y)
    ctx.scale(placement.scale, placement.scale)
    ctx.translate(-placement.origin_x, -placement.origin_y)
    model.draw(Painter(ctx, placement.scale * density))
    surface.flush()
    return surface


def save_png(model, path, density=1):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    surface = render(model, density)
    surface.write_to_png(str(path))
    return path
