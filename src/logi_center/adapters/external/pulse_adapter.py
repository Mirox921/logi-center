"""Read-only PulseAudio/PipeWire endpoint discovery and existing operation plans."""
import json,re
from logi_center.core.devices.devices import Device, DeviceManager
from logi_center.core.capabilities.model import Capability
from logi_center.core.discovery.identity import identity, usb_identity

class PulseAdapter:
    name='pactl'
    def __init__(self,runner=None):
        from logi_center.adapters.external.backend import run
        self.run=runner or run
    def discover(self):
        records=[]
        for collection,kind in [('sinks','output'),('sources','microphone')]:
            for node in json.loads(self.run(['pactl','-f','json','list',collection])):
                name=node['name']
                if name.endswith('.monitor') or name.startswith('easyeffects_'):continue
                props=node.get('properties',{});card=str(props.get('alsa.card',''))
                physical,vid,pid=usb_identity('/sys/class/sound/card'+card+'/device') if card.isdigit() else ('','','')
                # Same sound card can expose several legitimate audio endpoints.
                physical=physical or ('alsa-card:'+card if card.isdigit() else '')
                prefix=kind+':'+name
                caps=[]
                volumes=node.get('volume',{})
                if isinstance(volumes,dict) and volumes and all(isinstance(v,dict) and re.fullmatch(r'\d+%',str(v.get('value_percent',''))) for v in volumes.values()):
                    level=int(next(iter(volumes.values()))['value_percent'].rstrip('%'))
                    caps.append(Capability(prefix+':volume',self.name,True,True,True,True,level,'audio_server',minimum=0,maximum=100,evidence=['software_detected','read_observed'],limitation='Setting volume changes all channels.'))
                if type(node.get('mute')) is bool:caps.append(Capability(prefix+':mute',self.name,True,True,True,True,node['mute'],'audio_server',choices=[False,True],evidence=['software_detected','read_observed']))
                from logi_center.core.services.operations import plan_for
                for cap in caps:
                    setting=cap.name.rsplit(':',1)[-1]
                    cap.label=node.get('description','Audio endpoint')
                    cap.plan=lambda value,k=kind,n=name,f=setting:plan_for(['pactl','set-'+('sink' if k=='output' else 'source')+'-'+f,n,str(int(value))+'%' if f=='volume' else '1' if value else '0'])
                records.append(Device('pulse:'+prefix,node.get('description',name),'audio',self.name,name,physical,vid,pid,'usb' if vid else 'audio',capabilities=caps))
        return records
