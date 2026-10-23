"""Bounded Ace68-II 55/AA output/input protocol, independently implemented
from M HUB CZ channel's getInfo/getBase/getFuncConfig/getKeyTrigger definitions.
No factory reset, calibration, firmware or automatic profile repair.
"""
import os,time,select,fcntl
from execution import Fault,FaultCode

READ_COMMANDS={3,4,5,8,160}

def packet(command,offset,size,data=None):
    if type(command) is not int or type(offset) is not int or not 0<=offset<=65535 or type(size) is not int or not 1<=size<=56:raise ValueError('Invalid keyboard request bounds')
    if data is None and command not in READ_COMMANDS:raise ValueError('Undocumented read command')
    if data is not None and (len(data)!=size or any(type(v) is not int or not 0<=v<=255 for v in data)):raise ValueError('Invalid keyboard payload')
    body=bytearray(64);body[0]=0x55;body[1]=command;body[4:8]=bytes([size,offset&255,offset>>8,0])
    if data is not None:body[8:8+size]=bytes(data)
    body[3]=sum(body[4:])&255
    return bytes([0])+body

def response(frame,command,offset,size,allow_empty=False):
    if len(frame)!=64 or frame[0]!=0xAA or frame[1]!=command or frame[5]+256*frame[6]!=offset:return None
    count=frame[4]
    if not (0 if allow_empty else 1)<=count<=size or count>56:raise ValueError('Invalid keyboard reply length')
    if frame[3]!=(sum(frame[4:8+count])&255):raise ValueError('Keyboard reply checksum mismatch')
    return frame[8:8+count]

class Transport:
    def __init__(self,node):self.node=node;self.fd=None
    def __enter__(self):
        try:self.fd=os.open(self.node,os.O_RDWR|os.O_NONBLOCK|os.O_CLOEXEC)
        except FileNotFoundError:raise Fault(FaultCode.DISCONNECTED,'mchose-ace68','Configuration node disappeared') from None
        try:fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BaseException:os.close(self.fd);raise
        return self
    def __exit__(self,*args):os.close(self.fd)
    def request(self,command,offset,size,data=None):
        request=packet(command,offset,size,data);writing=data is not None
        if os.write(self.fd,request)!=len(request):raise Fault(FaultCode.CONNECTION,'mchose-ace68','Short USB output transfer')
        deadline=time.monotonic()+1.0
        while time.monotonic()<deadline:
            if not select.select([self.fd],[],[],max(0,deadline-time.monotonic()))[0]:break
            try:raw=os.read(self.fd,64)
            except BlockingIOError:continue
            if not raw:raise Fault(FaultCode.DISCONNECTED,'mchose-ace68','Keyboard disconnected')
            observed=response(raw,command,offset,size,allow_empty=writing)
            if observed is not None:return observed
        raise Fault(FaultCode.TIMEOUT,'mchose-ace68','No matching keyboard reply; no recovery write attempted')
    def read(self,command,offset,length):
        result=b''
        for i in range(0,length,56):
            count=min(56,length-i);chunk=self.request(command,offset+i,count);result+=chunk
            if len(chunk)<count:break
        return result

KEY_INDICES=[50,30,51,41,31,52,72,32,53,73,33,3,54,44,34,70,0,71,1,21,42,2,63,43,13,23,64,74,14,4,60,10,61,11,62,12,22,46,26,47,67,77,48,24,40,20,25,15,5,35,66,56,16,6,57,27,68,28,45,75,55,76,36,7,37,58,78,18]
RATES={4:1000,3:2000,2:4000,1:8000}
MODES={3:'Static',4:'Breathing',6:'Wave',255:'Off'}
KEY_FIELDS=['actuation','rapid_trigger','rt_press','rt_release','press_dead_zone','release_dead_zone']

def decode_keys(raw):
    if len(raw)!=1024:raise ValueError('Incomplete magnetic key table')
    result={f:{} for f in KEY_FIELDS};details={}
    for index in KEY_INDICES:
        key=str(index);b=raw[index*8:index*8+8]
        if b[0]&240!=160 or b[1]&15 not in [0,1,2]:raise ValueError('Unsupported magnetic-key record')
        press=(b[3]>>3)&3;release=(b[3]>>1)&3
        if press not in [0,1] or release not in [0,1]:raise ValueError('Unverified precision mode for Ace68-II')
        details[key]={'switch_type':b[0]&15,'press_base':100 if press==0 else 200,'release_base':100 if release==0 else 200}
        result['actuation'][key]=(int.from_bytes(bytes([b[2],b[3]&1]),'little')+1)/100
        result['rapid_trigger'][key]=b[1]&15
        result['rt_press'][key]=round((b[4]+256*(b[5]&1)+1)/details[key]['press_base'],3)
        result['rt_release'][key]=round((b[6]+256*(b[7]&1)+1)/details[key]['release_base'],3)
        result['press_dead_zone'][key]=(b[5]>>1)/100
        result['release_dead_zone'][key]=(b[7]>>1)/100
    result['key_details']=details;return result

def state(transport):
    info=transport.read(3,0,56);base=transport.read(4,0,56)
    if len(info)<2 or not any(info[:2]) or len(base)!=56:raise ValueError('Invalid Ace68-II info/base')
    order=list(base[2:6]);count=base[1];position=base[0]
    if sorted(order)!=[0,1,2,3] or not 1<=count<=4 or not 0<=position<count:raise ValueError('Invalid profile table; no automatic repair')
    profile=order[position];config=transport.read(5,profile*64,64);keys=transport.read(160,profile*1024,1024)
    if len(config)!=64 or config[4]&15 not in RATES or not 0<=config[9]<=100 or not 0<=config[10]<=4:raise ValueError('Unsupported profile configuration')
    result={'firmware_version':format(int.from_bytes(info[:2],'little'),'x'),'profiles':profile,'profile_choices':order[:count],'polling_rate':RATES[config[4]&15],'brightness':config[9],'lighting_speed':4-config[10],'lighting_mode':MODES.get(config[8],str(config[8])),'lighting_palette':{0:'Single color',1:'Random colors'}.get(config[12],str(config[12])),'lighting':list(config[14:17]),'raw_base':list(base),'raw_config':list(config),'raw_keys':list(keys)}
    result.update(decode_keys(keys));return result

def validate_key_value(current,field,key,value):
    import math
    if key not in current['key_details']:raise ValueError('Key is not in the verified Ace68-II layout')
    if field=='rapid_trigger':
        if type(value) is not int or value not in [0,1,2]:raise ValueError('Unsupported RT mode')
        return value
    if type(value) not in [int,float] or not math.isfinite(value):raise ValueError('Expected finite distance in millimetres')
    base=current['key_details'][key]['press_base' if field=='rt_press' else 'release_base'] if field in ['rt_press','rt_release'] else 100
    low,high=(.1,3.3) if field=='actuation' else (0,.5) if field.endswith('dead_zone') else (2/base,min(3.3,500/base))
    ticks=round(value*base)
    if not low<=value<=high or not math.isclose(value*base,ticks,abs_tol=1e-6):raise ValueError('Distance outside verified range/precision')
    return ticks

def changed_key(raw,field,value):
    b=bytearray(raw)
    if field=='actuation':
        value-=1;b[2]=value&255;b[3]=(b[3]&254)|(value>>8)
    elif field=='rapid_trigger':b[1]=(b[1]&240)|value
    elif field in ['rt_press','rt_release']:
        value-=1;i=4 if field=='rt_press' else 6;b[i]=value&255;b[i+1]=(b[i+1]&254)|(value>>8)
    elif field in ['press_dead_zone','release_dead_zone']:
        i=5 if field=='press_dead_zone' else 7;b[i]=(b[i]&1)|(value<<1)
    else:raise ValueError('Unimplemented magnetic parameter')
    return bytes(b)
