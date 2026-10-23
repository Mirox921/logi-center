"""Read-only capability queries; no properties are set here."""
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
