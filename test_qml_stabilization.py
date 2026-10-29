"""Targeted editor regressions. All writes stay inside memory transports."""
import copy,json,unittest
from pathlib import Path
from control_service import ratbag_controls,editor_result_message
from devices import Device,Capability
from operations import Result,State,Plan,Observation
from audio_status import endpoint_labels
from mouse_models import editor_callouts,layout,button_caption
import test_qml_editor as editor_tests
QCoreApplication=editor_tests.QCoreApplication
import test_qml_audio as audio_tests


def ratbag(color):
    return {'active':0,'dpis':[],'rates':[],'button_types':{},'led_modes':{0:['on','off']},'profiles':[
        {'index':0,'rate':1000,'resolutions':[],'buttons':[],'leds':[{'index':0,'depth':'rgb','mode':'on','color':color}]}]}


class PresentationTests(unittest.TestCase):
    def test_missing_rgb_is_unknown_and_black_is_actual_cache_value(self):
        device=Device('test','G502','mouse','ratbagctl','mock')
        for raw,expected in [(None,None),('',None),('invalid',None),('000000',[0,0,0]),('0a141e',[10,20,30])]:
            controls,_=ratbag_controls(device,ratbag(raw))
            field=next(f for f in controls if f.kind=='color')
            self.assertEqual(field.observed,expected)
            self.assertEqual(field.decode(field.encode(expected)),expected)
            self.assertEqual(field.source,'backend_cache')
    def test_result_states_are_not_promoted_to_hardware_confirmation(self):
        from execution import Fault,FaultCode
        cases=[(Result(State.CONFIRMED,'test',1,1,'device'),'применено'),
               (Result(State.SENT,'test',1,1,'backend_cache'),'кэш backend совпал'),
               (Result(State.SENT,'test',1),'не поддерживается'),
               (Result(State.SENT,'test',1,fault=Fault(FaultCode.CONNECTION,'test','Failed read')),'прочитать результат не удалось'),
               (Result(State.MISMATCH,'test',1,2,'device'),'другое значение'),
               (Result(State.ERROR,'test'),'Не удалось применить')]
        from i18n import set_language
        set_language('ru')
        for result,part in cases:self.assertIn(part,editor_result_message(result))
    def test_eleven_g502_targets_fit_without_overlap_at_narrow_and_desktop(self):
        for factor in (.625,300/440):
            positions=list(editor_callouts(11).values())
            for i,(x,y) in enumerate(positions):
                self.assertGreaterEqual(x*480*factor-22,0)
                self.assertLessEqual(x*480*factor+22,480*factor)
                self.assertGreaterEqual(y*440*factor-16,0)
                self.assertLessEqual(y*440*factor+16,440*factor)
                for xx,yy in positions[i+1:]:
                    self.assertTrue(abs(x-xx)*480*factor>=44 or abs(y-yy)*440*factor>=32)
        self.assertEqual(button_caption('G502 HERO',9),'Колесо вправо')
        self.assertEqual(button_caption('G502 HERO',10),'Колесо влево')
        self.assertLess(layout('G502',11)[4][1],layout('G502',11)[3][1])
    def test_logical_audio_routes_keep_descriptions_and_separate_ids(self):
        items=[{'index':1,'description':'Logitech G PRO X Gaming Headset Analog Stereo'},
               {'index':2,'description':'Controller HDMI / DisplayPort 3 Output','properties':{'device.description':'Controller'}},
               {'index':3,'description':'Controller HDMI / DisplayPort 2 Output','properties':{'device.description':'Controller'}},
               {'index':4,'description':'USB Audio'},{'index':5,'description':'USB Audio'}]
        labels=endpoint_labels(items,'sink')
        self.assertIn('G PRO X',labels[0]['label'])
        self.assertTrue(labels[1]['label'].startswith('HDMI / DisplayPort 3'))
        self.assertEqual(len({r['label'] for r in labels}),5)
        self.assertEqual([i['index'] for i in items],[1,2,3,4,5])
        self.assertEqual(endpoint_labels([{'properties':{'node.description':'Digital Microphone'}}],'source')[0]['label'],'Digital Microphone')
    def test_diagrams_are_valid_and_installed_recursively(self):
        import xml.etree.ElementTree as ET
        for name in ('g502','generic'):
            root=ET.parse(Path(__file__).parent/'qml_ui/assets/diagrams'/f'{name}.svg').getroot()
            self.assertEqual(root.attrib['viewBox'],'0 0 480 440')


@unittest.skipIf(QCoreApplication is None,'optional PySide6 unavailable')
class EditorFeedbackTests(unittest.TestCase):
    setUp=editor_tests.EditorTests.setUp
    tearDown=editor_tests.EditorTests.tearDown
    wait=editor_tests.EditorTests.wait
    @classmethod
    def setUpClass(cls):cls.app=QCoreApplication.instance() or QCoreApplication([])
    def test_read_only_boolean_has_no_editable_widget(self):
        self.device.capabilities.append(Capability('motion_sync','test',True,True,False,False,True,'device'))
        self.editor.bind(self.manager,self.device);self.editor.setSection('advanced')
        row=next(r for r in self.editor.fields._rows if r['id']=='test:motion_sync')
        self.assertEqual(row['kind'],'readonly');self.assertFalse(row['writable'])
    def test_unverified_write_retains_draft_and_cache_feedback(self):
        from i18n import LANGUAGE,set_language
        previous=LANGUAGE;set_language('ru')
        self.addCleanup(set_language,previous)
        self.device.capabilities[0].plan=lambda v:Plan(['set','dpi',v],v,lambda run:Observation(run(['get','dpi']),'backend_cache'))
        self.editor.bind(self.manager,self.device);self.editor.edit('test:dpi',850);self.editor.applyGroup();self.wait()
        self.owner._preferences_pool.submit(lambda:None).result()
        self.assertEqual(self.editor.resultState,'sent_unverified')
        self.assertIn('кэш backend совпал',self.editor.message)
        self.assertTrue(self.editor.store.values)
    def test_rgb_cache_readback_remains_a_channel_array(self):
        from control_service import Control
        field=Control('color','Цвет','lighting',[0,0,0],'test/rgb','test','color',source='backend_cache',writable=True)
        self.editor._controls=[field];self.editor._section='lighting'
        self.editor._accept('apply',[(field,[10,20,30],Result(State.SENT,'test','0a141e','0a141e','backend_cache'))],None,self.editor.epoch.token())
        self.assertEqual(self.editor.fields._rows[0]['value'],[10,20,30])
        self.assertTrue(self.editor.fields._rows[0]['cached'])
    def test_disconnect_marks_observation_stale_and_blocks_controls(self):
        self.device.connected=False;self.editor.bind(self.manager,self.device)
        self.assertTrue(all(r['stale'] and not r['writable'] for r in self.editor.fields._rows))


@unittest.skipIf(QCoreApplication is None,'optional PySide6 unavailable')
class AudioFeedbackTests(unittest.TestCase):
    run_command=audio_tests.AudioBridgeTests.run_command
    setUp=audio_tests.AudioBridgeTests.setUp
    tearDown=audio_tests.AudioBridgeTests.tearDown
    @classmethod
    def setUpClass(cls):cls.app=QCoreApplication.instance() or QCoreApplication([])
    def sync(self,default):
        self.controller.sync({'sinks':json.dumps(self.sinks),'sources':json.dumps(self.sources),'default_sink':default,'default_source':'mic'})
    def test_selection_tracks_external_default_but_keeps_manual_preview(self):
        self.sync('hdmi');self.assertEqual(self.controller.selectedOutput['name'],'hdmi')
        self.controller.selectEndpoint('sink','out');self.sync('hdmi')
        self.assertEqual(self.controller.selectedOutput['name'],'out')
        self.assertTrue(next(r for r in self.controller.outputs if r['name']=='hdmi')['default'])
    def test_preset_states_and_missing_backend_cannot_apply(self):
        self.assertEqual(self.controller.presetState,'unavailable')
        for available,presets,expected in [(False,{'input':[],'output':['Test']},'unavailable'),(True,{'input':[],'output':[]},'empty'),(True,{'input':[],'output':['Test']},'ready')]:
            self.controller._accept('prepare',(presets,{},available),None,self.controller.epoch.token())
            self.assertEqual(self.controller.presetState,expected)
            self.controller.loadPreset('output','')
            if not available:self.controller.loadPreset('output','Test')
            self.assertEqual(self.commands,[]);self.assertFalse(self.controller.busy)
        self.controller._accept('prepare',None,RuntimeError('Read failed'),self.controller.epoch.token())
        self.assertEqual(self.controller.presetState,'error')
        self.controller.loadPreset('output','Test');self.assertFalse(self.controller.busy)
