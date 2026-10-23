"""Opt-in audio resources and direction-safe EasyEffects presets."""
from pathlib import Path
from threading import Event,Lock,Thread
from array import array
import hashlib,json,math,os,select,signal,subprocess,tempfile,time,wave
from execution import Fault,FaultCode,classify
from operations import Result,State


def preset_lists(root=None):
    root=Path(root) if root else Path.home()/'.config/easyeffects'
    return {kind:sorted(p.stem for p in (root/kind).glob('*.json') if not p.stem.startswith('LogiCenter-')) for kind in ['input','output']}

def prepare_preset(kind,name,root=None):
    if kind not in ['input','output'] or Path(name).name!=name or name in ['.','..']:raise ValueError('Invalid preset selection')
    root=Path(root) if root else Path.home()/'.config/easyeffects'
    source=root/kind/(name+'.json')
    if source.stat().st_size>2*1024*1024:raise ValueError('Preset exceeds 2 MB')
    data=json.loads(source.read_text())
    if not isinstance(data.get(kind),dict):raise ValueError('Preset does not contain the selected audio direction')
    payload=json.dumps({kind:data[kind]},sort_keys=True,ensure_ascii=False)
    alias='LogiCenter-'+kind+'-'+hashlib.sha256(payload.encode()).hexdigest()[:16]
    opposite='output' if kind=='input' else 'input'
    if (root/opposite/(alias+'.json')).exists():raise ValueError('Managed preset name exists in the opposite direction')
    destination=root/kind/(alias+'.json')
    if destination.exists() and destination.read_text()!=payload:raise ValueError('Managed preset collision')
    if not destination.exists():
        with destination.open('x') as stream:stream.write(payload)
    return alias

def load_preset(kind,name,runner=None,root=None):
    from backend import run
    runner=runner or run
    try:
        alias=prepare_preset(kind,name,root)
        runner(['easyeffects','-l',alias])
        actual=runner(['easyeffects','-a',kind]).strip()
        # CLI can read last-loaded state from disk when the engine is not running.
        return Result(State.SENT if actual==alias else State.MISMATCH,'easyeffects',alias,actual,'backend_cache')
    except Fault as error:return Result(State.ERROR,'easyeffects',name,fault=error)

def processed_route(sources,outputs,raw_name):
    raw=next((s for s in sources if s['name']==raw_name),None)
    if raw is None:raise Fault(FaultCode.DISCONNECTED,'audio','Microphone is disconnected')
    captures=any(o.get('source')==raw['index'] and 'easy' in (' '.join(str(v) for k,v in o.get('properties',{}).items() if k in ['application.name','application.process.binary'])).lower() for o in outputs)
    processed=next((s['name'] for s in sources if s['name']=='easyeffects_source'),None)
    return processed if captures else None

def peak(raw):
    values=array('f');values.frombytes(raw[:len(raw)//4*4])
    finite=[abs(x) for x in values if math.isfinite(x)]
    return min(1.,max(finite,default=0.))

def wav_write(path,chunks,rate=16000):
    with wave.open(str(path),'wb') as output:
        output.setnchannels(1);output.setsampwidth(2);output.setframerate(rate)
        for raw in chunks:
            values=array('f');values.frombytes(raw[:len(raw)//4*4])
            pcm=array('h',(round(max(-1.,min(1.,x if math.isfinite(x) else 0))*32767) for x in values))
            output.writeframes(pcm.tobytes())

class AudioSession:
    def __init__(self,popen=None):
        self.popen=popen or subprocess.Popen;self.lock=Lock();self.processes=[];self.cancel=Event();self.finish=Event();self.generation=0;self.temp=None;self.clips={};self.recording=False
    def _launch(self,args):
        try:p=self.popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        except FileNotFoundError:raise Fault(FaultCode.MISSING,args[0],'Audio component is not installed') from None
        except PermissionError:raise Fault(FaultCode.PERMISSION,args[0],'Audio access denied') from None
        with self.lock:self.processes.append(p)
        return p
    @staticmethod
    def _terminate(process):
        if process.poll() is None:
            try:process.terminate()
            except ProcessLookupError:pass
    def _discard(self):
        self.clips={}
        if self.temp:self.temp.cleanup();self.temp=None
    def stop(self):
        self.cancel.set();self.finish.set();self.generation+=1;self.recording=False
        with self.lock:
            for process in self.processes:self._terminate(process)
        self._discard()
    def close(self):self.stop()
    def finish_recording(self):self.finish.set()
    def _begin(self):
        self.stop();self.cancel=Event();self.finish=Event()
        return self.generation,self.cancel,self.finish
    def _capture(self,source,cancel,finish,duration,on_level=None):
        process=self._launch(['parec','--device='+source,'--format=float32le','--rate=16000','--channels=1','--raw'])
        chunks=[];deadline=time.monotonic()+duration;last=0.;pending=b'';total=0
        try:
            while not cancel.is_set() and not finish.is_set() and time.monotonic()<deadline:
                if select.select([process.stdout],[],[],.15)[0]:
                    raw=os.read(process.stdout.fileno(),4096)
                    if not raw:
                        if not cancel.is_set() and not finish.is_set():
                            details=os.read(process.stderr.fileno(),2000).decode(errors='replace') if select.select([process.stderr],[],[],0)[0] else ''
                            raise classify('parec',details or 'Audio capture stopped unexpectedly')
                        break
                    raw=pending+raw;aligned=len(raw)//4*4;pending=raw[aligned:];raw=raw[:aligned];total+=len(raw)
                    if on_level:
                        if time.monotonic()-last>.1:on_level(peak(raw));last=time.monotonic()
                    else:chunks.append(raw)
                if not on_level and total>16000*4*min(duration,10)+8192:break
            return chunks
        finally:
            self._terminate(process)
            try:process.wait(timeout=.5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
            process.stdout.close();process.stderr.close()
            with self.lock:
                if process in self.processes:self.processes.remove(process)
    def meter(self,source,on_level,on_error):
        generation,cancel,finish=self._begin()
        def worker():
            try:self._capture(source,cancel,finish,3600,lambda value:on_level(value) if generation==self.generation else None)
            except Exception as error:
                if not cancel.is_set():on_error(error)
        Thread(target=worker,daemon=True).start()
    def record(self,source,processed,on_complete,on_error,seconds=8):
        if not 0<seconds<=10:raise ValueError('Recording limit is 10 seconds')
        generation,cancel,finish=self._begin();self.recording=True
        def worker():
            chunks={};errors=[];threads=[]
            def capture(label,device):
                try:chunks[label]=self._capture(device,cancel,finish,seconds)
                except Exception as error:errors.append(error);finish.set()
            for label,device in [('original',source),('processed',processed)]:
                if device:
                    thread=Thread(target=capture,args=(label,device),daemon=True);threads.append(thread);thread.start()
            for thread in threads:thread.join()
            if cancel.is_set() or generation!=self.generation:return
            self.recording=False
            if errors:on_error(errors[0]);return
            if not chunks.get('original'):on_error(Fault(FaultCode.CONNECTION,'parec','No microphone samples received'));return
            temp=tempfile.TemporaryDirectory(prefix='logi-audio-')
            try:
                clips={}
                for label,frames in chunks.items():
                    if frames:
                        path=Path(temp.name)/(label+'.wav');wav_write(path,frames);clips[label]=path
                with self.lock:
                    if generation!=self.generation:temp.cleanup();return
                    self.temp=temp;self.clips=clips
                on_complete(set(clips))
            except Exception as error:temp.cleanup();on_error(error)
        Thread(target=worker,daemon=True).start()
    def play(self,label):
        path=self.clips.get(label)
        if not path or not path.exists():raise Fault(FaultCode.CONFIG,'paplay','No test recording is available')
        process=self._launch(['paplay',str(path)])
        def reap():
            try:process.communicate(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.communicate()
            finally:
                with self.lock:
                    if process in self.processes:self.processes.remove(process)
        Thread(target=reap,daemon=True).start()
