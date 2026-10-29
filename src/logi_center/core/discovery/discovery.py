"""Event-based device discovery with a cheap fallback and explicit lifetime."""
from threading import Event,Lock,Thread
from dataclasses import dataclass
import subprocess,shutil
from pathlib import Path

@dataclass
class MousePresence:
    """Retain the selected model without treating its old name as connectivity."""
    name:str=''
    connected:bool|None=None
    def invalidate(self):self.connected=None
    def update(self,mice,error=False):
        if error:self.connected=None;return None
        selected=next((item for item in mice if item[1]==self.name),mice[0] if mice else None)
        self.connected=selected is not None
        if selected:self.name=selected[1]
        return selected

class Epoch:
    def __init__(self):self._lock=Lock();self._event=Event();self.generation=0
    def token(self):
        with self._lock:return self._event
    def invalidate(self):
        with self._lock:
            self._event.set();self._event=Event();self.generation+=1
            return self.generation

class DeviceMonitor:
    def __init__(self,callback):
        self.callback=callback;self.stop_event=Event();self.observer=None;self.process=None;self.threads=[];self.mode='udev';self.upower_connection=None;self.upower_subscription=None
    def start(self):
        try:
            import pyudev
            monitor=pyudev.Monitor.from_netlink(pyudev.Context())
            self.observer=pyudev.MonitorObserver(monitor,callback=self._udev_event,name='logi-udev');self.observer.start()
        except (ImportError,OSError):
            self.mode='sysfs-fallback';self._thread(self._fallback)
        try:
            from gi.repository import Gio
            self.upower_connection=Gio.bus_get_sync(Gio.BusType.SYSTEM,None)
            self.upower_subscription=self.upower_connection.signal_subscribe(
                'org.freedesktop.UPower','org.freedesktop.DBus.Properties','PropertiesChanged',None,None,
                Gio.DBusSignalFlags.NONE,self._upower_event)
        except Exception:
            self.upower_connection=None;self.upower_subscription=None
        if shutil.which('pactl'):self._thread(self._audio)
    def _udev_event(self,device):
        if self.stop_event.is_set():return
        if device.subsystem in ['usb','hidraw','sound','input','bluetooth'] and device.action in ['add','remove','bind','unbind','change']:self.callback('devices')
        elif device.subsystem=='power_supply' and device.action=='change':self.callback('battery')
    def _upower_event(self,connection,sender,path,interface,signal,parameters):
        if self.stop_event.is_set():return
        try:changed_interface,properties,_=parameters.unpack()
        except (AttributeError,ValueError,TypeError):return
        if changed_interface=='org.freedesktop.UPower.Device' and any(key in properties for key in ['Percentage','State','IsPresent','WarningLevel']):
            self.callback('battery')
    def _thread(self,fn):
        thread=Thread(target=fn,daemon=True);self.threads.append(thread);thread.start()
    def _fallback(self):
        previous=None
        while not self.stop_event.wait(5):
            current=tuple(sorted(str(p.resolve()) for folder in ['/sys/class/hidraw','/sys/class/sound','/sys/class/input'] for p in Path(folder).glob('*')))
            if previous is not None and current!=previous:self.callback('devices')
            previous=current
    def _audio(self):
        # Restart a dropped subscription at a bounded rate while the app remains open.
        while not self.stop_event.is_set():
            try:
                self.process=subprocess.Popen(['pactl','subscribe'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,env=__import__('os').environ|{'LC_ALL':'C.UTF-8'})
                for line in self.process.stdout:
                    if self.stop_event.is_set():break
                    if any("Event '"+verb+"'" in line for verb in ['new','remove']) and any('on '+kind+' ' in line for kind in ['sink','source','card']):
                        self.callback('devices')
                    elif "Event 'change'" in line and any('on '+kind in line for kind in ['server','sink ','source ']):
                        self.callback('audio-state')
                self.process.stdout.close();self.process.wait(timeout=1)
            except (OSError,subprocess.TimeoutExpired):pass
            if self.process and self.process.poll() is None:self.process.kill();self.process.wait()
            self.process=None
            if self.stop_event.wait(5):break
    def stop(self):
        self.stop_event.set()
        if self.observer:self.observer.stop()
        if self.upower_connection and self.upower_subscription:
            self.upower_connection.signal_unsubscribe(self.upower_subscription)
            self.upower_subscription=None;self.upower_connection=None
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=.5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
        for thread in self.threads:thread.join(timeout=1)
