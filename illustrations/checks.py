"""Headless PNG, layout, contrast and edge checks using only Cairo + stdlib.

Fringe/banding checks are conservative heuristics, not a perceptual certificate.
Visual review on both backgrounds remains required.
"""
import argparse
import hashlib
import io
import math
from pathlib import Path
import struct
import sys
import cairo
from .layouts import LAYOUTS, validate_layout
from .models import ARTWORK_KEYS, build_model
from .render import render, silhouette
from .units import WIDTH, HEIGHT


class Pixels:
    def __init__(self, surface):
        surface.flush()
        self.surface = surface
        self.width, self.height = surface.get_width(), surface.get_height()
        self.stride = surface.get_stride()
        self.data = bytes(surface.get_data())

    def rgba(self, x, y):
        i = y * self.stride + x * 4
        values = self.data[i:i + 4]
        return (values[2], values[1], values[0], values[3]) if sys.byteorder == 'little' else (values[1], values[2], values[3], values[0])

    def bounds(self, threshold=1):
        left, top, right, bottom = self.width, self.height, -1, -1
        for y in range(self.height):
            for x in range(self.width):
                if self.rgba(x, y)[3] >= threshold:
                    left, top, right, bottom = min(left, x), min(top, y), max(right, x), max(bottom, y)
        return left, top, right, bottom


def lightness(rgb):
    channels = [v / 255 for v in rgb]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
    y = sum(a * b for a, b in zip(linear, (.2126, .7152, .0722)))
    return 116 * y ** (1 / 3) - 16 if y > 216 / 24389 else (24389 / 27) * y


def sample(pixels, model, point, density):
    x, y = model.placement.point(*point)
    return pixels.rgba(min(pixels.width - 1, max(0, round(x * density))),
                       min(pixels.height - 1, max(0, round(y * density))))[:3]


def mouse_geometry(model):
    errors=[];spans=model.checks['bezier_spans'];tangent_error=curvature_jump=0.
    if not 16<=len(spans)<=20:errors.append('mouse control count outside16–20')
    def norm(v):return math.hypot(*v)
    for i,a in enumerate(spans):
        b=spans[(i+1)%len(spans)]
        u=tuple(3*(a[3][k]-a[2][k]) for k in (0,1));v=tuple(3*(b[1][k]-b[0][k]) for k in (0,1))
        tangent_error=max(tangent_error,norm(tuple(u[k]-v[k] for k in (0,1))))
        aa=tuple(6*(a[3][k]-2*a[2][k]+a[1][k]) for k in (0,1))
        bb=tuple(6*(b[2][k]-2*b[1][k]+b[0][k]) for k in (0,1))
        ca=abs(u[0]*aa[1]-u[1]*aa[0])/norm(u)**3
        cb=abs(v[0]*bb[1]-v[1]*bb[0])/norm(v)**3
        curvature_jump=max(curvature_jump,abs(ca-cb))
    points=model.outlines[0].points;turn=0
    for i,b in enumerate(points):
        a,c=points[i-1],points[(i+1)%len(points)]
        u=tuple(b[k]-a[k] for k in (0,1));v=tuple(c[k]-b[k] for k in (0,1))
        turn=max(turn,math.degrees(math.acos(max(-1,min(1,sum(x*y for x,y in zip(u,v))/(norm(u)*norm(v)))))))
    _,y=max(points,key=lambda p:p[0]);widest=(y+model.height_mm/2)/model.height_mm
    if tangent_error>1e-8 or curvature_jump>1e-8 or turn>4:errors.append('mouse shell has a tangent/curvature/discretization discontinuity')
    if not .70<=widest<=.80:errors.append('mouse maximum width departed from iteration4 reference')
    if not .42<=model.checks['button_length_ratio']<=.48:errors.append('button zone length outside42–48%')
    if not .09<=model.checks['wheel_width_ratio']<=.11 or not 16<=model.checks['wheel_length_mm']<=18:errors.append('wheel dimensions outside9–11% shell width x16–18mm')
    ranges={'generic':(.54,.56),'wireless':(.54,.56),'gaming':(.55,.57),'compact':(.53,.54)}
    low,high=ranges[model.checks['variant']]
    if not low<=model.width_mm/model.height_mm<=high:errors.append('mouse width/length outside variant range')
    probe=-model.height_mm/2+model.height_mm*.18
    intersections=[]
    for a,b in zip(points,points[1:]+points[:1]):
        if (a[1]<=probe<b[1]) or (b[1]<=probe<a[1]):intersections.append(a[0]+(b[0]-a[0])*(probe-a[1])/(b[1]-a[1]))
    front=(max(intersections)-min(intersections))/model.width_mm
    if not .82<=front<=.95:errors.append(f'mouse front width fraction {front:.4f} outside iteration4 shoulder range')
    if model.checks['mark_length_mm']>model.height_mm*.02:errors.append('mouse mark exceeds2% length')
    sides=model.checks['side_buttons']
    for side in sides:
        if side['protrusion_mm']>.6 or not .38<=side['fraction']<=.52:errors.append('side button protrusion/position outside tolerance')
    if len(sides)==2 and not 12<=abs(sides[0]['center_y']-sides[1]['center_y'])<=14:errors.append('side button spacing outside12–14mm')
    return errors,{'tangent_error':tangent_error,'curvature_jump':curvature_jump,'max_turn_degrees':turn,'widest_fraction':widest,'front_width_fraction':front,'shell_width_length_ratio':model.width_mm/model.height_mm}


def check_png(path, key, density):
    errors, metrics = [], {}
    path = Path(path)
    try:
        raw = path.read_bytes()
    except OSError:
        return ['PNG cannot be read'], metrics
    expected = WIDTH * density, HEIGHT * density
    if raw[:8] != b'\x89PNG\r\n\x1a\n' or len(raw) < 33:
        return ['not a PNG'], metrics
    width, height, bits, colour = struct.unpack('>IIBB', raw[16:26])
    if (width, height) != expected or (bits, colour) != (8, 6):
        return [f'expected {expected}, RGBA8; got {(width, height)}, type {colour}/{bits}'], metrics
    try:
        pixels = Pixels(cairo.ImageSurface.create_from_png(str(path)))
    except (cairo.Error, OSError):
        return ['PNG decode failed'], metrics
    bounds = pixels.bounds()
    l, t, r, b = bounds
    margin = min(l, t, width - 1 - r, height - 1 - b)
    metrics['margin_px'] = round(margin / density, 2)
    if margin < 6 * density:
        errors.append(f'transparent margin {margin}px is below {6 * density}px')
    if min(l, width - 1 - r) < width * .08 or min(t, height - 1 - b) < height * .08:
        errors.append('device and shadow exceed the 8% composition padding')
    if any(pixels.rgba(x, y)[3] for x, y in
           [(x, y) for y in (0, height - 1) for x in range(width)] +
           [(x, y) for x in (0, width - 1) for y in range(height)]):
        errors.append('canvas border is not completely transparent')
    opaque = pixels.bounds(250)
    metrics['width_fraction'] = round((opaque[2] - opaque[0] + 1) / width, 4)
    metrics['height_fraction'] = round((opaque[3] - opaque[1] + 1) / height, 4)
    model = build_model(key)
    family = model.checks['family']
    if family == 'keyboard' and metrics['width_fraction'] < .775*model.width_mm/440:
        errors.append('keyboard is too small relative to the family physical scale')
    if family == 'mouse' and metrics['height_fraction'] < .695*model.height_mm/124:
        errors.append('mouse is too small relative to the family physical scale')
    if family == 'keyboard':
        case_l = lightness(sample(pixels, model, model.checks['case'], density))
        differences=[lightness(sample(pixels,model,point,density))-case_l for point in model.checks['key_centres']]
        contrast=min(differences)
        mean=sum(differences)/len(differences)
        metrics['mean_key_case_delta_L']=round(mean,2)
        metrics['minimum_key_case_delta_L'] = round(contrast, 2)
        if contrast<6 or not 8<=mean<=12:
            errors.append(f'key/case lightness difference minimum={contrast:.2f}, mean={mean:.2f}; expected minimum>=6, mean 8–12 L*')
    if family == 'mouse':
        geometry_errors,geometry_metrics=mouse_geometry(model);errors.extend(geometry_errors);metrics.update(geometry_metrics)
        gap_l = lightness(sample(pixels, model, model.checks['gap'], density))
        button_l = lightness(sample(pixels, model, model.checks['button'], density))
        metrics['button_gap_delta_L'] = round(button_l - gap_l, 2)
        if button_l - gap_l < 5:
            errors.append('primary-button gap has insufficient contrast')
    # A bright/neutral translucent edge farther than one logical pixel from an
    # opaque surface indicates a matte fringe. Black contact shadow and amber
    # LED halos are excluded by colour; premultiplied storage is checked too.
    fringe = 0
    for y in range(t, b + 1):
        for x in range(l, r + 1):
            red, green, blue, alpha = pixels.rgba(x, y)
            if max(red, green, blue) > alpha:
                errors.append('invalid premultiplied RGB at transparent edge')
                return errors, metrics
            if not 12 < alpha < 240 or red < alpha * .14:
                continue
            if max(red, green, blue) - min(red, green, blue) > alpha * .09:
                continue
            near_opaque = any(pixels.rgba(xx, yy)[3] >= 240
                for yy in range(max(0, y - density), min(height, y + density + 1))
                for xx in range(max(0, x - density), min(width, x + density + 1)))
            if not near_opaque:
                fringe += 1
    metrics['fringe_pixels'] = fringe
    if fringe > 4 * density * density:
        errors.append(f'{fringe} light matte-fringe pixels outside the 1px edge band')
    gradient = model.checks.get('gradient')
    if gradient:
        x, y, w, h = gradient
        start, end = model.checks.get('gradient_line', ((x, y + h / 2), (x + w, y + h / 2)))
        values = [round(sum(sample(pixels, model, tuple(a + (b - a) * i / 79 for a, b in zip(start, end)), density)) / 3)
                  for i in range(80)]
        metrics['gradient_levels'] = len(set(values))
        metrics['maximum_gradient_step'] = max(abs(a - b) for a, b in zip(values, values[1:]))
        if metrics['gradient_levels'] < model.checks.get('gradient_min_levels', 4) or metrics['maximum_gradient_step'] > 4:
            errors.append('gradient region is flat or contains a visible step')
    if model.symmetry_outlines:
        mask = silhouette(model, 1, outlines=model.symmetry_outlines)
        mask.flush()
        data, stride = bytes(mask.get_data()), mask.get_stride()
        difference = total = 0
        for y in range(HEIGHT):
            for x in range(WIDTH // 2):
                a, b = data[y * stride + x], data[y * stride + WIDTH - x - 1]
                difference += abs(a - b)
                total += a + b
        metrics['core_symmetry_error'] = round(difference / max(total, 1), 5)
        if metrics['core_symmetry_error'] > .015:
            errors.append('core silhouette is not symmetric (boom microphone excluded)')
    return errors, metrics


NEUTRAL_KEYS=('bluetooth_audio','builtin_audio','audio_unknown','unknown','touchpad')


def silhouette_differences(directory,keys=NEUTRAL_KEYS):
    """64 px compositional silhouette Jaccard distance, excluding contact shadow.

    Intentional aliases (unknown pointer / unknown module) are not compared;
    these five positively different classes must differ in outline, not an icon.
    """
    masks={}
    for key in keys:
        source=cairo.ImageSurface.create_from_png(str(Path(directory)/(key.replace('_','-')+'@2x.png')))
        small=cairo.ImageSurface(cairo.FORMAT_ARGB32,64,40);ctx=cairo.Context(small)
        ctx.scale(64/source.get_width(),40/source.get_height());ctx.set_source_surface(source);ctx.paint()
        pixels=Pixels(small)
        masks[key]={(x,y) for y in range(40) for x in range(64) if pixels.rgba(x,y)[3]>=230}
    return {a+'/'+b:round(1-len(masks[a]&masks[b])/max(1,len(masks[a]|masks[b])),4)
            for i,a in enumerate(keys) for b in keys[i+1:]}


def check_all(directory, deterministic=False):
    failures = []
    if all((Path(directory)/(key.replace('_','-')+'@2x.png')).is_file() for key in NEUTRAL_KEYS):
        for pair,distance in silhouette_differences(directory).items():
            if distance<.12:failures.append(f'silhouette/{pair}: {distance} is below .12 Jaccard distance at 64px')
    for name, layout in LAYOUTS.items():
        failures.extend(f'layout/{name}: {error}' for error in validate_layout(layout))
    for key in ARTWORK_KEYS:
        for density in (1, 2):
            path = Path(directory) / f'{key.replace("_", "-")}@{density}x.png'
            if not path.is_file():
                failures.append(f'{key}/{density}: missing PNG')
                continue
            errors, metrics = check_png(path, key, density)
            failures.extend(f'{key}/{density}: {error}' for error in errors)
            if deterministic:
                stream = io.BytesIO()
                render(build_model(key), density).write_to_png(stream)
                if hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(stream.getvalue()).digest():
                    failures.append(f'{key}/{density}: render bytes are not deterministic')
            print(f'{"FAIL" if errors else "PASS"}: {path.name}: {metrics}', flush=True)
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'qml_ui/assets/devices/generated')
    parser.add_argument('--deterministic', action='store_true')
    args = parser.parse_args()
    errors = check_all(args.directory, args.deterministic)
    for error in errors:
        print('FAIL:', error)
    print(f'{"FAIL" if errors else "PASS"}: {len(ARTWORK_KEYS) * 2} PNGs; {len(LAYOUTS)} layouts; {len(errors)} failures')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
