"""Read-only capability queries; no properties are set here."""
import re


def device_models():
    """Unique ratbag names and model IDs, for conservative kernel matching.

    Model is shared by all units of a product. Callers must also require a
    unique backend selector and a unique physical kernel candidate.
    """
    from gi.repository import Gio, GLib
    connection = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)

    def props(path, interface):
        return connection.call_sync(
            'org.freedesktop.ratbag1', path, 'org.freedesktop.DBus.Properties',
            'GetAll', GLib.Variant('(s)', ('org.freedesktop.ratbag1.' + interface,)),
            GLib.VariantType.new('(a{sv})'), Gio.DBusCallFlags.NONE, 1500, None,
        ).unpack()[0]

    names = {}
    duplicates = set()
    for path in props('/org/freedesktop/ratbag1', 'Manager').get('Devices', []):
        device = props(path, 'Device')
        name = device.get('Name')
        model = re.fullmatch(r'(?:usb|bluetooth):([0-9a-fA-F]{4}):([0-9a-fA-F]{4}):[0-9a-fA-F]+', str(device.get('Model', '')))
        if not name or not model:
            continue
        if name in names:
            duplicates.add(name)
        names[name] = (model[1].lower(), model[2].lower())
    return {name: pair for name, pair in names.items() if name not in duplicates}

def button_types(model,profile):
    from gi.repository import Gio,GLib
    connection=Gio.bus_get_sync(Gio.BusType.SYSTEM,None)
    def props(path,interface):
        return connection.call_sync('org.freedesktop.ratbag1',path,'org.freedesktop.DBus.Properties','GetAll',GLib.Variant('(s)',('org.freedesktop.ratbag1.'+interface,)),GLib.VariantType.new('(a{sv})'),Gio.DBusCallFlags.NONE,2500,None).unpack()[0]
    manager=props('/org/freedesktop/ratbag1','Manager')
    matching=[]
    for path in manager.get('Devices',[]):
        device=props(path,'Device')
        if device.get('Model')==model:matching.append(device)
    if len(matching)!=1:return {}
    paths=matching[0].get('Profiles',[])
    for path in paths:
        p=props(path,'Profile')
        if p.get('Index')==profile:return {props(button,'Button')['Index']:props(button,'Button').get('ActionTypes',[]) for button in p.get('Buttons',[])}
    return {}
