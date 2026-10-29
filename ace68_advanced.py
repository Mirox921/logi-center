"""Typed native Ace68-II advanced bindings; no I/O outside the shared adapter.

M HUB CZ: DKS 162/163, MT/RS/SOCD 164/165, TGL 166/167.
Only unreferenced zero records are allocated. Existing records are never
compacted or renumbered. Binding references are installed after record data.
"""
from copy import deepcopy
from ace68_protocol import KEY_INDICES
from ace68_bindings import validate_action

BANKS={'dks':(162,163,768,24),'mt':(164,165,256,6),'tgl':(166,167,128,3)}
TYPES={'dks':144,'tgl':145,'mt':146,'rs':147,'socd':148}


def _actions(current,defaults):
    return [[list((defaults[layer] if bank[i*3]==255 else bank)[i*3:i*3+3]) for i in range(128)] for layer,bank in enumerate(current)]


def _phase_decode(word):
    a,b,c,d=word&7,(word>>3)&7,(word>>6)&7,(word>>9)&1
    convert=lambda v:3 if v&4 else 2 if v&2 else 1 if v&1 else 0
    a,b,c,d=convert(a),convert(b),2 if c&2 else 1 if c&1 else 0,d
    if a==3:
        if b==3:a,b,c=4,0,0
        else:b=0
    elif b==3:c=0
    return [a,b,c,d]


def _phase_encode(phase):
    if (not isinstance(phase,list) or len(phase)!=4 or
            any(type(v) is not int or not 0<=v<=high for v,high in zip(phase,[4,3,2,1]))):raise ValueError('Invalid DKS phase')
    a,b,c,d=phase
    if a==4:a,b,c=3,3,2
    elif a==3:a,b=3,2
    if b==3:c=2
    bits=lambda v:(1 if v>0 else 0)|(2 if v>1 else 0)|(4 if v>2 else 0)
    word=bits(a)|(bits(b)<<3)|(bits(c)<<6)|(bits(d)<<9)
    if _phase_decode(word)!=phase:raise ValueError('Incompatible DKS phases')
    return word


def decode(bindings,defaults,banks,raw_keys):
    matrix=_actions(bindings,defaults);result={}
    for layer,rows in enumerate(matrix):
        for index in KEY_INDICES:
            kind,slot,extra=rows[index]
            name=next((name for name,code in TYPES.items() if kind==code),None)
            if not name:continue
            if slot>=32:raise ValueError('Unknown advanced record index')
            if name in ('rs','socd'):
                if extra not in KEY_INDICES or extra==index or rows[extra][0]!=kind or rows[extra][2]!=index:
                    raise ValueError('Unpaired advanced keys; no repair attempted')
                if extra<index:continue
            group=name if name in ('dks','tgl') else 'mt';size=BANKS[group][3]
            record=banks[group][slot*size:(slot+1)*size]
            entry={'kind':name,'layer':layer,'keys':[index]}
            if name=='tgl':entry['actions']=[record[:3]]
            elif name=='dks':
                entry.update(points=record[:4],actions=[record[4+i*5:7+i*5] for i in range(4)],
                    phases=[_phase_decode(int.from_bytes(bytes(record[7+i*5:9+i*5]),'little')) for i in range(4)])
            else:
                entry['actions']=[record[:3],record[3:6]]
                if name=='mt':entry['time']=extra*10
                else:
                    entry['keys'].append(extra)
                    if name=='socd':entry['priority']=raw_keys[index*8+1]>>4
            result[str(layer)+':'+str(index)]=entry
    return result


def read(wire,profile,observed):
    banks={name:list(wire.read(command,profile*area,area)) for name,(command,write,area,size) in BANKS.items()}
    if any(len(banks[name])!=spec[2] for name,spec in BANKS.items()):raise ValueError('Incomplete advanced bank')
    return {'raw_advanced':banks,'advanced_keys':decode(observed['raw_bindings'],observed['default_bindings'],banks,observed['raw_keys'])}


def prepare(observed,changes):
    if not isinstance(changes,dict) or len(changes)!=1:raise ValueError('Apply one advanced binding at a time')
    identifier,desired=next(iter(changes.items()));profile=observed['profiles']
    matrix=_actions(observed['raw_bindings'],observed['default_bindings'])
    before=deepcopy(matrix);banks=deepcopy(observed['raw_advanced']);keys=bytearray(observed['raw_keys'])
    original=observed['advanced_keys'].get(identifier)
    if original:
        if original['kind']=='dks':
            layer=original['layer'];slot=before[layer][original['keys'][0]][1]
            record=banks['dks'][slot*24:(slot+1)*24]
            if any(record[8+i*5]&252 for i in range(4)):
                raise ValueError('Unknown DKS reserved bits; definition is preserved')
        for index in original['keys']:matrix[original['layer']][index]=observed['default_bindings'][original['layer']][index*3:index*3+3]
    elif desired is None:raise ValueError('Advanced binding is absent')
    data_frames=[];priority_frames=[];cleanup=[]
    used={name:set() for name in BANKS}
    for row in before:
        for kind,slot,unused in row:
            group='dks' if kind==144 else 'tgl' if kind==145 else 'mt' if kind in (146,147,148,149) else None
            if group:used[group].add(slot)

    def allocate(group,record):
        command,write,area,size=BANKS[group]
        free=next((i for i in range(32) if i not in used[group] and not any(banks[group][i*size:(i+1)*size])),None)
        if free is None:raise ValueError('No unused zero advanced records; existing data is preserved')
        used[group].add(free);banks[group][free*size:(free+1)*size]=list(record)
        data_frames.append((write,profile*area+free*size,bytes(record)))
        return free

    if desired is not None:
        if not isinstance(desired,dict) or desired.get('kind') not in TYPES:raise ValueError('Unknown advanced type')
        name=desired['kind'];layer=desired.get('layer');indices=desired.get('keys');actions=desired.get('actions')
        count=2 if name in ('rs','socd') else 1
        if (type(layer) is not int or not 0<=layer<4 or not isinstance(indices,list) or len(indices)!=count or
                any(type(i) is not int or i not in KEY_INDICES for i in indices) or len(set(indices))!=count):raise ValueError('Invalid advanced target')
        if identifier!=str(layer)+':'+str(min(indices)):raise ValueError('Advanced binding identity differs from target')
        if any(144<=matrix[layer][i][0]<=149 for i in indices):raise ValueError('Remove the existing advanced binding first')
        expected_actions=4 if name=='dks' else 1 if name=='tgl' else 2
        if not isinstance(actions,list) or len(actions)!=expected_actions:raise ValueError('Wrong advanced action count')
        for action in actions:validate_action(action)
        if name=='tgl':slots=[allocate('tgl',actions[0])]
        elif name=='dks':
            points=desired.get('points',[10,30,30,10]);phases=desired.get('phases')
            if (not isinstance(points,list) or len(points)!=4 or any(type(v) is not int or not 0<=v<=255 for v in points) or
                    points!=(original.get('points') if original and original['kind']=='dks' else [10,30,30,10])):
                raise ValueError('DKS travel points must retain the observed/native defaults')
            if not isinstance(phases,list) or len(phases)!=4:raise ValueError('Expected four DKS action phases')
            record=bytearray(points)
            for action,phase in zip(actions,phases):record.extend(bytes(action)+_phase_encode(phase).to_bytes(2,'little'))
            slots=[allocate('dks',record)]
        else:
            slots=[allocate('mt',actions[0]+actions[1])]
            if count==2:slots.append(allocate('mt',actions[1]+actions[0]))
        if name=='mt':
            duration=desired.get('time')
            if type(duration) is not int or not 0<=duration<=1000 or duration%10:raise ValueError('MT time is 0..1000 ms, step 10')
        if name=='socd':
            priority=desired.get('priority')
            if type(priority) is not int or priority not in (0,1,2,3):raise ValueError('Unknown SOCD priority')
        for n,index in enumerate(indices):
            extra=duration//10 if name=='mt' else indices[1-n] if count==2 else 0
            matrix[layer][index]=[TYPES[name],slots[n],extra]
            if name=='socd':
                value=priority if n==0 else {0:0,1:2,2:1,3:3}[priority]
                offset=index*8;previous=keys[offset+1]>>4
                if previous>3:raise ValueError('Unknown native priority bits; key record is preserved')
                if previous!=value and any(matrix[other][index][0]==148 for other in range(4) if other!=layer):
                    raise ValueError('SOCD priority is shared with another layer; preserve its binding')
                keys[offset+1]=(keys[offset+1]&15)|(value<<4)
                priority_frames.append((161,profile*1024+offset,bytes(keys[offset:offset+8])))
    # Fn access must remain available in the base layers.
    for layer in (0,2):
        fn=lambda value:value in ([240,255,1],[240,255,3])
        if any(fn(a) for a in before[layer]) and not any(fn(a) for a in matrix[layer]):raise ValueError('Preserve at least one Fn key')
    reference_frames=[(9,(profile*4+layer)*512+i*3,bytes(value)) for layer,row in enumerate(matrix) for i,value in enumerate(row) if value!=before[layer][i]]
    # Clear only now-unreferenced records belonging to the replaced definition.
    if original:
        group=original['kind'] if original['kind'] in ('dks','tgl') else 'mt'
        command,write,area,size=BANKS[group]
        for index in original['keys']:
            slot=before[original['layer']][index][1]
            still_used=any((a[0]==144 if group=='dks' else a[0]==145 if group=='tgl' else a[0] in (146,147,148,149)) and a[1]==slot for row in matrix for a in row)
            if not still_used:
                record=observed['raw_advanced'][group][slot*size:(slot+1)*size]
                if group=='dks' and any(record[8+i*5]&252 for i in range(4)):continue
                cleanup.append((write,profile*area+slot*size,bytes(size)));banks[group][slot*size:(slot+1)*size]=[0]*size
    target_bindings=deepcopy(observed['raw_bindings'])
    for command,offset,record in reference_frames:
        layer=(offset//512)%4;local=offset%512;target_bindings[layer][local:local+3]=list(record)
    expected=decode(target_bindings,observed['default_bindings'],banks,list(keys)).get(identifier)
    return data_frames+priority_frames+reference_frames+cleanup,{identifier:expected}
