"""Offline art invariants; no GTK, Qt, hardware discovery or audio imports."""
import contextlib
from dataclasses import replace
import hashlib
import io
import os
from pathlib import Path
import re
import runpy
import tempfile
import unittest
from unittest.mock import patch
import cairo

from scripts.artwork.illustrations.checks import check_all, check_png
from scripts.artwork.illustrations.layouts import LAYOUTS, validate_layout, ALPHA_WIDTHS
from scripts.artwork.illustrations.models import ARTWORK_KEYS, build_model
from scripts.artwork.illustrations.palette import TOKENS
from scripts.artwork.illustrations.render import render
from scripts.artwork.illustrations.shapes import Outline, offset_fill

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'assets/devices/generated'


class IllustrationPipeline(unittest.TestCase):
    def test_ansi_and_ace_layouts_counts_geometry_and_special_keys(self):
        self.assertEqual([sum(row) for row in ALPHA_WIDTHS], [15] * 5)
        for name, count in (('60', 61), ('65', 68), ('tkl', 87), ('full', 104), ('laptop', 78)):
            layout = LAYOUTS[name]
            with self.subTest(name=name):
                self.assertEqual(len(layout.keys), count)
                self.assertEqual(validate_layout(layout), [])
        for label, width in (('Backspace', 2), ('Enter', 2.25), ('LShift', 2.25), ('Space', 6.25)):
            key = next(key for key in LAYOUTS['60'].keys if key.label == label)
            self.assertEqual(key.width, width)
        from logi_center.adapters.mchose.ace68_adapter import LAYOUT
        # Generic 65% artwork has a grave key here; exact Ace68-II's native
        # index 34 is Insert. A generic illustration is not a hardware key map.
        ace_labels=[label.replace('↑', 'Up').replace('←', 'Left').replace('↓', 'Down').replace('→', 'Right')
                    for row in LAYOUT for label in row]
        self.assertEqual(ace_labels[14],'Insert')
        ace_labels[14]='`'
        self.assertEqual([key.label for key in LAYOUTS['65'].keys],
                         ace_labels)
        self.assertEqual([sum(key.width for key in LAYOUTS['65'].keys if key.y == y) for y in range(5)], [16] * 5)
        altered = replace(LAYOUTS['60'], keys=tuple(replace(key, width=6) if key.label == 'Space' else key
                                                  for key in LAYOUTS['60'].keys))
        self.assertTrue(any('row' in error for error in validate_layout(altered)))

    def test_mouse_c2_shell_and_confirmed_geometry_limits(self):
        from scripts.artwork.illustrations.checks import mouse_geometry
        for key in ('mouse','mouse_gaming','mouse_compact','mouse_wireless'):
            model=build_model(key);errors,metrics=mouse_geometry(model)
            self.assertEqual(errors,[],(key,metrics))
            self.assertEqual(len(model.checks['side_buttons']),2 if key in ('mouse_gaming','mouse_wireless') else 0)
            self.assertEqual(bool(model.symmetry_outlines),key!='mouse_gaming')

    def test_mouse_silhouette_stays_close_to_user_selected_iteration4(self):
        from scripts.artwork.illustrations.checks import Pixels
        reference=ROOT/'tests/fixtures/artwork/iteration4'
        for key in ('mouse','mouse_gaming','mouse_wireless','mouse_compact'):
            filename=key.replace('_','-')+'@1x.png'
            def mask(path):
                p=Pixels(cairo.ImageSurface.create_from_png(str(path)))
                return {(x,y) for y in range(p.height) for x in range(p.width) if p.rgba(x,y)[3]>=245}
            a,b=mask(reference/filename),mask(ASSETS/filename)
            self.assertGreaterEqual(len(a&b)/len(a|b),.97,key)

    def test_touchpad_and_generic_are_different_without_panel_mask(self):
        confirmed,generic=build_model('touchpad'),build_model('pointer_generic')
        self.assertTrue(confirmed.checks['click_zone']);self.assertTrue(confirmed.checks['microtexture'])
        self.assertFalse(generic.checks['click_zone']);self.assertFalse(generic.checks['microtexture'])
        self.assertAlmostEqual(generic.checks['surface_ratio'],1.4)
        self.assertTrue(1.5<=confirmed.checks['surface_ratio']<=1.6)
        self.assertFalse(confirmed.checks['panel_mask']);self.assertFalse(generic.checks['panel_mask'])

    def test_touchpad_differs_from_monitor_keyboard_and_audio_at64px(self):
        from scripts.artwork.illustrations.checks import silhouette_differences
        for key,distance in silhouette_differences(ASSETS,keys=('touchpad','display_audio','builtin_audio','unknown','keyboard_65','keyboard_full')).items():
            if key.startswith('touchpad/'):
                self.assertGreaterEqual(distance,.15,(key,distance))

    def test_extended_block_gaps_and_laptop_function_and_arrow_geometry(self):
        for name in ('tkl','full'):
            keys={k.label:k for k in LAYOUTS[name].keys}
            self.assertEqual(keys['F1'].x-keys['Esc'].x-keys['Esc'].width,.5)
            for a,b in (('F4','F5'),('F8','F9')):
                self.assertEqual(keys[b].x-keys[a].x-keys[a].width,.5)
            self.assertEqual(keys['`'].y-keys['F1'].y-keys['F1'].height,.5)
            self.assertEqual(keys['Insert'].x-15,.5)
            self.assertTrue(all(k.height==1 for k in keys.values() if k.label not in ('+','NumEnter')))
            if name=='full':self.assertEqual(keys['Num'].x-(keys['PgUp'].x+1),.5)
        keys={k.label:k for k in LAYOUTS['laptop'].keys}
        self.assertEqual(keys['F1'].height,.7)
        self.assertTrue(all(keys[k].height==.5 for k in ('Left','Right','Up','Down')))
        self.assertEqual(keys['Up'].x,keys['Down'].x)
        self.assertEqual(keys['Down'].y,keys['Up'].y+.5)
        self.assertEqual(keys['Left'].y,keys['Right'].y)

    def test_family_scale_remains_physical_and_compact_is_smaller(self):
        from scripts.artwork.illustrations.checks import Pixels
        for family in (('mouse','mouse_compact','mouse_gaming','mouse_wireless'),
                       ('keyboard_60','keyboard_65','keyboard_tkl','keyboard_full','keyboard_builtin')):
            self.assertEqual(len({build_model(key).placement.scale for key in family}),1)
        def size(key):
            l,t,r,b=Pixels(cairo.ImageSurface.create_from_png(str(ASSETS/(key.replace('_','-')+'@2x.png')))).bounds(245)
            return r-l+1,b-t+1
        normal,compact=size('mouse'),size('mouse_compact')
        self.assertAlmostEqual(compact[1]/normal[1],103/120,delta=.02)
        self.assertAlmostEqual(compact[0]/normal[0],55/66,delta=.03)
        self.assertLess(compact[1],normal[1])
        self.assertEqual(sorted(['keyboard_60','keyboard_65','keyboard_tkl','keyboard_full'],key=lambda k:size(k)[0]),
                         ['keyboard_60','keyboard_65','keyboard_tkl','keyboard_full'])

    def test_backlight_parameter_changes_gaps_without_recolouring_key_tops(self):
        from scripts.artwork.illustrations.models.keyboard import build
        from scripts.artwork.illustrations.checks import Pixels,sample
        a,b=build('65',backlight=0),build('65',backlight=.55)
        plain,lit=render(a),render(b)
        self.assertNotEqual(bytes(plain.get_data()),bytes(lit.get_data()))
        for point in a.checks['key_centres']:
            self.assertEqual(sample(Pixels(plain),a,point,1),sample(Pixels(lit),b,point,1))

    def test_runtime_geometry_metadata_matches_committed_opaque_bounds(self):
        import json
        from scripts.artwork.illustrations.checks import Pixels
        data=json.loads((ASSETS/'geometry.json').read_text())
        self.assertEqual(data['version'],1)
        self.assertEqual(set(data['classes']),set(ARTWORK_KEYS))
        for key,row in data['classes'].items():
            pixels=Pixels(cairo.ImageSurface.create_from_png(str(ASSETS/(key.replace('_','-')+'@1x.png'))))
            l,t,r,b=pixels.bounds(245)
            self.assertEqual(row['bounds'],[l/512,t/320,(r+1)/512,(b+1)/320],key)
            family=[value for value in data['classes'].values() if value['family']==row['family']]
            self.assertEqual(row['family_width'],max(v['bounds'][2]-v['bounds'][0] for v in family))
            self.assertEqual(row['family_height'],max(v['bounds'][3]-v['bounds'][1] for v in family))

    def test_neutral_silhouettes_are_different_at_64px(self):
        from scripts.artwork.illustrations.checks import silhouette_differences
        distances=silhouette_differences(ASSETS)
        self.assertEqual(len(distances),10)
        self.assertTrue(all(value>=.12 for value in distances.values()),distances)

    def test_palette_matches_current_qml_tokens(self):
        qml = (ROOT / 'src/logi_center/qml_ui/qml/Theme/Theme.qml').read_text()
        for key, value in TOKENS.items():
            actual = re.search(r'property color ' + key + r':\s*"(#[a-fA-F0-9]{6})"', qml)
            self.assertIsNotNone(actual, key)
            self.assertEqual(actual[1].lower(), value)

    def test_all_committed_pngs_pass_structural_and_quality_checks(self):
        with contextlib.redirect_stdout(io.StringIO()):
            failures = check_all(ASSETS)
        self.assertEqual(failures, [])
        self.assertEqual(len(list(ASSETS.glob('*.png'))), len(ARTWORK_KEYS) * 2)

    def test_primary_class_renders_are_byte_deterministic_in_this_environment(self):
        for key in ('mouse_gaming', 'keyboard_65', 'headset'):
            for density in (1, 2):
                first, second = io.BytesIO(), io.BytesIO()
                render(build_model(key), density).write_to_png(first)
                render(build_model(key), density).write_to_png(second)
                # Different Cairo versions may rasterize an edge differently.
                # Compare fresh renders locally; committed PNGs are checked
                # structurally above on every platform.
                self.assertEqual(hashlib.sha256(first.getvalue()).digest(), hashlib.sha256(second.getvalue()).digest(),
                                 (key, density))

    def test_concave_offset_preserves_notch_and_never_creates_a_spike(self):
        surface = cairo.ImageSurface(cairo.FORMAT_A8, 64, 64)
        ctx = cairo.Context(surface)
        shape = Outline(((8, 8), (56, 8), (56, 20), (24, 20), (24, 44), (56, 44), (56, 56), (8, 56)))
        offset_fill(ctx, shape, 4, lambda: ctx.set_source_rgba(1, 1, 1, 1))
        surface.flush()
        raw, stride = bytes(surface.get_data()), surface.get_stride()
        self.assertEqual(raw[32 * stride + 15], 255)
        self.assertEqual(raw[32 * stride + 22], 0)
        self.assertEqual(raw[32 * stride + 35], 0)
        self.assertEqual(raw[14 * stride + 35], 255)
        self.assertEqual(raw[14 * stride + 9], 0)

    def test_checks_reject_clipping_wrong_size_and_low_key_contrast(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'corrupt.png'
            image = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10)
            image.write_to_png(str(path))
            self.assertTrue(check_png(path, 'mouse', 1)[0])
            path.write_bytes((ASSETS / 'mouse@1x.png').read_bytes()[:33] + b'broken-image-data')
            self.assertIn('PNG decode failed', check_png(path, 'mouse', 1)[0])
            image = cairo.ImageSurface.create_from_png(str(ASSETS / 'mouse@1x.png'))
            ctx = cairo.Context(image)
            ctx.set_source_rgb(1, 1, 1)
            ctx.rectangle(0, 0, 3, 3)
            ctx.fill()
            image.write_to_png(str(path))
            self.assertTrue(any('margin' in error or 'border' in error for error in check_png(path, 'mouse', 1)[0]))
            image = cairo.ImageSurface.create_from_png(str(ASSETS / 'keyboard-65@1x.png'))
            model = build_model('keyboard_65')
            x, y = model.placement.point(*model.checks['key_centres'][0])
            ctx = cairo.Context(image)
            ctx.set_source_rgb(.15, .15, .15)
            ctx.rectangle(x - 2, y - 2, 5, 5)
            ctx.fill()
            image.write_to_png(str(path))
            self.assertTrue(any('lightness' in error for error in check_png(path, 'keyboard_65', 1)[0]))

    def test_user_install_copies_pngs_and_excludes_renderer(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            data = home / 'data'
            previous=data/'logi-center';previous.mkdir(parents=True)
            (previous/'dashboard.py').write_text('# Obsolete bundled GTK module')
            (previous/'user-note.txt').write_text('Keep unrelated files')
            with patch('pathlib.Path.home', return_value=home), patch.dict(os.environ, {'XDG_DATA_HOME': str(data)}), \
                 contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(ROOT / 'install.py'), run_name='__main__')
            runtime = data / 'logi-center'
            self.assertFalse((runtime / 'illustrations').exists())
            for key in ARTWORK_KEYS:
                path = runtime / 'logi_center/assets/devices/generated' / f'{key.replace("_", "-")}@2x.png'
                self.assertTrue(path.is_file(), path)
            self.assertTrue((runtime / 'logi_center/core/devices/device_artwork.py').is_file())
            self.assertTrue((runtime / 'logi_center/core/services/control_service.py').is_file())
            for controller in ('editor','audio','diagnostics'):
                self.assertTrue((runtime / f'logi_center/qml_ui/bridge/{controller}.py').is_file())
            for filename in ('src/logi_center/core/services/battery_service.py','src/logi_center/core/services/battery_presentation.py','src/logi_center/qml_ui/qml/DeviceImage.qml','assets/devices/generated/geometry.json','assets/mice/diagrams/k7-dock.svg'):
                self.assertTrue((runtime / (filename.replace('src/logi_center/', 'logi_center/') if filename.startswith('src/') else 'logi_center/'+filename)).is_file(), filename)
            self.assertTrue((runtime / 'logi_center/qml_ui/qml/Main.qml').is_file())
            for filename in ('dashboard.py','mouse_editor.py','device_ui.py','peripheral_ui.py'):
                self.assertFalse((runtime / (filename.replace('src/logi_center/', 'logi_center/') if filename.startswith('src/') else 'logi_center/'+filename)).exists())
            self.assertEqual((runtime/'user-note.txt').read_text(),'Keep unrelated files')
            self.assertTrue((runtime / 'logi_center/assets/fonts/SOURCES.md').is_file())
            for component in ('DeviceEditor','ControlEditor','K7DockPanel','MouseButtons','KeyboardEditor','AudioPage','AudioEndpoint','CutInput','CutCombo','CutSlider','AppHeader', 'SettingsPage', 'AboutPage', 'BackupsPage', 'DisclosureItem', 'DashboardToolbar'):
                self.assertTrue((runtime / f'logi_center/qml_ui/qml/{component}.qml').is_file())
            self.assertFalse((runtime / 'qml_ui/gtk_backups.py').exists())
            self.assertTrue((runtime / 'logi_center/qml_ui/bridge/backups.py').is_file())
            self.assertTrue((runtime / 'logi_center/qml_ui/bridge/preferences.py').is_file())
            self.assertTrue((runtime / 'logi_center/qml_ui/bridge/backup_simulation.py').is_file())
            self.assertTrue((runtime / 'logi_center/assets/icons/SOURCES.md').is_file())
            for name in ('g502.svg','generic.svg','SOURCES.md'):
                self.assertTrue((runtime / 'logi_center/assets/mice/diagrams' / name).is_file())


if __name__ == '__main__':
    unittest.main()
