import json,tempfile,time,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock
from logi_center.core.services.drafts import DraftStore
try:
    from PySide6.QtCore import QObject,QCoreApplication
    from logi_center.qml_ui.bridge.audio import AudioController
except ImportError:QCoreApplication=None


class FakeSession:
    def __init__(self):self.calls=[];self.clips={}
    def stop(self):self.clips={}
    def meter(self,source,level,error):self.calls.append(('meter',source));level(.5)
    def record(self,source,processed,done,error,seconds):self.calls.append(('record',source,processed,seconds));self.clips={'original':True};done(set(self.clips))
    def play(self,label,error):self.calls.append(('play',label))


@unittest.skipIf(QCoreApplication is None,'optional PySide6 unavailable')
class AudioBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QCoreApplication.instance() or QCoreApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.pool=ThreadPoolExecutor(max_workers=1)
        self.owner=QObject();self.owner.tr=lambda s:s;self.owner.refresh=Mock();self.owner._preferences_pool=ThreadPoolExecutor(max_workers=1)
        self.owner._editor=Mock(store=DraftStore(Path(self.temp.name)/'logi_center.core.services.drafts.json'))
        self.session=FakeSession();self.commands=[]
        self.default='out'
        self.sinks=[{'name':'out','description':'USB Headphones','index':1,'state':'IDLE','volume':{'left':{'value_percent':'50%'}},'mute':False},
                    {'name':'hdmi','description':'HDMI / DisplayPort 3 Output','index':2,'state':'UNAVAILABLE','volume':{},'mute':False}]
        self.sources=[{'name':'mic','description':'Microphone','index':3,'state':'IDLE','volume':{'left':{'value_percent':'60%'}},'mute':False}]
        self.controller=AudioController(self.owner,self.pool,True,self.run_command,self.session)
        self.controller.sync({'sinks':json.dumps(self.sinks),'sources':json.dumps(self.sources),'default_sink':'out','default_source':'mic'})
    def run_command(self,args,**unused):
        self.commands.append(args)
        if args[1:]==['-f','json','list','sources']:return json.dumps(self.sources)
        if args[1:]==['-f','json','list','source-outputs']:return '[]'
        if args[1:]==['-f','json','list','sinks']:return json.dumps(self.sinks)
        if args[1]=='set-sink-volume':self.sinks[0]['volume']['left']['value_percent']=args[3];return ''
        if args[1]=='set-default-sink':self.default=args[2];return ''
        if args[1]=='get-default-sink':return self.default
        if args[1]=='set-sink-mute':self.sinks[0]['mute']=args[3]=='1';return ''
        raise ValueError('Unexpected fake audio command')
    def wait(self):
        deadline=time.monotonic()+2
        while self.controller.busy and time.monotonic()<deadline:self.app.processEvents();time.sleep(.003)
        self.app.processEvents();self.assertFalse(self.controller.busy)
    def tearDown(self):
        self.controller.shutdown();self.pool.shutdown(wait=True);self.owner._preferences_pool.shutdown(wait=True);self.temp.cleanup()
    def test_edit_does_not_write_and_explicit_apply_readback_confirms(self):
        self.controller.editVolume('sink',42);self.assertEqual(self.commands,[])
        self.controller.applyEndpoint('sink','volume');self.wait()
        self.owner._preferences_pool.submit(lambda:None).result()
        self.assertEqual(self.sinks[0]['volume']['left']['value_percent'],'42%')
        self.assertEqual(self.owner._editor.store.values,{})
        self.assertIn('аудиосистемой',self.controller.message)
    def test_unavailable_hdmi_cannot_be_selected_as_default(self):
        self.controller.selectEndpoint('sink','hdmi');self.controller.applyEndpoint('sink','default')
        self.assertEqual(self.commands,[]);self.assertFalse(self.controller.selectedOutput['available'])
    def test_default_and_mute_changes_are_confirmed_by_audio_server(self):
        self.sinks[1]['state']='IDLE';self.controller.sync({'sinks':json.dumps(self.sinks),'sources':json.dumps(self.sources)})
        self.controller.selectEndpoint('sink','hdmi');self.controller.applyEndpoint('sink','default');self.wait();self.assertEqual(self.default,'hdmi')
        self.controller.selectEndpoint('sink','out');self.controller.applyEndpoint('sink','mute');self.wait();self.assertTrue(self.sinks[0]['mute'])
    def test_recording_is_explicit_and_processed_sample_is_not_fabricated(self):
        self.assertEqual(self.session.calls,[])
        self.controller.startTest('record');self.wait();self.app.processEvents()
        self.assertEqual(self.session.calls,[('record','mic',None,8)])
        self.assertEqual(self.controller.clips,['original'])
        self.controller.stopTest();self.assertEqual(self.controller.clips,[])
    def test_cancelled_preparation_never_starts_capture(self):
        from threading import Event
        entered,release=Event(),Event();original=self.controller.runner
        def delayed(args,**kw):entered.set();release.wait(1);return original(args,**kw)
        self.controller.runner=delayed
        self.controller.startTest('record');self.assertTrue(entered.wait(1));self.controller.stopTest();release.set();self.wait()
        self.assertEqual(self.session.calls,[])
    def test_source_removal_clears_temporary_recording(self):
        self.controller.startTest('record');self.wait()
        self.controller.sync({'sinks':json.dumps(self.sinks),'sources':'[]'})
        self.assertEqual(self.controller.clips,[]);self.assertEqual(self.session.clips,{})
    def test_external_volume_change_marks_draft_conflict(self):
        self.controller.editVolume('sink',40);self.sinks[0]['volume']['left']['value_percent']='70%'
        self.controller.sync({'sinks':json.dumps(self.sinks),'sources':json.dumps(self.sources)})
        self.assertTrue(self.controller.selectedOutput['conflict']);self.controller.applyEndpoint('sink','volume');self.assertEqual(self.commands,[])
    def test_audio_server_error_preserves_draft(self):
        def failure(args,**unused):raise ConnectionError('Audio server unavailable')
        self.controller.runner=failure;self.controller.editVolume('sink',40);self.controller.applyEndpoint('sink','volume');self.wait()
        self.owner._preferences_pool.submit(lambda:None).result()
        self.assertEqual(self.owner._editor.store.values['audio:sink:out:volume']['desired'],40)

