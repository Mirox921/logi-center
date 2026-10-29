"""Small helpers for truthful PipeWire/PulseAudio device presentation."""


def port_available(port):
    if not isinstance(port,dict):return None
    value=port.get('availability',port.get('available'))
    if isinstance(value,bool):return value
    if isinstance(value,str):
        value=value.strip().casefold()
        if value in {'yes','available','true','1'}:return True
        if value in {'no','unavailable','false','0','not available'}:return False
    return None


def device_available(device):
    """Return True/False only when PulseAudio/ALSA actually reports it."""
    if not isinstance(device,dict):return None
    state=str(device.get('state','')).upper()
    if state in {'UNAVAILABLE','NO'}:return False
    if state in {'RUNNING','IDLE','SUSPENDED'}:return True
    active=device.get('active_port')
    active_state=port_available(active)
    if active_state is not None:return active_state
    ports=[port_available(port) for port in device.get('ports',[]) if isinstance(port,dict)]
    known=[value for value in ports if value is not None]
    if any(known):return True
    if known and all(value is False for value in known):return False
    value=port_available(device)
    return value


def describe_availability(device):
    return {True:'available',False:'unavailable',None:'unknown'}[device_available(device)]


def endpoint_labels(items,kind,translate=lambda text:text):
    """Name logical routes from server metadata, keeping all stable IDs separate."""
    import re
    rows=[]
    def clean(value):return ' '.join(str(value or '').split())[:220]
    for item in items:
        props=item.get('properties',{})
        props=props if isinstance(props,dict) else {}
        description=clean(item.get('description') or props.get('node.description') or props.get('device.description') or props.get('device.product.name') or props.get('alsa.card_name'))
        route=clean(props.get('device.profile.description'))
        port=item.get('active_port')
        if isinstance(port,str):
            ports=item.get('ports') or []
            if isinstance(ports,dict):ports=ports.values()
            port=next((p for p in ports if isinstance(p,dict) and p.get('name')==port),{})
        port=port if isinstance(port,dict) else {}
        route=clean(port.get('description')) or route
        # Preserve numbered HDMI routes without repeating the entire controller name.
        hdmi=re.search(r'HDMI\s*/\s*DisplayPort\s*\d+',description,re.I)
        if hdmi:
            controller=clean(props.get('device.description') or props.get('alsa.card_name'))
            description=(route if re.search(r'HDMI\s*/\s*DisplayPort\s*\d+',route,re.I) else hdmi[0])+(' · '+controller if controller else '')
        label=description or translate('Аудиовыход' if kind=='sink' else 'Источник записи')
        if route and route.casefold() not in label.casefold():label+=' · '+route
        bus={'usb':'USB','bluetooth':'Bluetooth','pci':'PCI'}.get(props.get('device.bus'),'')
        rows.append({'label':label,'route':route,'bus':bus})
    counts={row['label']:sum(other['label']==row['label'] for other in rows) for row in rows}
    for index,row in enumerate(rows):
        if counts[row['label']]>1:
            # This is a server endpoint number, not a physical serial or a merge key.
            row['label']+=' · '+translate('Маршрут')+' '+str(items[index].get('index',index+1))
    return rows
