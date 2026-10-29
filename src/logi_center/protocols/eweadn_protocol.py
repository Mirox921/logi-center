"""Pure EWEADN/ByteTech mouse codec; supplied archive + official Hub 3.3.4.

No I/O. Configuration writes are prepared from complete observed pages and
preserve unknown bits. Macro-bank OTA/format and firmware are never exposed.
"""
import struct

REPORT_ID=3
PACKET_SIZE=63
RATES=(1000,500,250,125,8000,4000,2000)
MODE_BITS={0:0,1:64,2:128,3:4}
MODELS={9895604650026:'s9max',9895604649998:'s9pro',9895604650000:'s9ultra',9895604650058:'s9ultra+'}
NAMES={'s9max':'EWEADN S9 Max','s9pro':'EWEADN S9 Pro','s9ultra':'EWEADN S9 Ultra','s9ultra+':'EWEADN S9 Ultra+'}
FIELDS=('dpi_config','sensor_config','button_bindings')


def integer(value,low,high):
    if type(value) is not int or not low<=value<=high:raise ValueError('EWEADN value outside documented range')
    return value


def packet(main,sub=0,data=b'',encap=0):
    integer(main,0,255);integer(sub,0,255)
    integer(encap,0,255)
    if len(data)>57:raise ValueError('Configuration payload too large')
    result=bytearray(PACKET_SIZE);result[1]=0x50;result[2]=len(data);result[3]=encap;result[4]=main;result[5]=sub
    result[6:6+len(data)]=data;result[0]=sum(result[1:])&255
    return bytes([REPORT_ID])+result


class ResponseError(ValueError):
    def __init__(self,reason,expected=None,actual=None):
        self.reason=reason;self.expected=expected;self.actual=actual
        super().__init__('Invalid EWEADN response: '+reason)


def response(raw,page,encap=0):
    raw=bytes(raw)
    if len(raw)==64:
        if raw[0]!=REPORT_ID:raise ResponseError('report_id',REPORT_ID,raw[0])
        raw=raw[1:]
    elif raw[:1]==bytes([REPORT_ID]):raw=raw[1:]
    if len(raw)<6:raise ResponseError('short_header')
    if raw[0]!=0x50:raise ResponseError('command_type',0x50,raw[0])
    if raw[1]!=0:raise ResponseError('ack',0,raw[1])
    size=raw[2]
    # The supplied S9 receiver reference documents 0x0b in ten-byte
    # replies. Accept only its exact short wire shape (16 bytes with ID),
    # never synthesize the eleventh byte from the allocated buffer padding.
    if size==11 and len(raw)==15:size=10
    if not 1<=size<=min(10,len(raw)-5):
        raise ResponseError('payload_length',min(10,len(raw)-5),raw[2])
    if raw[3]!=encap:raise ResponseError('encapsulation',encap,raw[3])
    if raw[4]!=page:raise ResponseError('offset',page,raw[4])
    return raw[5:5+size]


def model_identity(model):
    if len(model)<8:raise ValueError('Short EWEADN model reply')
    model_id=MODELS.get(int.from_bytes(model[2:8],'big'))
    if model_id is None:raise ValueError('Receiver model is not a verified S9 revision')
    return {'model_id':model_id,'name':NAMES[model_id],
            'firmware_version':f'0x{int.from_bytes(model[:2],"little"):04x}'}


def basics(raw):
    if len(raw)<7:raise ValueError('Short EWEADN status')
    battery=raw[0]&127
    return {'battery_status':battery if battery<=100 else None,'charging':bool(raw[0]&128),
            'profiles':raw[1]&15,'profile_count':raw[1]>>4,'max_report':raw[2],
            'max_dpi':int.from_bytes(raw[4:6],'little'),'macro_size':raw[6]}


def decode(pages,connection='wireless'):
    status=basics(pages[129]);model=pages[128]
    if len(model)<8:raise ValueError('Short EWEADN model reply')
    model_id=MODELS.get(int.from_bytes(model[2:8],'big'))
    if model_id is None:raise ValueError('Receiver model is not a verified S9 revision')
    sensor=bytes(pages[64]);dpi=bytes(pages[65]);buttons=bytes(pages[0])
    if len(sensor)<10 or len(dpi)<41 or len(buttons)<12:raise ValueError('Short EWEADN configuration page')
    active=(sensor[2]>>4);count=sensor[2]&15
    if not 1<=count<=8 or not 1<=active<=count or status['profiles']!=sensor[9]:raise ValueError('Profile or stage changed during read')
    if not 100<=status['max_dpi']<=65000:raise ValueError('Invalid device DPI limit')
    flags=sensor[5]
    mode=3 if flags&4 else (flags>>6)&3
    if mode not in MODE_BITS:raise ValueError('Unknown performance mode')
    config={'count':count,'active':active-1,'axes_available':bool(sensor[1]&128)}
    if config['axes_available'] and len(dpi)<57:raise ValueError('Missing independent DPI axes')
    for i in range(8):
        raw=struct.unpack_from('<H',dpi,1+i*2)[0]
        # The native encoding is DPI/50 - 1 within the sensor range.
        config['x'+str(i)]=(raw+1)*50
        config['y'+str(i)]=(struct.unpack_from('<H',dpi,41+i*2)[0]+1)*50 if config['axes_available'] else config['x'+str(i)]
        config['color'+str(i)]=list(dpi[17+i*3:20+i*3])
    sensor_config={'lod':sensor[3],'debounce':sensor[4],'sleep':sensor[8]*30,
                   'motion_sync':bool(flags&32),'ripple':bool(flags&16),'angle_snap':bool(flags&1),
                   'performance_mode':mode,'polling_rate':RATES[((sensor[1]>>4)&7) if connection=='usb' else sensor[1]&7] if (sensor[1]&7)<7 and ((sensor[1]>>4)&7)<7 else None}
    bindings={str(i):list(buttons[4*i:4*i+4]) for i in range(min(5,len(buttons)//4))}
    writable=[i for i in range(len(bindings)) if i<3 or bindings[str(i)][0]!=0]
    return dict(status,model_id=model_id,name=NAMES[model_id],firmware_version=f'0x{int.from_bytes(model[:2],"little"):04x}',
                connection=connection,dpi_config=config,sensor_config=sensor_config,button_bindings=bindings,
                writable_buttons=writable,pages={'0':list(buttons[:20]),'64':list(sensor[:10]),
                '65':list(dpi[:57 if config['axes_available'] else 41])})


def validate_action(action):
    if not isinstance(action,list) or len(action)!=4:raise ValueError('Expected four EWEADN action bytes')
    for value in action:integer(value,0,255)
    kind,c1,c2,c3=action
    if kind==0 and (c1 or c2 or c3):raise ValueError('Malformed default action')
    if kind==1 and (not 1<=c1<=5 or c2 or c3):raise ValueError('Unsupported mouse action')
    if kind==2 and (not 4<=c1<=231 or c2 or c3):raise ValueError('Unsupported keyboard action')
    if kind==3 and (c3 or (c1|(c2<<8)) not in (0xe2,0xe9,0xea,0xcd,0xb5,0xb6,0xb7,0x6f,0x70)):
        raise ValueError('Unsupported consumer action')
    if kind not in (0,1,2,3):raise ValueError('Action requires an unimplemented encoder')
    return action


def prepare(state,field,changes):
    """Return native commands plus expected pages; no blind setter defaults."""
    if field not in FIELDS or not isinstance(changes,dict) or not changes:raise ValueError('Invalid EWEADN changes')
    current=state[field];target={**current,**changes}
    if set(changes)-set(current) or 'axes_available' in changes:raise ValueError('Unknown setting')
    pages={int(k):bytearray(v) for k,v in state['pages'].items()};commands=[]
    if field=='sensor_config':
        raw=pages[64]
        for key,value in changes.items():
            if key in ('motion_sync','ripple','angle_snap'):
                if type(value) is not bool:raise ValueError('Expected a sensor switch')
                bit={'motion_sync':32,'ripple':16,'angle_snap':1}[key]
                raw[5]=(raw[5]&~bit)|(bit if value else 0)
            elif key=='performance_mode':
                integer(value,0,3);raw[5]=(raw[5]&~0xc4)|MODE_BITS[value]
            elif key=='polling_rate':
                if value not in RATES:raise ValueError('Unsupported polling rate')
                code=RATES.index(value)
                if state['max_report'] not in range(7) or value>RATES[state['max_report']]:raise ValueError('Polling rate exceeds device limit')
                shift=4 if state['connection']=='usb' else 0;mask=7<<shift
                raw[1]=(raw[1]&~mask)|(code<<shift)
                commands.append((53,1,bytes([raw[1]])))
            else:
                limits={'lod':(1,3 if state['model_id'] in ('s9ultra','s9ultra+') else 2),'debounce':(0,20),'sleep':(0,3000)}
                low,high=limits[key];integer(value,low,high)
                if key=='sleep' and value%30:raise ValueError('Sleep timer step is 30 seconds')
                native=value//30 if key=='sleep' else value
                offset={'lod':3,'debounce':4,'sleep':8}[key];raw[offset]=native
                commands.append((53,offset,bytes([native])))
        if set(changes)&{'motion_sync','ripple','angle_snap','performance_mode'}:commands.append((53,5,bytes([raw[5]])))
    elif field=='button_bindings':
        for key,value in changes.items():
            if int(key) not in state['writable_buttons']:raise ValueError('This physical button has no verified writable slot')
            validate_action(value)
        if not any(value==[1,1,0,0] or key=='0' and value==[0,0,0,0] for key,value in target.items()):
            raise ValueError('Keep at least one left-click button')
        # Establish the replacement left-click first. If that write is ignored,
        # per-command readback stops before the original left click is removed.
        ordered=sorted(changes.items(),key=lambda item:0 if item[1]==[1,1,0,0] or item[0]=='0' and item[1]==[0,0,0,0] else 1)
        for key,value in ordered:
            offset=4*int(key);pages[0][offset:offset+4]=bytes(value);commands.append((48,offset,bytes(value)))
    else:
        count=integer(target['count'],1,8);active=integer(target['active'],0,count-1)
        # SetDPI selects the stage being written. Restore the original active
        # stage last. All enabled stage values/colors come from the fresh page.
        affected={int(k[1:]) for k in changes if k.startswith(('x','y'))}|{int(k[5:]) for k in changes if k.startswith('color')}
        if any(i>=count for i in affected):raise ValueError('Cannot write a disabled DPI stage')
        if 'count' in changes:affected.update(range(count))
        affected.discard(active);order=sorted(affected)+[active]
        for i in order:
            x=integer(target['x'+str(i)],50,state['max_dpi']);y=integer(target['y'+str(i)],50,state['max_dpi'])
            if x%50 or y%50:raise ValueError('DPI step is 50')
            if not current['axes_available'] and x!=y:raise ValueError('Separate DPI axes are not active')
            color=target['color'+str(i)]
            if not isinstance(color,list) or len(color)!=3:raise ValueError('Expected RGB')
            for v in color:integer(v,0,255)
            data=bytes([((i+1)<<4)|count])+struct.pack('<H',x//50-1)+bytes(color)
            # The Hub uses v2.1, with optional independent Y encoded in 3 bytes.
            data+=bytes([128 if current['axes_available'] else 0])+struct.pack('<H',y//50-1 if current['axes_available'] else 0)
            commands.append((58,0,data))
            struct.pack_into('<H',pages[65],1+i*2,x//50-1);pages[65][17+i*3:20+i*3]=bytes(color)
            if current['axes_available']:struct.pack_into('<H',pages[65],41+i*2,y//50-1)
        pages[64][2]=((active+1)<<4)|count
    return commands,{str(p):list(v) for p,v in pages.items()}
