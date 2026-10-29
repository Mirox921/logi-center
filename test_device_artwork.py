import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from device_artwork import DeviceArtworkProvider, artwork_key, local_identity, validate_artwork_file
from devices import Device


class DeviceArtworkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.assets = self.root / 'assets'
        generated = self.assets / 'generated'
        generated.mkdir(parents=True)
        (generated / 'mouse.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        (generated / 'touchpad.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        (generated / 'display_audio.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        (generated / 'keyboard_65.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        (generated / 'unknown.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        self.data = self.root / 'data'
        self.config = self.root / 'config'
        self.env = patch.dict(os.environ, {'XDG_DATA_HOME': str(self.data), 'XDG_CONFIG_HOME': str(self.config)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.device = Device('mouse:one', 'Mouse', 'mouse', 'test', 'hid:one',
                             physical='/usb1/1-2', connected=True, vid='1234', pid='5678')
        self.provider = DeviceArtworkProvider(self.assets, exact_models={
            ('1234', '5678', '0100'): self.root / 'exact.svg',
            ('1234', '5678', '0200'): self.root / 'exact2.svg'},
            system_models={('1234', '5678', '0100'): self.root / 'system.svg'})
        for filename in ('exact.svg', 'exact2.svg', 'system.svg'):
            (self.root / filename).write_text('<svg/>')

    def tearDown(self):
        self.temp.cleanup()

    def test_source_precedence_and_revision_match(self):
        self.assertEqual(self.provider.resolve(self.device).source, 'generated')
        self.device.revision = '0100'
        result = self.provider.resolve(self.device)
        self.assertEqual((result.source, result.path), ('exact-model', self.root / 'exact.svg'))
        self.device.revision = 'unknown'
        self.assertEqual(self.provider.resolve(self.device).source, 'generated')
        self.provider.exact_models.clear()
        self.assertEqual(self.provider.resolve(self.device).source, 'generated')
        self.device.revision = '0100'
        self.provider.system_models[('1234', '5678', '0100')] = self.root / 'system.svg'
        self.assertEqual(self.provider.resolve(self.device).source, 'system')

    def test_packaged_g502_svg_routes_by_product_id_without_claiming_revision(self):
        assets=Path(__file__).resolve().parent/'qml_ui/assets/devices'
        provider=DeviceArtworkProvider(assets,data_dir=self.data/'images')
        mouse=Device('g502','Logitech G502 HERO','mouse','ratbagctl','selector',
                     physical='/usb/a',vid='046d',pid='c08b')
        artwork=provider.resolve(mouse)
        self.assertEqual((artwork.source,artwork.path.name),('exact-model','g502-top-wired-qt.svg'))
        # Shipped, reviewed Inkscape SVGs retain editor metadata/styles. The
        # deliberately narrower validator for untrusted uploads is unchanged.
        import xml.etree.ElementTree as ET
        self.assertEqual(ET.parse(artwork.path).getroot().tag,'{http://www.w3.org/2000/svg}svg')
        geometry=provider.describe(artwork)
        self.assertTrue(geometry['valid'])
        self.assertAlmostEqual(geometry['aspect'],1103/2048)
        self.assertAlmostEqual(geometry['bounds'][0],0)
        mouse.connection='wireless'
        artwork=provider.resolve(mouse)
        self.assertEqual(artwork.path.name,'g502-top-wireless-qt.svg')
        self.assertAlmostEqual(provider.describe(artwork)['aspect'],1103/2048)
        mouse.connection='usb'
        self.assertEqual(provider.resolve(mouse).path.name,'g502-top-wired-qt.svg')
        mouse.pid='c098'
        self.assertNotEqual(provider.resolve(mouse).source,'exact-model')
        mouse.pid='c08b'
        custom=self.root/'custom.svg'
        custom.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        provider.set_user_artwork(mouse,custom)
        self.assertEqual(provider.resolve(mouse).source,'user')

    def test_generated_raster_prefers_hidpi_png(self):
        generated=self.assets/'generated'
        (generated/'mouse@1x.png').write_bytes(b'png-1x')
        (generated/'mouse@2x.png').write_bytes(b'png-2x')
        resolved=self.provider.resolve(self.device)
        self.assertEqual(resolved.path,generated/'mouse@2x.png')
        (generated/'mouse@2x.png').unlink()
        self.assertEqual(self.provider.resolve(self.device).path,generated/'mouse@1x.png')

    def test_user_artwork_has_precedence_persists_and_clears(self):
        svg = self.root / 'custom.svg'
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"><path d="M1 1h2"/></svg>')
        installed = self.provider.set_user_artwork(self.device, svg)
        self.assertEqual(self.provider.resolve(self.device).source, 'user')
        document = json.loads(self.provider.preferences_file.read_text())
        self.assertNotIn(self.device.id, document['devices'])
        self.assertNotIn(self.device.physical, installed.name)
        self.assertTrue(self.provider.clear_user_artwork(self.device))
        self.assertEqual(self.provider.resolve(self.device).source, 'generated')

    def test_duplicate_model_devices_get_distinct_local_artwork_identities(self):
        other = Device('mouse:two', 'Mouse', 'mouse', 'test', 'hid:two',
                       physical='/usb1/1-3', connected=True, vid='1234', pid='5678')
        self.assertNotEqual(local_identity(self.device), local_identity(other))

    def test_classifier_uses_device_subtype(self):
        touchpad = Device('tp', 'Touchpad', 'mouse', 'input', '/i2c-ELAN/1', connection='internal')
        touchpad.input_subtype = 'touchpad'
        hdmi = Device('audio', 'HDMI DisplayPort 3 Output', 'audio', 'pulse', 'alsa_output.pci.hdmi-stereo-extra3')
        keyboard = Device('keyboard', 'Keyboard', 'keyboard', 'input', '/usb/1', vid='41e4', pid='2116')
        self.assertEqual(artwork_key(touchpad), 'touchpad')
        self.assertEqual(artwork_key(hdmi), 'display_hdmi')
        self.assertEqual(artwork_key(keyboard), 'keyboard_65')

    def test_artwork_variants_use_metadata_not_display_names(self):
        keyboard = Device('k', 'Unknown 60% TKL full-size Keyboard', 'keyboard', 'input', connection='usb')
        self.assertEqual(artwork_key(keyboard), 'keyboard')
        keyboard.keyboard_layout = 'tkl'
        self.assertEqual(artwork_key(keyboard), 'keyboard_tkl')
        audio = Device('a', 'Gaming USB Headset HDMI', 'audio', 'pactl', connection='usb')
        self.assertEqual(artwork_key(audio), 'audio_unknown')
        audio.audio_subtype = 'headset'
        self.assertEqual(artwork_key(audio), 'headset')
        self.device.mouse_variant = 'compact'
        self.assertEqual(artwork_key(self.device), 'mouse_compact')

    def test_touchpad_needs_positive_evidence_not_vendor_or_bus(self):
        pointer=Device('p','MSNB0001:00 04F3:30AA Mouse','mouse','input',
                       physical='/sys/devices/i2c-3/pointer',vid='04f3',pid='30aa',connection='internal')
        self.assertEqual(artwork_key(pointer),'pointer_generic')
        pointer.udev_properties={'ID_INPUT_TOUCHPAD':'1'}
        self.assertEqual(artwork_key(pointer),'touchpad')
        pointer.udev_properties={};pointer.name='Touchpad'
        self.assertEqual(artwork_key(pointer),'pointer_generic')

    def test_untyped_bluetooth_audio_never_becomes_speaker(self):
        device=Device('bt','Portable Speaker','audio','input',connection='bluetooth')
        self.assertEqual(artwork_key(device),'bluetooth_audio')
        device.audio_subtype='headset'
        self.assertEqual(artwork_key(device),'headset')

    def test_decoder_rejection_falls_through_and_fixed_file_recovers(self):
        self.provider.data_dir.mkdir(parents=True)
        path=self.provider.data_dir/(local_identity(self.device)+'.svg')
        path.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        self.assertEqual(self.provider.resolve(self.device).source,'user')
        self.provider.reject_decoding(path)
        self.assertEqual(self.provider.resolve(self.device).source,'generated')
        path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="2"/></svg>')
        self.assertEqual(self.provider.resolve(self.device).source,'user')

    def test_provenance_hash_changes_when_same_file_changes(self):
        artwork=self.provider.resolve(self.device)
        old=self.provider.describe(artwork)
        artwork.path.write_text('<svg><path/></svg>')
        new=self.provider.describe(artwork)
        self.assertNotEqual(old['sha256'],new['sha256'])
        self.assertEqual(new['file'],artwork.path.name)

    def test_manual_image_slug_path_and_legacy_preference_survive(self):
        from device_artwork import local_identity
        slug = local_identity(self.device)
        self.provider.data_dir.mkdir(parents=True)
        manual = self.provider.data_dir / (slug + '.svg')
        manual.write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect width="2" height="2"/></svg>')
        self.assertEqual(self.provider.data_dir.name, 'device-images')
        self.assertEqual(self.provider.resolve(self.device).path, manual)
        self.assertTrue(self.provider.clear_user_artwork(self.device))
        self.assertEqual(self.provider.resolve(self.device).source, 'generated')
        legacy = self.data / 'logi-center/device-artwork' / (slug + '.svg')
        legacy.parent.mkdir(parents=True)
        legacy.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        self.provider._write_preferences(slug, legacy.name)
        reloaded = DeviceArtworkProvider(self.assets)
        self.assertEqual(reloaded.resolve(self.device).path, legacy)
        reloaded.clear_user_artwork(self.device)
        self.assertTrue(legacy.is_file())
        self.assertEqual(reloaded.resolve(self.device).source, 'generated')

    def test_confirmed_display_route_chooses_connector_not_a_speaker(self):
        from devices import Device
        for route,expected in (('alsa_output.pci-test.hdmi-stereo-extra3','display_hdmi'),
                               ('test.displayport.2','display_dp'),('unknown','audio_unknown')):
            device=Device('display-test','Not a model','audio','pipewire',route)
            self.assertEqual(artwork_key(device),expected)
        device.audio_subtype='display_audio'
        self.assertEqual(artwork_key(device),'display_audio')

    def test_canonical_png_names_win_over_legacy_pack(self):
        from devices import Capability
        self.device.capabilities = [Capability('dpi', 'test', True, True, value=800)]
        generated = self.assets / 'generated'
        (generated / 'mouse_gaming@2x.png').write_bytes(b'legacy')
        (generated / 'mouse-gaming@2x.png').write_bytes(b'current')
        self.assertEqual(self.provider.resolve(self.device).path.name, 'mouse-gaming@2x.png')

    def test_missing_class_asset_uses_neutral_fallback(self):
        (self.assets / 'generated/mouse.svg').unlink()
        (self.assets / 'generated/unknown.svg').unlink()
        fallback = self.assets / 'fallback@2x.png'
        fallback.write_bytes(b'trusted-project-png')
        artwork = self.provider.resolve(self.device)
        self.assertEqual((artwork.source, artwork.path), ('fallback', fallback))

    def test_svg_active_and_excessive_content_rejected(self):
        bad = self.root / 'bad.svg'
        bad.write_text('<svg><script>alert(1)</script></svg>')
        self.assertFalse(validate_artwork_file(bad)[0])
        bad.write_text('<svg>' + '<rect/>' * 5001 + '</svg>')
        self.assertFalse(validate_artwork_file(bad)[0])
        bad.write_text('<svg><path fill="url(#safe) url(https://example.invalid/image)"/></svg>')
        self.assertFalse(validate_artwork_file(bad)[0])

    def test_webp_declared_dimensions_are_bounded_before_decode(self):
        path = self.root / 'image.webp'
        def write_extended(width, height):
            data = b'VP8X' + (10).to_bytes(4, 'little') + b'\x00' * 4 + \
                (width - 1).to_bytes(3, 'little') + (height - 1).to_bytes(3, 'little')
            path.write_bytes(b'RIFF' + (len(data) + 4).to_bytes(4, 'little') + b'WEBP' + data)
        write_extended(100, 100)
        self.assertTrue(validate_artwork_file(path)[0])
        write_extended(100000, 100000)
        self.assertFalse(validate_artwork_file(path)[0])

    def test_invalid_image_does_not_replace_existing_preference(self):
        valid = self.root / 'valid.svg'
        valid.write_text('<svg xmlns="http://www.w3.org/2000/svg"><circle r="4"/></svg>')
        current = self.provider.set_user_artwork(self.device, valid)
        broken = self.root / 'broken.svg'
        broken.write_text('<svg><script/></svg>')
        with self.assertRaises(ValueError):
            self.provider.set_user_artwork(self.device, broken)
        self.assertEqual(self.provider.resolve(self.device).path, current)


if __name__ == '__main__':
    unittest.main()
