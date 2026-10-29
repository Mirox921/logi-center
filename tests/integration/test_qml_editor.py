"""Editor behavior over fake transports; no real device access."""
import tempfile,time,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock
from logi_center.core.devices.devices import Device, DeviceManager
from logi_center.core.capabilities.model import Capability
from logi_center.core.services.drafts import DraftStore
from logi_center.core.services.operations import Plan,Observation
from logi_center.core.services.control_service import capability_controls,ratbag_controls,keyboard_keys,key_controls,is_k7_ultra,k7_dpi_indicator
try:
    from PySide6.QtCore import QCoreApplication,QObject
    from logi_center.qml_ui.bridge.editor import EditorController
except ImportError:QCoreApplication=None


class Controls(unittest.TestCase):
    def test_unanswered_identity_query_has_actionable_recovery_without_profile_reset(self):
        from logi_center.core.services.control_service import fault_message
        from logi_center.core.services.execution import Fault,FaultCode
        from logi_center.i18n import set_language
        try:
            set_language('ru')
            text=fault_message(Fault(FaultCode.CONNECTION,'mchose','Empty identity reply; profile recovery is never automatic'))
            self.assertIn('Разбуди',text);self.assertIn('Прочитать настройки',text)
            set_language('en')
            self.assertIn('Wake it',fault_message(Fault(FaultCode.CONNECTION,'mchose','Empty identity reply')))
        finally:set_language('ru')

    def test_k7_manual_dpi_indicator_colors_are_one_per_stage(self):
        self.assertEqual([k7_dpi_indicator(i)[0] for i in range(6)],
                         ['Красный','Синий','Зелёный','Жёлтый','Бирюзовый','Фиолетовый'])
        for invalid in (-1,6,True,None,'1'):
            self.assertIsNone(k7_dpi_indicator(invalid))

    def test_k7_sensor_flags_stay_read_only_and_model_match_is_exact(self):
        caps=[Capability(name,'mchose',True,True,False,False,value,'device',
                         limitation='Protocol diagnostic') for name,value in
              [('motion_sync',False),('ripple',True),('angle_snap',False)]]
        device=Device('k7','MCHOSE K7 Ultra','mouse','mchose',vid='3837',pid='1001',capabilities=caps)
        device.backends=['mchose']
        self.assertTrue(is_k7_ultra(device))
        fields=capability_controls(device)
        self.assertEqual(len(fields),3)
        self.assertTrue(all(not field.writable and field.factory is None for field in fields))
        self.assertTrue(all('только для чтения' in field.note for field in fields))
        device.name='MCHOSE L7 Ultra'
        self.assertFalse(is_k7_ultra(device))

    def test_g502_hero_exposes_native_effect_period_only_for_exact_model(self):
        device=Device('g502','Logitech G502 HERO','mouse','ratbagctl','exact-g502')
        data={'active':0,'text':'Model: usb:046d:c08b:0','dpis':[],'rates':[],
              'button_types':{},'led_modes':{0:['on','off','cycle','breathing']},
              'profiles':[{'index':0,'rate':1000,'resolutions':[],'buttons':[],
                           'leds':[{'index':0,'depth':'rgb','mode':'cycle','color':None,
                                    'duration':0,'brightness':0}]}]}
        fields,_=ratbag_controls(device,data)
        cycle=next(f for f in fields if f.id=='ratbagctl:led:0:duration:cycle')
        self.assertEqual((cycle.minimum,cycle.maximum,cycle.step,cycle.observed),(1000,10000,100,0))
        self.assertEqual(cycle.plans(8000)[0].command,
                         ['ratbagctl','exact-g502','profile','0','led','0','set','duration','8000'])
        with self.assertRaises(ValueError):cycle.validate(0)
        other={**data,'text':'Model: usb:046d:c08d:0'}
        self.assertFalse(any(':duration:' in f.id for f in ratbag_controls(device,other)[0]))

    def test_two_backend_controls_do_not_share_a_draft_or_broadcast(self):
        device=Device('one','Mouse','mouse','first',capabilities=[Capability('dpi',b,True,True,True,value=800,minimum=50,maximum=1600,plan=lambda v:Plan(['fake'],v)) for b in ('first','second')])
        controls=capability_controls(device)
        self.assertEqual(len({c.draft_key for c in controls}),2)

    def test_g515_uses_local_data_and_existing_sequential_plans(self):
        from logi_center.core.services.control_service import g515_controls,g515_lighting_plans
        controls=g515_controls([{'key':'brightness_control','value':'50','choices':None}],{'rgb_zone_1':{'ID':'1','color':'0xff3030'}})
        self.assertEqual(len(controls),7)
        self.assertTrue(all(c.source=='local_saved_settings' for c in controls if not c.id.startswith(('g515:period:','g515:intensity:'))))
        plans=g515_lighting_plans(10,[10,20,30]);self.assertEqual(len(plans),2)
        self.assertEqual(plans[0].command,['solaar','config','G515','rgb_control','true'])
        self.assertIn('0x0a141e',plans[1].command[-1])
    def test_only_real_capabilities_get_writable_controls(self):
        device=Device('m','Mouse','mouse','test',capabilities=[
            Capability('dpi','test',True,True,True,True,800,'device',minimum=50,maximum=26000,step=50,plan=lambda v:Plan(['fake'],v)),
            Capability('motion_sync','test',True,True,False,False,True,'device'),
            Capability('dks','test',None)])
        fields=capability_controls(device)
        self.assertEqual([f.id for f in fields],['test:dpi','test:motion_sync'])
        fields[0].validate(850)
        for bad in (True,851,-1,float('nan')):
            with self.assertRaises(ValueError):fields[0].validate(bad)
        self.assertFalse(fields[1].writable)

    def test_ace_layout_and_selected_key_scope(self):
        rows=keyboard_keys();self.assertEqual(len(rows),68);self.assertEqual(len({r['id'] for r in rows}),68)
        caps=[Capability('profiles','mchose-ace68',True,True,value=2),Capability('key_details','mchose-ace68',True,True,value={'50':{'press_base':100,'release_base':200}})]
        for name in ('actuation','rapid_trigger','rt_press','rt_release','press_dead_zone','release_dead_zone'):
            caps.append(Capability(name,'mchose-ace68',True,True,True,True,{'50':0 if name=='rapid_trigger' else .3},'device',plan=lambda v:Plan(['fake'],v)))
        fields=key_controls(Device('ace','Ace','keyboard','mchose-ace68',capabilities=caps),'50')
        self.assertEqual(len(fields),6)
        self.assertTrue(all(':profile:2:key:50:' in f.draft_key for f in fields))
        self.assertEqual(next(f for f in fields if f.capability=='rt_release').step,.005)

    def test_ratbag_unknown_action_types_are_read_only_and_rgb_owner_wins(self):
        device=Device('mouse','Mouse','mouse','ratbagctl','nick',capabilities=[Capability('lighting','openrgb',True,True,True)])
        data={'active':0,'dpis':[400,800],'rates':[500,1000],'profiles':[{'index':0,'rate':1000,'resolutions':[{'index':0,'dpi':800,'active':True,'disabled':False}],
            'buttons':[{'index':0,'action':'button 1','macro':False}],'leds':[{'index':0,'mode':'on','depth':'rgb','color':'ffffff'}]}], 'button_types':{},'led_modes':{0:['on','off']}}
        fields,buttons=ratbag_controls(device,data)
        self.assertFalse(any(f.group=='lighting' for f in fields));self.assertEqual(buttons[0]['actions'],[])


@unittest.skipIf(QCoreApplication is None,'optional PySide6 unavailable')
class EditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QCoreApplication.instance() or QCoreApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.owner=QObject();self.owner.tr=lambda text:text
        self.owner._preferences_pool=ThreadPoolExecutor(max_workers=1);self.pool=ThreadPoolExecutor(max_workers=1)
        self.owner.refresh=Mock();self.values={'dpi':800,'debounce':4};self.calls=[]
        def runner(args,**unused):
            self.calls.append(args)
            if args[0]=='set':self.values[args[1]]=args[2];return ''
            return self.values[args[1]]
        self.editor=EditorController(self.owner,self.pool,store=DraftStore(Path(self.temp.name)/'logi_center.core.services.drafts.json'),runner=runner)
        self.device=Device('unit','Mouse','mouse','test','target',physical='/test/one',capabilities=[])
        for name,low,high,step in (('dpi',50,26000,50),('debounce',0,255,1)):
            self.device.capabilities.append(Capability(name,'test',True,True,True,True,self.values[name],'device',minimum=low,maximum=high,step=step,
                plan=lambda v,n=name:Plan(['set',n,v],v,lambda run,n=n:Observation(run(['get',n]),'device'))))
        self.manager=DeviceManager();self.manager.devices=[self.device];self.editor.bind(self.manager,self.device)
    def wait(self):
        deadline=time.monotonic()+3
        while self.editor.busy and time.monotonic()<deadline:self.app.processEvents();time.sleep(.005)
        self.app.processEvents();self.assertFalse(self.editor.busy)
    def tearDown(self):
        self.editor.shutdown();self.pool.shutdown(wait=True);self.owner._preferences_pool.shutdown(wait=True);self.temp.cleanup()
    def test_edit_is_draft_apply_uses_readback_and_discards_only_confirmed(self):
        self.editor.edit('test:dpi',850);self.assertEqual(self.calls,[])
        self.editor.applyGroup();self.wait()
        self.owner._preferences_pool.submit(lambda:None).result()
        self.assertEqual(self.values['dpi'],850);self.assertEqual(self.editor.resultState,'confirmed')
        self.assertNotIn('device:unit:dpi',self.editor.store.values)
    def test_draft_survives_device_switch_and_telemetry_without_model_reset(self):
        resets=[];self.editor.fields.modelReset.connect(lambda:resets.append(True))
        self.editor.edit('test:dpi',900);self.editor.bind(self.manager,None);self.editor.bind(self.manager,self.device)
        self.assertEqual(next(r['value'] for r in self.editor.fields._rows if r['id']=='test:dpi'),900)
        self.assertEqual(resets,[])
    def test_k7_indicator_and_dock_sections_never_start_writes(self):
        self.device.name='MCHOSE K7 Ultra';self.device.vid='3837';self.device.pid='1001'
        self.device.connected=True
        self.device.backend='mchose';self.device.backends=['mchose']
        self.device.capabilities=[Capability('charging','mchose',True,True,False,False,False,'device'),
                                  Capability('profiles','mchose',True,True,False,False,0,'device'),
                                  Capability('motion_sync','mchose',True,True,False,False,False,'device')]
        self.editor.bind(self.manager,self.device)
        self.assertTrue({'indicators','dock'} <= {s['id'] for s in self.editor.sections})
        self.assertIn('Профиль 1',self.editor.k7Status['profile'])
        self.assertEqual(self.editor.k7Status['charging'],'Не заряжается')
        for section in ('indicators','dock'):
            self.editor.setSection(section)
            self.assertEqual(self.editor.fields._rows,[])
            self.assertEqual(self.editor.dirtyCount,0)
        self.assertEqual(self.calls,[])
    def test_k7_dpi_stage_shows_manual_color_without_changing_hardware(self):
        self.device.name='MCHOSE K7 Ultra';self.device.vid='3837';self.device.pid='1001'
        self.device.connected=True;self.device.backend='mchose';self.device.backends=['mchose']
        self.device.capabilities=[Capability('stage','mchose',True,True,True,True,0,'device',
            choices=list(range(6)),plan=lambda value:Plan(['fake'],value))]
        self.editor.bind(self.manager,self.device)
        self.assertEqual(self.editor.k7Status['stageNumber'],1)
        self.assertEqual(self.editor.k7Status['stageName'],'Красный')
        row=next(r for r in self.editor.fields._rows if r['id']=='mchose:stage')
        self.assertEqual(row['observed'],'1')
        self.assertEqual(row['choiceLabels'],['1 · Красный','2 · Синий','3 · Зелёный',
                                               '4 · Жёлтый','5 · Бирюзовый','6 · Фиолетовый'])
        self.editor.edit('mchose:stage',4)
        row=next(r for r in self.editor.fields._rows if r['id']=='mchose:stage')
        self.assertEqual(row['indicatorColor'],k7_dpi_indicator(4)[1])
        self.assertEqual(self.editor.k7Status['stageNumber'],1)  # observed, not the draft
        self.assertEqual(self.calls,[])
    def test_mchose_dpi_drafts_stay_with_their_profile_and_stage(self):
        self.device.name='MCHOSE K7 Ultra';self.device.vid='3837';self.device.pid='1001'
        self.device.connected=True;self.device.backend='mchose';self.device.backends=['mchose']
        profile=Capability('profiles','mchose',True,True,value=0,source='device')
        stage=Capability('stage','mchose',True,True,value=0,source='device')
        dpi=Capability('dpi','mchose',True,True,True,True,400,'device',minimum=50,maximum=42000,
                       step=50,plan=lambda value:Plan(['fake'],value))
        self.device.capabilities=[profile,stage,dpi]
        self.editor.bind(self.manager,self.device);self.editor.edit('mchose:dpi',450)
        stage.value=1;dpi.value=800;self.editor._build()
        row=next(r for r in self.editor.fields._rows if r['id']=='mchose:dpi')
        self.assertEqual(row['value'],800);self.assertFalse(row['dirty'])
        self.editor.edit('mchose:dpi',850)
        profile.value=1;dpi.value=800;self.editor._build()
        self.assertEqual(next(r['value'] for r in self.editor.fields._rows if r['id']=='mchose:dpi'),800)
        profile.value=0;stage.value=0;dpi.value=400;self.editor._build()
        self.assertEqual(next(r['value'] for r in self.editor.fields._rows if r['id']=='mchose:dpi'),450)
        self.assertEqual(self.calls,[])
    def prepare_k7_observer(self):
        self.device.name='MCHOSE K7 Ultra';self.device.vid='3837';self.device.pid='1001'
        self.device.connected=True;self.device.backend='mchose';self.device.backends=['mchose']
        self.device.targets={'mchose':['target']}
        self.device.capabilities=[Capability(name,'mchose',True,True,False,False,value,'device') for name,value in
                                  [('profiles',0),('stage',0),('dpi',400)]]
        self.editor.bind(self.manager,self.device)

    def test_k7_dock_composes_drafts_into_one_rgb_write_and_targeted_read(self):
        import json
        from logi_center.adapters.mchose.mchose_adapter import dock_capability,dock_values,prepare_dock_record
        self.prepare_k7_observer();record=bytes([1,1,0,100,0,3,1,0,0,255,0,0,255,0,0]);calls=[]
        self.device.capabilities.append(dock_capability('target',{'dock_lighting':dock_values(record),'dock_rgb_record':list(record)}))
        self.editor._build();self.editor.setSection('dock')
        def runner(args,**unused):
            nonlocal record
            calls.append(args)
            if args[2]=='set':
                payload=json.loads(args[-1]);self.assertEqual(payload['expected_record'],list(record))
                record=prepare_dock_record(record,payload['changes']);return ''
            state={'dock_lighting':dock_values(record),'dock_rgb_record':list(record)}
            if args[2]=='read':state.update(profiles=0,stage=0,raw=[0]*63)
            return json.dumps(state)
        self.editor.runner=runner
        self.editor.edit('mchose:dock:mode','static');self.editor.edit('mchose:dock:color',[120,30,10])
        self.editor.edit('mchose:dock:brightness',80)
        self.assertEqual(calls,[])
        self.editor.applyGroup();self.wait()
        writes=[args for args in calls if args[2]=='set']
        self.assertEqual(len(writes),1)
        self.assertEqual(json.loads(writes[0][-1])['changes'],{'mode':'static','brightness':80,'color':[120,30,10]})
        self.assertEqual(self.editor.dockState['color'],[120,30,10])
        self.assertEqual(self.editor.dirtyCount,0);self.assertEqual(self.editor.resultState,'confirmed')
        self.owner.refresh.assert_not_called()
        self.editor.edit('mchose:dock:mode','wave')
        visible={row['id'].split(':')[-1] for row in self.editor.fields._rows}
        self.assertEqual(visible,{'enabled','mode','brightness','direction'})
        self.editor.discardGroup();self.assertEqual(self.editor.dockState['mode'],'static')

    def test_k7_dock_off_and_stale_record_keep_effect_and_drafts(self):
        from logi_center.adapters.mchose.mchose_adapter import dock_capability,dock_values
        from logi_center.core.services.execution import Fault,FaultCode
        self.prepare_k7_observer();record=bytes([1,1,0,100,0,3,1,0,0,255,0,0,255,0,0])
        self.device.capabilities.append(dock_capability('target',{'dock_lighting':dock_values(record),'dock_rgb_record':list(record)}))
        self.editor._build();self.editor.setSection('dock')
        self.editor.edit('mchose:dock:enabled',False)
        self.assertEqual(self.editor.dockState['mode'],'battery')
        self.assertEqual({row['id'].split(':')[-1] for row in self.editor.fields._rows},{'enabled','mode'})
        def stale(args,**unused):raise Fault(FaultCode.CONFIG,'mchose','Dock lighting changed since the command was prepared')
        self.editor.runner=stale;self.editor.applyGroup();self.wait()
        self.assertTrue(self.editor._pending);self.assertIn('черновик сохранён',self.editor.message)
        self.editor.discardGroup();self.assertTrue(self.editor.dockState['enabled'])

    def test_unscoped_mchose_draft_is_visible_but_never_reassigned(self):
        self.prepare_k7_observer()
        self.editor.store.edit('device:unit:dpi',400,450)
        self.editor._build()
        row=next(r for r in self.editor.fields._rows if r['id']=='mchose:dpi')
        self.assertEqual(row['legacyDraft'],'450')
        self.assertEqual(row['value'],400);self.assertFalse(row['dirty'])
        self.assertEqual(self.editor.store.values['device:unit:dpi']['desired'],450)

    def test_queued_mchose_write_keeps_its_original_profile_guard(self):
        import json
        from threading import Event
        from logi_center.adapters.mchose.mchose_adapter import setting_plan,update_observed
        from logi_center.core.services.execution import Fault,FaultCode
        self.prepare_k7_observer()
        dpi=next(c for c in self.device.capabilities if c.name=='dpi')
        dpi.writable=True;dpi.minimum=50;dpi.maximum=42000;dpi.step=50
        dpi.plan=lambda value:setting_plan('target','dpi',value,0,0)
        self.editor._build();self.editor.edit('mchose:dpi',450)
        blocker=Event();self.pool.submit(lambda:blocker.wait(2))
        calls=[]
        def runner(args,**unused):
            calls.append(args)
            raise Fault(FaultCode.CONFIG,'mchose','Profile or DPI stage changed since the command was prepared')
        self.editor.runner=runner;self.editor.applyGroup()
        update_observed(self.device,{'profiles':1,'stage':0,'dpi':800})
        blocker.set();self.wait()
        self.assertEqual(len(calls),1)
        self.assertEqual(json.loads(calls[0][-1]),{'value':450,'expected_profile':0,'expected_stage':0})
        self.assertIn('черновик сохранён',self.editor.message)
        self.assertTrue(self.editor._pending)

    def finish_state_read(self):
        self.pool.submit(lambda:None).result(timeout=2)
        self.app.processEvents()
        self.assertFalse(self.editor._state_busy)

    def test_k7_passive_state_read_updates_dpi_color_without_blocking_or_resets(self):
        import json
        self.prepare_k7_observer();commands=[];resets=[]
        self.editor.fields.modelReset.connect(lambda:resets.append(True))
        self.editor.runner=lambda args:commands.append(args) or json.dumps({'profiles':1,'stage':2,'dpi':1600,'raw':[0]*63})
        self.editor.observing=True;self.editor._state_timer.stop();self.editor._poll_state()
        self.assertFalse(self.editor.busy)
        self.finish_state_read()
        self.assertEqual(commands,[['logi-sdk','mchose','read','target']])
        self.assertEqual(self.editor.k7Status['stageNumber'],3)
        self.assertEqual(self.editor.k7Status['stageName'],'Зелёный')
        self.assertEqual(self.editor.k7Status['profile'],'Профиль 2')
        self.assertEqual(resets,[])
        self.assertEqual(self.editor._state_timer.interval(),5000)
        self.editor.observing=False;self.assertFalse(self.editor._state_timer.isActive())

    def test_k7_passive_read_cannot_overwrite_a_new_operation_or_disconnected_device(self):
        import json
        from threading import Event
        self.prepare_k7_observer();started=Event();release=Event()
        def runner(args):
            started.set();release.wait(2)
            return json.dumps({'profiles':1,'stage':2,'dpi':1600,'raw':[0]*63})
        self.editor.runner=runner;self.editor.observing=True;self.editor._state_timer.stop();self.editor._poll_state()
        self.assertTrue(started.wait(1))
        self.editor.bind(self.manager,None);release.set();self.finish_state_read()
        self.assertEqual(self.device.capabilities[1].value,0)
        self.assertFalse(self.editor._state_timer.isActive())
        self.editor.bind(self.manager,self.device)
        token=self.editor._state_epoch.token();self.editor._state_epoch.invalidate();self.editor._busy=True
        self.editor._accept_state({'profiles':2,'stage':4},None,token)
        self.assertTrue(self.editor.busy)
        self.assertEqual(self.editor.k7Status['stageNumber'],1)
        self.editor._busy=False

    def test_k7_observer_error_keeps_values_and_backs_off_simulation_never_polls(self):
        from logi_center.core.services.execution import Fault,FaultCode
        self.prepare_k7_observer()
        def failed(args):raise Fault(FaultCode.PERMISSION,'mchose','Denied')
        self.editor.runner=failed;self.editor.observing=True;self.editor._state_timer.stop();self.editor._poll_state()
        self.finish_state_read()
        self.assertTrue(self.editor.liveReadError)
        self.assertEqual(self.editor.k7Status['stageNumber'],1)
        self.assertTrue(all(row['stale'] for row in self.editor.fields._rows))
        self.assertEqual(self.editor._state_timer.interval(),15000)
        self.editor.runner=lambda args:'{"raw":[]}'
        self.editor._state_timer.stop();self.editor._poll_state();self.finish_state_read()
        self.assertTrue(self.editor.liveReadError)
        self.assertEqual(self.editor.k7Status['stageNumber'],1)
        self.editor.observing=False;self.editor.simulation=True;self.editor.runner=Mock()
        self.editor.observing=True;self.editor._poll_state()
        self.editor.runner.assert_not_called();self.assertFalse(self.editor._state_timer.isActive())
    def test_k7_disconnected_link_does_not_show_stale_charge_or_profile(self):
        self.device.name='MCHOSE K7 Ultra';self.device.vid='3837';self.device.pid='1001'
        self.device.backend='mchose';self.device.backends=['mchose'];self.device.connected=False
        self.device.capabilities=[Capability('charging','mchose',True,True,False,False,True,'device'),
                                  Capability('profiles','mchose',True,True,False,False,2,'device')]
        self.editor.bind(self.manager,self.device)
        self.assertEqual(self.editor.k7Status,{'link':'Мышь не подключена','charging':'Нет данных',
            'profile':'Нет данных','stageNumber':0,'stageColor':'','stageName':''})
    def test_k7_charge_uses_dashboard_evidence_and_telemetry_signal(self):
        from datetime import datetime,timezone,timedelta
        from logi_center.core.services.battery_presentation import battery_display
        self.device.name='MCHOSE K7 Ultra';self.device.vid='3837';self.device.pid='1001'
        self.device.backend='mchose';self.device.backends=['mchose'];self.device.connected=True
        old=Capability('charging','mchose',True,True,False,False,False,'device')
        old.observed_at=(datetime.now(timezone.utc)-timedelta(seconds=30)).isoformat()
        fresh=Capability('charging','kernel-battery',True,True,False,False,True,'kernel')
        self.device.capabilities=[old,fresh]
        self.editor.bind(self.manager,self.device)
        self.assertEqual(battery_display(self.device)['charging'],True)
        self.assertEqual(self.editor.k7Status['charging'],'Заряжается')
        notifications=[];resets=[]
        self.editor.changed.connect(lambda:notifications.append(True))
        self.editor.fields.modelReset.connect(lambda:resets.append(True))
        fresh.value=False
        self.editor.telemetryUpdated()
        self.assertEqual(notifications,[True])
        self.assertEqual(resets,[])
        self.assertEqual(self.editor.k7Status['charging'],'Не заряжается')
        fresh.observed_at=(datetime.now(timezone.utc)-timedelta(seconds=120)).isoformat()
        old.observed_at=fresh.observed_at
        self.assertEqual(self.editor.k7Status['charging'],'Нет данных')
    def test_k7_explicit_refresh_reads_profile_without_discards_or_writes(self):
        import json
        self.device.name='RealTek MCHOSE K7 Ultra';self.device.vid='3837';self.device.pid='1001'
        self.device.connected=True
        self.device.backend='mchose';self.device.backends=['mchose'];self.device.targets={'mchose':['target']}
        self.device.capabilities=[Capability('profiles','mchose',True,True,False,False,0,'device'),
                                  Capability('charging','mchose',True,True,False,False,False,'device'),
                                  Capability('motion_sync','mchose',True,True,False,False,False,'device')]
        commands=[]
        self.editor.runner=lambda args:commands.append(args) or json.dumps({
            'profiles':1,'stage':0,'charging':True,'motion_sync':True,'raw':[0]*63})
        self.editor.bind(self.manager,self.device)
        self.editor.reload();self.wait()
        self.assertEqual(commands,[['logi-sdk','mchose','read','target']])
        self.assertEqual(self.editor.k7Status['profile'],'Профиль 2')
        self.assertEqual(self.editor.k7Status['charging'],'Заряжается')
        self.assertFalse(next(f for f in self.editor._controls if f.capability=='motion_sync').writable)
    def test_k7_late_read_is_ignored_after_disconnect(self):
        import json
        from threading import Event
        self.device.name='MCHOSE K7 Ultra';self.device.vid='3837';self.device.pid='1001'
        self.device.backend='mchose';self.device.backends=['mchose'];self.device.targets={'mchose':['target']}
        self.device.capabilities=[Capability('profiles','mchose',True,True,False,False,0,'device')]
        started=Event();release=Event()
        def delayed_read(args):
            self.assertEqual(args,['logi-sdk','mchose','read','target'])
            started.set();release.wait(2)
            return json.dumps({'profiles':2,'raw':[0]*63})
        self.editor.runner=delayed_read;self.editor.bind(self.manager,self.device)
        self.editor.reload();self.assertTrue(started.wait(1))
        self.editor.bind(self.manager,None);release.set()
        self.pool.submit(lambda:None).result(timeout=2)
        self.app.processEvents()
        self.assertEqual(self.device.capabilities[0].value,0)
    def test_g502_editor_uses_packaged_svg_and_existing_button_anchors(self):
        from logi_center.core.devices.device_artwork import DeviceArtworkProvider
        from logi_center.core.devices.mouse_models import G502
        self.owner._artwork=DeviceArtworkProvider(Path(__file__).resolve().parents[2]/'assets/devices',
                                                  allow_user_artwork=False)
        self.device.name='Logitech G502 HERO';self.device.vid='046d';self.device.pid='c08b'
        self.editor.bind(self.manager,self.device)
        self.editor._buttons=[{'index':i} for i in range(11)]
        self.assertEqual(self.editor.buttonDiagram,(Path(__file__).resolve().parents[2]/'assets/mice/g502-top-wired-qt.svg').as_uri())
        self.assertEqual((self.editor.buttons[4]['x'],self.editor.buttons[4]['y']),G502[4])
        self.device.pid='c098';self.editor.bind(self.manager,self.device)
        self.assertEqual(self.editor.buttonDiagram,(Path(__file__).resolve().parents[2]/'assets/mice/diagrams/g502.svg').as_uri())
    def test_rebind_blocks_prepared_write(self):
        self.editor.edit('test:dpi',900)
        self.device.targets={'test':['replacement']}
        self.editor.applyGroup();self.wait()
        self.assertEqual(self.calls,[]);self.assertEqual(self.editor.resultState,'disconnected')
        self.assertIn('device:unit:dpi',self.editor._pending)
    def test_conflicting_draft_cannot_write(self):
        self.editor.edit('test:dpi',900);self.device.capabilities[0].value=1000;self.editor.bind(self.manager,self.device)
        self.editor.applyGroup();self.assertEqual(self.calls,[]);self.assertIn('конфликтует',self.editor.message)
    def test_reset_cannot_be_overwritten_by_queued_persistence(self):
        self.editor.edit('test:dpi',900);self.editor.flush();self.editor.discardGroup()
        self.owner._preferences_pool.submit(lambda:None).result()
        self.assertEqual(self.editor.store.values,{})
    def test_unverified_value_keeps_draft(self):
        self.device.capabilities[0].plan=lambda v:Plan(['set','dpi',v],v,lambda run:Observation(v,'backend_cache'))
        self.editor.bind(self.manager,self.device);self.editor.edit('test:dpi',900);self.editor.applyGroup();self.wait()
        self.owner._preferences_pool.submit(lambda:None).result()
        self.assertEqual(self.editor.resultState,'sent_unverified')
        self.assertEqual(self.editor.store.values['device:unit:dpi']['desired'],900)
        self.editor.edit('test:dpi',800);self.editor.applyGroup();self.wait()
        self.owner._preferences_pool.submit(lambda:None).result()
        self.assertEqual(self.values['dpi'],800)
        self.assertEqual(self.editor.store.values['device:unit:dpi']['base'],900)

    def test_partial_apply_keeps_failed_draft_and_reports_previous_success(self):
        from logi_center.core.services.execution import Fault,FaultCode
        self.values['sleep']=30
        self.device.capabilities.append(Capability('sleep','test',True,True,True,True,30,'device',minimum=0,maximum=255,
            plan=lambda value:Plan(['set','sleep',value],value)))
        original=self.editor.runner
        def fail(args,**kw):
            if args[:2]==['set','sleep']:raise Fault(FaultCode.DISCONNECTED,'test','Disconnected')
            return original(args,**kw)
        self.editor.runner=fail;self.editor.bind(self.manager,self.device);self.editor.setSection('advanced')
        self.editor.edit('test:debounce',5);self.editor.edit('test:sleep',31);self.editor.applyGroup();self.wait()
        self.owner._preferences_pool.submit(lambda:None).result()
        self.assertEqual(self.values['debounce'],5)
        self.assertNotIn('device:unit:debounce',self.editor.store.values)
        self.assertIn('device:unit:sleep',self.editor.store.values)
        self.assertIn('Некоторые изменения применены',self.editor.message)

    def test_macro_reset_preserves_drafts_of_other_buttons(self):
        self.device.targets['ratbagctl']=['fake-ratbag']
        self.editor._ratbag={'active':0,'dpis':[],'rates':[],'button_types':{0:[4],1:[4]},'led_modes':{},'profiles':[{'index':0,'resolutions':[],'rate':None,'leds':[],
            'buttons':[{'index':i,'action':'button 1','macro':False} for i in range(2)]}]}
        self.editor._build();self.editor.selectButton(0);self.editor.addPause(100);self.editor.selectButton(1);self.editor.addPause(200);self.editor.resetMacro()
        self.owner._preferences_pool.submit(lambda:None).result()
        state=self.editor.store.values[self.editor._macro_key()]['desired']
        self.assertEqual(state['tokens'],{'0':['t100']})

    def test_mchose_sdk_plan_reuses_existing_adapter_and_guard(self):
        import json
        from logi_center.adapters.mchose.mchose_adapter import setting_plan
        self.device.backend='mchose';self.device.backends=['mchose'];self.device.targets={'mchose':['target']}
        self.device.capabilities=[Capability('dpi','mchose',True,True,True,True,800,'device',minimum=50,maximum=26000,step=50,plan=lambda value:setting_plan('target','dpi',value))]
        def sdk(args,**unused):
            self.assertEqual(args[:2],['logi-sdk','mchose'])
            if args[2]=='set':self.values['dpi']=json.loads(args[5]);return ''
            return json.dumps({'dpi':self.values['dpi']})
        self.editor.runner=sdk;self.editor.bind(self.manager,self.device);self.editor.edit('mchose:dpi',850.0);self.editor.applyGroup();self.wait()
        self.assertEqual(self.values['dpi'],850);self.assertIs(type(self.values['dpi']),int)
        self.assertEqual(self.editor.resultState,'confirmed')

    def test_native_right_modifier_keeps_its_side(self):
        from PySide6.QtCore import QEvent,Qt
        from PySide6.QtGui import QKeyEvent
        event=QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_Control,Qt.KeyboardModifier.NoModifier,0,0xffe4,0,'')
        self.assertEqual(self.editor._event_name(event),'Control_R')

    def test_g502_cycle_to_static_sets_mode_before_color_and_keeps_unverified_draft(self):
        import copy
        device=Device('g502','Logitech G502 HERO','mouse','ratbagctl','exact-g502',physical='/test/g502',connected=True)
        state={'active':0,'dpis':[],'rates':[],'button_types':{},'led_modes':{0:['on','off','cycle','breathing']},
               'profiles':[{'index':0,'rate':1000,'resolutions':[],'buttons':[],
                            'leds':[{'index':0,'depth':'rgb','mode':'cycle','color':None},
                                    {'index':1,'depth':'rgb','mode':'cycle','color':None}]}]}
        state['led_modes'][1]=list(state['led_modes'][0])
        commands=[]
        def runner(args,**unused):
            commands.append(args)
            if args[-3:]==['profile','active','get']:return '0'
            led_index=int(args[args.index('led')+1])
            led=state['profiles'][0]['leds'][led_index]
            if args[-1]=='get':
                return 'LED: '+str(led_index)+', depth: rgb, mode: '+led['mode']+(', color: '+led['color'] if led['color'] else '')
            if 'set' in args:
                index=args.index('set');led[args[index+1]]=args[index+2]
                return ''
            raise AssertionError(args)
        self.manager.devices=[device];self.editor.runner=runner
        reads=[]
        def read(target):reads.append(target);return copy.deepcopy(state)
        self.editor.reader=read
        self.editor.bind(self.manager,device);self.wait();self.editor.setSection('lighting')
        self.editor.edit('ratbagctl:led:0:mode','on')
        self.editor.applyGroup()
        self.assertEqual(commands,[])
        self.assertIn('Выбери цвет',self.editor.message)
        self.editor.edit('ratbagctl:led:0:color',[34.5,102.0,170.0])
        self.assertIsNone(self.editor._desired(self.editor._field('ratbagctl:led:0:color'))[0])
        self.editor.edit('ratbagctl:led:0:color',[34.0,102.0,170.0])
        self.assertEqual(self.editor._desired(self.editor._field('ratbagctl:led:0:color'))[0],[34,102,170])
        color_row=next(row for row in self.editor.fields._rows if row['id']=='ratbagctl:led:0:color')
        self.assertEqual(color_row['value'],[34,102,170])
        self.assertTrue(color_row['dirty'])
        self.editor.applyGroup();self.wait()
        self.owner._preferences_pool.submit(lambda:None).result()
        writes=[args for args in commands if 'set' in args]
        self.assertEqual([args[args.index('set')+1:] for args in writes],[['mode','on'],['color','2266aa']])
        self.assertEqual({args[1] for args in writes},{'exact-g502'})
        self.assertEqual(self.editor.resultState,'sent_unverified')
        self.assertEqual(self.editor._ratbag['profiles'][0]['leds'][0]['color'],'2266aa')
        self.assertEqual(reads,['exact-g502'])  # No full mouse reload after the two LED writes.
        self.assertIn('mouse:exact-g502:profile:0/led:0:color',self.editor.store.values)
        commands.clear()
        self.editor.edit('ratbagctl:led:1:mode','on')
        self.editor.edit('ratbagctl:led:1:color',[0xaa,0x44,0x22])
        self.editor.applyGroup();self.wait()
        self.assertEqual([args[args.index('led')+1] for args in commands if 'set' in args],['1','1'])
        self.assertEqual(state['profiles'][0]['leds'][0]['color'],'2266aa')
        self.assertEqual(state['profiles'][0]['leds'][1]['color'],'aa4422')

    def test_external_profile_switch_blocks_rgb_write_and_refreshes_editor(self):
        import copy
        device=Device('g502','Logitech G502 HERO','mouse','ratbagctl','exact-g502',physical='/test/g502',connected=True)
        state={'active':0,'dpis':[],'rates':[],'button_types':{},'led_modes':{0:['on','off']},
               'profiles':[{'index':index,'rate':1000,'resolutions':[],'buttons':[],
                            'leds':[{'index':0,'depth':'rgb','mode':'on','color':color}]}
                           for index,color in ((0,'eb4d4b'),(1,'deddda'))]}
        commands=[]
        def runner(args,**unused):
            commands.append(args)
            if args[-3:]==['profile','active','get']:return str(state['active'])
            raise AssertionError('Unexpected hardware command: '+repr(args))
        self.manager.devices=[device];self.editor.runner=runner
        self.editor.reader=lambda target:copy.deepcopy(state)
        self.editor.bind(self.manager,device);self.wait();self.editor.setSection('lighting')
        self.editor.edit('ratbagctl:led:0:color',[255,255,255])
        state['active']=1  # The physical profile button changed after the editor read.
        self.editor.applyGroup();self.wait()
        self.owner._preferences_pool.submit(lambda:None).result()
        self.assertFalse(any('set' in args for args in commands))
        self.assertEqual(self.editor._ratbag['active'],1)
        self.assertEqual(self.editor.resultState,'stale')
        self.assertIn('черновик сохранён',self.editor.message)
        self.assertIn('mouse:exact-g502:profile:0/led:0:color',self.editor.store.values)

    def test_g502_cycle_stages_period_brightness_then_firmware_mode(self):
        import copy
        device=Device('g502','Logitech G502 HERO','mouse','ratbagctl','exact-g502',physical='/test/g502',connected=True)
        state={'active':0,'text':'Model: usb:046d:c08b:0','dpis':[],'rates':[],
               'button_types':{},'led_modes':{0:['on','off','cycle','breathing']},
               'profiles':[{'index':0,'rate':1000,'resolutions':[],'buttons':[],
                            'leds':[{'index':0,'depth':'rgb','mode':'on','color':'eb4d4b','duration':0,'brightness':0}]}]}
        commands=[]
        def runner(args,**unused):
            commands.append(args)
            if args[-3:]==['profile','active','get']:return str(state['active'])
            led=state['profiles'][0]['leds'][0]
            if args[-1]=='get':
                return 'LED: 0, depth: rgb, mode: '+led['mode']+', duration: '+str(led['duration'])+', brightness: '+str(led['brightness'])
            if 'set' in args:
                index=args.index('set');key=args[index+1]
                led[key]=int(args[index+2]) if key in ('duration','brightness') else args[index+2]
                return ''
            raise AssertionError(args)
        self.manager.devices=[device];self.editor.runner=runner;self.editor.reader=lambda target:copy.deepcopy(state)
        self.editor.bind(self.manager,device);self.wait();self.editor.setSection('lighting')
        self.editor.edit('ratbagctl:led:0:mode','cycle')
        self.assertEqual(commands,[])
        visible={row['id'] for row in self.editor.fields._rows}
        self.assertIn('ratbagctl:led:0:duration:cycle',visible)
        self.assertNotIn('ratbagctl:led:0:duration:breathing',visible)
        self.assertNotIn('ratbagctl:led:0:color',visible)
        self.assertEqual(self.editor._desired(self.editor._field('ratbagctl:led:0:duration:cycle'))[0],8000)
        self.assertEqual(self.editor._desired(self.editor._field('ratbagctl:led:0:brightness:cycle'))[0],255)
        self.editor.edit('ratbagctl:led:0:duration:cycle',2600)
        self.editor.edit('ratbagctl:led:0:mode','breathing')
        self.assertEqual(self.editor._desired(self.editor._field('ratbagctl:led:0:duration:breathing'))[0],8000)
        self.editor.edit('ratbagctl:led:0:mode','cycle')
        self.assertEqual(self.editor._desired(self.editor._field('ratbagctl:led:0:duration:cycle'))[0],2600)
        self.editor.applyGroup();self.wait()
        writes=[args[args.index('set')+1:] for args in commands if 'set' in args]
        self.assertEqual(writes,[['duration','2600'],['brightness','255'],['mode','cycle']])
        self.assertEqual(state['profiles'][0]['leds'][0]['duration'],2600)
        self.assertEqual(self.editor.resultState,'sent_unverified')

    def test_g502_zero_period_requires_explicit_speed_edit_and_reactivates_mode(self):
        import copy
        device=Device('g502','Logitech G502 HERO','mouse','ratbagctl','exact-g502',physical='/test/g502',connected=True)
        state={'active':0,'text':'Model: usb:046d:c08b:0','dpis':[],'rates':[],
               'button_types':{},'led_modes':{0:['on','cycle']},
               'profiles':[{'index':0,'rate':1000,'resolutions':[],'buttons':[],
                            'leds':[{'index':0,'depth':'rgb','mode':'cycle','color':None,'duration':0,'brightness':0}]}]}
        commands=[]
        def runner(args,**unused):
            commands.append(args)
            if args[-3:]==['profile','active','get']:return '0'
            led=state['profiles'][0]['leds'][0]
            if args[-1]=='get':return f"LED: 0, depth: rgb, mode: {led['mode']}, duration: {led['duration']}, brightness: {led['brightness']}"
            if 'set' in args:
                index=args.index('set');key=args[index+1]
                led[key]=int(args[index+2]) if key in ('duration','brightness') else args[index+2]
                return ''
            raise AssertionError(args)
        self.manager.devices=[device];self.editor.runner=runner;self.editor.reader=lambda target:copy.deepcopy(state)
        self.editor.bind(self.manager,device);self.wait();self.editor.setSection('lighting')
        self.assertEqual(self.editor.dirtyCount,0)
        self.editor.edit('ratbagctl:led:0:duration:cycle',8000)
        self.assertEqual(commands,[])  # Editing a draft never writes to the device.
        self.editor.applyGroup();self.wait()
        self.assertEqual([args[args.index('set')+1:] for args in commands if 'set' in args],
                         [['duration','8000'],['brightness','255'],['mode','cycle']])

    def k7_fixture(self):
        import json
        from unittest.mock import patch
        from tests.unit.test_k7_settings import NativeTransport,ITEM
        from logi_center.adapters.mchose.mchose_adapter import hardware,k7_capabilities
        native=NativeTransport()
        device=Device('k7','MCHOSE K7 Ultra','mouse','mchose','target',physical='/test/k7',
                      vid='3837',pid='1001',connection='wireless',connected=True)
        device.capabilities=[Capability('profiles','mchose',True,True,False,False,1,'device'),
                             *k7_capabilities('target',native.read())]
        commands=[]
        def runner(args,**unused):
            commands.append(args)
            if args[2]=='read':return json.dumps(native.read())
            item={**ITEM,'physical':'target'}
            from logi_center.core.discovery.identity import identity
            with patch('logi_center.adapters.mchose.mchose_adapter.candidates',return_value=[item]),patch('logi_center.adapters.mchose.mchose_adapter.atomic_json'),patch('logi_center.adapters.mchose.mchose_adapter.time.sleep'):
                return json.dumps(hardware('set',identity('target'),args[4],json.loads(args[5]),transport=lambda node:native))
        self.manager.devices=[device];self.editor.runner=runner;self.editor.bind(self.manager,device)
        return native,device,commands

    def test_k7_dpi_batch_has_linked_axes_safe_count_and_targeted_readback(self):
        native,device,commands=self.k7_fixture()
        self.assertTrue(self.editor.k7Editor);self.assertFalse(self.editor.k7SeparateAxes)
        self.editor.edit('mchose:dpi_config:x1',850)
        self.assertEqual(self.editor._desired(self.editor._field('mchose:dpi_config:y1'))[0],850)
        self.editor.edit('mchose:dpi_config:active',5)
        self.editor.edit('mchose:dpi_config:count',2)
        self.assertEqual(self.editor._desired(self.editor._field('mchose:dpi_config:active'))[0],1)
        self.assertEqual(commands,[]);self.editor.applyGroup();self.wait()
        self.assertEqual(len(native.commands),1);self.assertEqual(native.commands[0][1],0x40)
        self.assertEqual((native.read()['stage'],native.read()['dpi']),(1,850))
        self.assertEqual(self.editor.resultState,'confirmed');self.assertEqual(self.editor.dirtyCount,0)
        self.owner.refresh.assert_not_called()

    def test_k7_separate_axes_and_discard_survive_page_changes(self):
        native,device,commands=self.k7_fixture()
        self.editor.setK7SeparateAxes(True);self.editor.edit('mchose:dpi_config:x0',450)
        self.assertEqual(self.editor._desired(self.editor._field('mchose:dpi_config:y0'))[0],400)
        self.editor.setSection('buttons');self.editor.setSection('pointer')
        self.assertEqual(self.editor._desired(self.editor._field('mchose:dpi_config:x0'))[0],450)
        self.editor.discardGroup();self.assertEqual(self.editor.dirtyCount,0);self.assertEqual(commands,[])

    def test_k7_button_editor_selects_native_ids_and_blocks_last_left_click(self):
        native,device,commands=self.k7_fixture();self.editor.setSection('buttons')
        self.assertEqual([b['index'] for b in self.editor.k7Buttons],[0,2,1,3,4])
        self.editor.selectK7Button(4);self.assertEqual(self.editor.k7SelectedButton,4)
        self.editor.edit('mchose:button_bindings:0',[9,0xffffff]);self.editor.applyGroup()
        self.assertFalse(self.editor.busy);self.assertIn('левым щелчком',self.editor.message)
        self.assertEqual(commands,[]);self.editor.discardGroup()
        self.editor.edit('mchose:button_bindings:4',[1,0x100000]);self.editor.applyGroup();self.wait()
        self.assertEqual(native.read()['button_bindings']['4'],[1,0x100000])
        self.assertEqual(self.editor.dirtyCount,0);self.assertEqual(len(native.commands),1)

    def test_k7_stale_profile_retains_draft_without_writes(self):
        native,device,commands=self.k7_fixture();self.editor.edit('mchose:dpi_config:x1',850)
        native.raw[0]=0
        self.editor.applyGroup();self.wait()
        self.assertEqual(native.commands,[]);self.assertGreater(self.editor.dirtyCount,0)
        self.assertNotEqual(self.editor.resultState,'confirmed')

    def test_k7_wired_identity_retains_editors_without_claiming_a_dock(self):
        native,device,commands=self.k7_fixture();device.pid='4150'
        self.editor.bind(self.manager,device)
        self.assertTrue(self.editor.k7Editor)
        self.assertIn('buttons',[s['id'] for s in self.editor.sections])
        self.assertNotIn('dock',[s['id'] for s in self.editor.sections])
        self.assertEqual(commands,[])

    def test_k7_old_dpi_and_stage_drafts_remain_visible_for_manual_review(self):
        native,device,commands=self.k7_fixture()
        old='device:k7:dpi:profile:1:stage:3'
        self.editor.store.values[old]={'base':3200,'desired':3250}
        self.editor.store.values['device:k7:stage:profile:1']={'base':0,'desired':3}
        rows=self.editor.k7LegacyDrafts
        self.assertEqual(len(rows),2);self.assertEqual(next(r['value'] for r in rows if r['key']==old),'3250')
        self.assertEqual(self.editor.dirtyCount,0);self.assertEqual(commands,[])
        self.editor.discardK7LegacyDraft(old)
        self.assertNotIn(old,{r['key'] for r in self.editor.k7LegacyDrafts})

    def test_k7_sensor_batch_can_switch_on_and_off_and_keeps_other_bits(self):
        native,device,commands=self.k7_fixture();self.editor.setSection('advanced')
        self.editor.edit('mchose:sensor_config:motion_sync',True)
        self.editor.edit('mchose:sensor_config:ripple',True)
        self.assertEqual(commands,[]);self.editor.applyGroup();self.wait()
        self.assertEqual(self.editor.resultState,'confirmed');self.assertEqual(len(native.commands),1)
        self.editor.edit('mchose:sensor_config:motion_sync',False);self.editor.applyGroup();self.wait()
        self.assertFalse(native.read()['sensor_config']['motion_sync'])
        self.assertTrue(native.read()['sensor_config']['ripple']);self.assertTrue(native.raw[17]&32)
