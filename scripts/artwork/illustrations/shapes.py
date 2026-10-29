"""Sampled curves and clipping-based offsets, including concave outlines."""
from dataclasses import dataclass
import math
import cairo


@dataclass(frozen=True)
class Outline:
    points: tuple

    @property
    def bounds(self):
        xs, ys = zip(*self.points)
        return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)

    def path(self, ctx):
        ctx.new_path()
        ctx.move_to(*self.points[0])
        for point in self.points[1:]:
            ctx.line_to(*point)
        ctx.close_path()

    def moved(self, dx=0, dy=0):
        return Outline(tuple((x + dx, y + dy) for x, y in self.points))


def catmull_rom(points, steps=12, closed=True):
    points = tuple(points)
    result = []
    for i in range(len(points) if closed else len(points) - 1):
        p0 = points[(i - 1) % len(points)] if closed or i else points[0]
        p1, p2 = points[i], points[(i + 1) % len(points)]
        p3 = points[(i + 2) % len(points)] if closed or i + 2 < len(points) else points[-1]
        for j in range(steps):
            t = j / steps
            result.append(tuple(.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t +
                (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t * t +
                (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t ** 3) for k in range(2)))
    if not closed:
        result.append(points[-1])
    return Outline(tuple(result))


def bezier(a, b, c, d, steps=48):
    return tuple(tuple((1 - t) ** 3 * a[k] + 3 * (1 - t) ** 2 * t * b[k] +
                       3 * (1 - t) * t * t * c[k] + t ** 3 * d[k] for k in range(2))
                 for t in (j / steps for j in range(steps + 1)))


def rounded_rect(x, y, width, height, radius=2):
    radii = (radius,) * 4 if isinstance(radius, (int, float)) else radius
    result = []
    # TL, TR, BR, BL with independent radii; no perspective or curved edges.
    for cx, cy, start, r in ((x + radii[0], y + radii[0], 180, radii[0]),
                             (x + width - radii[1], y + radii[1], 270, radii[1]),
                             (x + width - radii[2], y + height - radii[2], 0, radii[2]),
                             (x + radii[3], y + height - radii[3], 90, radii[3])):
        r = max(0, min(r, width / 2, height / 2))
        for j in range(17):
            angle = math.radians(start + 90 * j / 16)
            result.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return Outline(tuple(result))


def circle(cx, cy, radius, steps=128):
    return Outline(tuple((cx + radius * math.cos(i * math.tau / steps),
                          cy + radius * math.sin(i * math.tau / steps)) for i in range(steps)))


def ribbon(points, half_width):
    """Constant-width planar tube around a sampled open curve."""
    sides = [[], []]
    for index, point in enumerate(points):
        a, b = points[max(0, index - 1)], points[min(len(points) - 1, index + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy) or 1
        for side, sign in zip(sides, (-1, 1)):
            side.append((point[0] - sign * dy / length * half_width,
                         point[1] + sign * dx / length * half_width))
    return Outline(tuple(sides[0] + list(reversed(sides[1]))))


def offset_fill(ctx, outline, distance, paint):
    """Raster Boolean offset: positive = inset; negative = outset.

    Stroke erosion/dilation avoids offset-line spikes and self intersections at
    reflex vertices. Concave notches remain clipped, with round joins. This
    deliberately returns a Cairo group rather than an invalid polygon loop.
    """
    ctx.save()
    ctx.push_group()
    outline.path(ctx)
    paint()
    ctx.fill()
    if distance > 0:
        ctx.set_operator(cairo.OPERATOR_DEST_OUT)
        ctx.set_source_rgba(0, 0, 0, 1)
        outline.path(ctx)
        ctx.set_line_width(2 * distance)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
    elif distance < 0:
        outline.path(ctx)
        paint()
        ctx.set_line_width(-2 * distance)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
    ctx.pop_group_to_source()
    ctx.set_operator(cairo.OPERATOR_OVER)
    ctx.paint()
    ctx.restore()
