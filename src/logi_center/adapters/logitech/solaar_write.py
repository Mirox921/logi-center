"""Scoped CLI adapter: an explicit setting must not play a shutdown animation on exit."""
import sys
import re


def brightness_metadata(setting,templates):
    """Inspect the initialized validator, without requesting additional HID data.

    Some Solaar builds snap writes to firmware halving marks; stock builds
    expose a continuous range. Use the installed implementation, not guessed
    G515 levels or a version-number heuristic.
    """
    validator=getattr(setting,'_validator',None)
    minimum=getattr(validator,'min_value',None);maximum=getattr(validator,'max_value',None)
    if type(minimum) is not int or type(maximum) is not int or not 0<=minimum<=maximum<=100:
        return None
    info={'minimum':minimum,'maximum':maximum}
    steps=getattr(validator,'steps',0);marks=getattr(templates,'halving_marks',None)
    if type(steps) is int and 2<=steps<=15 and callable(marks):
        levels=marks(maximum,steps)
        if isinstance(levels,list) and all(type(v) is int for v in levels):
            levels=sorted({v for v in levels if minimum<=v<=maximum})
            if levels:info['levels']=levels
    return info


def expose_brightness_metadata(templates):
    """Annotate the one scoped CLI getter in this short-lived process only."""
    cls=getattr(templates,'BrightnessControl',None)
    if cls is None:return
    original=cls.read
    def read(setting,*args,**kwargs):
        value=original(setting,*args,**kwargs)
        info=brightness_metadata(setting,templates)
        if info is not None:
            import json
            print('#   logi-center-brightness: '+json.dumps(info,sort_keys=True))
        status=battery_metadata(setting,templates)
        if status is not None:
            import json
            print('#   logi-center-battery: '+json.dumps(status,sort_keys=True))
        return value
    cls.read=read


def battery_metadata(setting,templates):
    """One supported HID++ battery getter; never apply or initialize settings."""
    device=getattr(setting,'_device',None)
    reader=getattr(templates,'_hidpp20',None)
    features=getattr(templates,'_F',None)
    if device is None or reader is None or features is None:return None
    if not getattr(device,'online',False):return None
    # Avoid Solaar's battery wrapper that may update LEDs on old protocols.
    for name,method in (('UNIFIED_BATTERY','get_battery_unified'),
                        ('BATTERY_STATUS','get_battery_status'),
                        ('BATTERY_VOLTAGE','get_battery_voltage')):
        feature=getattr(features,name,None)
        if feature is None or feature not in device.features:continue
        try:result=getattr(reader,method)(device)
        except Exception:return None
        if not isinstance(result,tuple) or len(result)!=2:return None
        battery=result[1];status=getattr(getattr(battery,'status',None),'name',None)
        charging=True if status in ('RECHARGING','ALMOST_FULL','SLOW_RECHARGE') else False if status in ('DISCHARGING','FULL') else None
        level=getattr(battery,'level',None)
        # Approximate enum levels must not become invented percentages.
        return {'battery_status':level if type(level) is int and 0<=level<=100 else None,
                'charging':charging}
    return None


def rgb_metadata(setting,templates):
    """Only effects/fields enumerated by this device's initialized validator."""
    validator=getattr(setting,'_validator',None)
    options=getattr(validator,'options',None)
    if not isinstance(options,(list,tuple)):return None
    tables=getattr(getattr(templates,'hidpp20',None),'LEDEffects',{})
    fields={str(f.get('name')):f for f in getattr(setting,'possible_fields',[]) if isinstance(f,dict)}
    effects=[]
    for option in options:
        effect=int(option.ID)
        if effect not in (0,1,3,4,10,11,21,22,23) or effect not in tables:continue
        layout=tables[effect];defaults=layout[2] if len(layout)>2 else {};ranges=layout[3] if len(layout)>3 else {}
        params={}
        for parameter in layout[1]:
            name=str(parameter)
            if name not in ('color','period','intensity','saturation','direction','speed'):continue
            field=fields.get(name,{})
            limits=ranges.get(parameter)
            spec={}
            if limits:spec.update(minimum=int(limits[0]),maximum=int(limits[1]))
            elif 'min' in field and 'max' in field:spec.update(minimum=int(field['min']),maximum=int(field['max']))
            choices=field.get('choices')
            if choices is not None:spec['choices']=[int(v) for v in choices]
            if parameter in defaults:spec['default']=int(defaults[parameter])
            params[name]=spec
        effects.append({'id':effect,'parameters':params})
    return {'readable':bool(getattr(validator,'readable',False) and getattr(getattr(setting,'_rw',None),'read_fnid',None) is not None),
            'effects':effects}


def expose_rgb_metadata(templates):
    cls=getattr(templates,'RGBEffectSetting',None)
    if cls is None:return
    original=cls.read
    def read(setting,*args,**kwargs):
        value=original(setting,*args,**kwargs)
        info=rgb_metadata(setting,templates)
        if info is not None:
            import json
            print('#   logi-center-rgb: '+json.dumps(info,sort_keys=True))
        return value
    cls.read=read


def read_only_args(args):
    from logi_center.adapters.logitech.g515_adapter import READ_KEYS
    if len(args)!=3 or args[0]!='config' or not args[1] or args[2] not in READ_KEYS:
        raise ValueError('Read-only Solaar requires exactly one allowlisted setting and no value')
    return args


def freeze_configuration(configuration):
    """Getters may populate defaults in memory; never persist them in this worker."""
    configuration.save=lambda *args,**kwargs:None
    if hasattr(configuration,'do_save'):configuration.do_save=lambda *args,**kwargs:None


def guard_reads(settings,rgb_power):
    """No settings writes/apply, RGB controller start, or shutdown animation."""
    def denied(*args,**kwargs):raise RuntimeError('Hardware writes are disabled in read-only Solaar')
    pending=[settings.Setting];seen=set()
    while pending:
        cls=pending.pop()
        if cls in seen:continue
        seen.add(cls);pending.extend(cls.__subclasses__())
        for name in ('write','write_key_value','write_item_value','apply'):
            if hasattr(cls,name):setattr(cls,name,denied)
    for name in ('FeatureRW','FeatureRWMap','RegisterRW'):
        cls=getattr(settings,name,None)
        if cls is not None and hasattr(cls,'write'):cls.write=denied
    if rgb_power is not None:
        rgb_power.start=denied
        rgb_power.cleanup=lambda device:rgb_power.stop(device)


def guard_effect_write(templates):
    """Refresh the prerequisite in the *same* process as the zone write.

    Patched Solaar gates RGBEffectSetting.write on rgb_control._value.
    A preceding CLI process cannot initialize that object's memory.
    Never enable control here: the explicit application plan owns that write.
    """
    cls=getattr(templates,'RGBEffectSetting',None)
    if cls is None:return
    original=cls.write
    def write(setting,value,*args,**kwargs):
        control=next((s for s in setting._device.settings if s.name=='rgb_control'),None)
        # Setting.read(cached=False) can still return old _value on an empty
        # reply. Validate the actual getter response instead of that fallback.
        reply=control._rw.read(setting._device) if control is not None else None
        observed=control._validator.validate_read(reply) if reply else None
        if observed is not True:
            raise RuntimeError('LED Control is disabled or could not be read; effect was not sent')
        control._value=observed
        return original(setting,value,*args,**kwargs)
    cls.write=write


def match_unit_devices(devices,target):
    """Exact G515 unit IDs can differ from the receiver pairing serial."""
    target=target.casefold();matches=[]
    for device in devices:
        serial=str(getattr(device,'serial','') or '').casefold()
        g515='g515' in str(getattr(device,'name','')).casefold()
        unit=str(getattr(device,'unitId','') or '').casefold() if g515 else ''
        if not re.fullmatch('[0-9a-f]{8,32}',unit) or len(set(unit))<=1:unit=''
        if serial==target or unit==target:matches.append((device,unit))
    if len(matches)>1:
        units={unit for _,unit in matches}
        if len(units)!=1 or not next(iter(units)):
            raise RuntimeError('Exact device identity is ambiguous')
    # A live cable view of the same unit takes priority over its receiver view.
    return [d for d,_ in sorted(matches,key=lambda pair:getattr(pair[0],'receiver',None) is not None)]


def enable_unit_selector(cli):
    original=cli._find_device
    def find(receivers,name):
        if not re.fullmatch('[0-9a-fA-F]{8,32}',name or ''):
            yield from original(receivers,name);return
        devices=list(original(receivers,''))
        if len(devices)>16:raise RuntimeError('Too many device identity candidates')
        yield from match_unit_devices(devices,name)
    cli._find_device=find


def main(args=None):
    args=list(sys.argv[1:] if args is None else args)
    readonly=args[:1]==['--read-only']
    if readonly:args=read_only_args(args[1:])  # validate before importing device code
    # Stock and patched Solaar builds with the same release number can differ.
    # An optional RGB power manager must not be a prerequisite for reading.
    try:from logitech_receiver import rgb_power
    except ImportError:rgb_power=None
    # Process-local only: never play a firmware shutdown animation on close.
    if rgb_power is not None:rgb_power.cleanup=lambda device:rgb_power.stop(device)
    from solaar import cli
    enable_unit_selector(cli)
    if readonly:
        from solaar import configuration
        freeze_configuration(configuration)
        from logitech_receiver import settings,settings_templates  # load overrides before guarding
        guard_reads(settings,rgb_power)
        if args[2]=='brightness_control':expose_brightness_metadata(settings_templates)
        if args[2]=='rgb_zone_1':expose_rgb_metadata(settings_templates)
        from solaar.cli import run
        return run(args)
    if len(args)>=4 and args[0]=='config' and args[2]=='rgb_zone_1':
        from logitech_receiver import settings_templates
        guard_effect_write(settings_templates)
    from solaar.gtk import main as cli_main
    return cli_main()


if __name__=='__main__':sys.exit(main())
