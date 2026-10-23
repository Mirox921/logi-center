"""Private app drafts, kept separately from observations and submitted settings."""
from pathlib import Path
from copy import deepcopy
from threading import RLock
import json,os,tempfile

def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump(value,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        try:os.unlink(name)
        except FileNotFoundError:pass

class DraftStore:
    def __init__(self,path=None):
        self.path=Path(path) if path else Path.home()/'.config/logi-center/drafts.json'
        self.lock=RLock();self.values={}
        try:
            if self.path.stat().st_size<=2*1024*1024:
                data=json.loads(self.path.read_text())
                if data.get('version')==1 and isinstance(data.get('drafts'),dict):self.values=data['drafts']
        except (OSError,ValueError,AttributeError):pass
    def save(self):atomic_json(self.path,{'version':1,'drafts':self.values})
    def edit(self,key,base,desired):
        with self.lock:
            if desired==base:self.values.pop(key,None)
            else:
                previous=self.values.get(key,{})
                self.values[key]={'base':deepcopy(previous.get('base',base)),'desired':deepcopy(desired)}
            self.save()
    def get(self,key,observed):
        with self.lock:
            value=self.values.get(key)
            if not isinstance(value,dict) or not {'base','desired'}<=value.keys():return deepcopy(observed),False
            return deepcopy(value['desired']),observed!=value['base'] and observed!=value['desired']
    def submitted(self,key,state):
        with self.lock:
            if state=="confirmed":self.values.pop(key,None)
            elif key in self.values:self.values[key]["submission_state"]=state
            self.save()
    def discard(self,key):
        with self.lock:self.values.pop(key,None);self.save()
