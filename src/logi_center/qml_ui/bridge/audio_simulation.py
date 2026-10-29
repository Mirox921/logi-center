"""Explicit memory-only PulseAudio fixture for the simulated QML frontend."""
import json
from copy import deepcopy


class AudioSimulation:
    def __init__(self):
        self.items={
            'sinks':[{'index':1,'name':'simulation-output','description':'USB Headphones · SIM','state':'IDLE','volume':{'mono':{'value_percent':'50%'}},'mute':False},
                     {'index':2,'name':'simulation-hdmi','description':'HDMI / DisplayPort 3 · SIM','state':'UNAVAILABLE','volume':{},'mute':False}],
            'sources':[{'index':3,'name':'simulation-microphone','description':'Microphone · SIM','state':'IDLE','volume':{'mono':{'value_percent':'60%'}},'mute':False}]}
        self.defaults={'sink':'simulation-output','source':'simulation-microphone'}
    def snapshot(self):return {'sinks':json.dumps(self.items['sinks']),'sources':json.dumps(self.items['sources']),
                               'default_sink':self.defaults['sink'],'default_source':self.defaults['source']}
    def run(self,args,**unused):
        if args[:4]==['pactl','-f','json','list']:return json.dumps(self.items.get(args[4],[]))
        if args[:1]!=['pactl']:raise ValueError('Unsupported simulated audio command')
        op=args[1]
        for kind in ('sink','source'):
            if op=='get-default-'+kind:return self.defaults[kind]
            if op=='set-default-'+kind:self.defaults[kind]=args[2];return ''
            for setting in ('volume','mute'):
                if op=='set-'+kind+'-'+setting:
                    item=next(i for i in self.items[kind+'s'] if i['name']==args[2])
                    if setting=='volume':item['volume']={'mono':{'value_percent':args[3]}}
                    else:item['mute']=args[3]=='1'
                    return ''
        raise ValueError('Unsupported simulated audio command')
