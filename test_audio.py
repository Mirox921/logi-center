import json,unittest,tempfile
from pathlib import Path
from array import array
from threading import Event
from unittest.mock import Mock
from audio_pipeline import AudioSession,peak,prepare_preset,preset_lists,processed_route
from execution import Fault

class Audio(unittest.TestCase):
    def test_no_capture_on_construction(self):
        factory=Mock();session=AudioSession(factory);factory.assert_not_called();session.close();factory.assert_not_called()
    def test_peak_nan_and_clipping(self):
        self.assertEqual(peak(array('f',[.1,-.5,float('nan')]).tobytes()),.5)
        self.assertEqual(peak(array('f',[2.]).tobytes()),1.)
    def test_direction_alias_does_not_load_same_name_other_side(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root)
            for kind in ['input','output']:
                (root/kind).mkdir();(root/kind/'voice.json').write_text(json.dumps({kind:{'plugins_order':[]}}))
            alias=prepare_preset('input','voice',root)
            self.assertFalse((root/'output'/(alias+'.json')).exists())
            self.assertEqual(preset_lists(root),{'input':['voice'],'output':['voice']})
    def test_processed_requires_actual_capture_link(self):
        sources=[{'index':1,'name':'mic'},{'index':2,'name':'easyeffects_source'}]
        self.assertIsNone(processed_route(sources,[],'mic'))
        self.assertEqual(processed_route(sources,[{'source':1,'properties':{'application.name':'Easy Effects'}}],'mic'),'easyeffects_source')
    def test_missing_mic(self):
        with self.assertRaises(Fault):processed_route([],[],'missing')
    def test_record_missing_backend_never_creates_sample(self):
        error=Event();session=AudioSession(Mock(side_effect=FileNotFoundError()))
        session.record('mic',None,lambda value:self.fail('must not succeed'),lambda value:error.set(),seconds=.01)
        self.assertTrue(error.wait(2));self.assertFalse(session.clips);session.close()
    def test_cleanup_discards_temporary_files(self):
        session=AudioSession();session.temp=tempfile.TemporaryDirectory();path=Path(session.temp.name)/'test.wav';path.write_bytes(b'')
        session.clips={'original':path};session.stop();self.assertFalse(path.exists())
    def test_synthetic_wave_format_is_real_pcm(self):
        from audio_pipeline import wav_write
        import wave
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'sample.wav';wav_write(path,[array('f',[0.,.5,-.5]).tobytes()])
            with wave.open(str(path)) as clip:
                self.assertEqual((clip.getnchannels(),clip.getsampwidth(),clip.getframerate(),clip.getnframes()),(1,2,16000,3))
