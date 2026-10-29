"""Isolated, read-only G502 profile observation through the installed Solaar API.

Never enumerate settings, acquire RGB ownership, or call Device.close cleanup
callbacks. The SDK worker closes only its transport handle.
"""
import re
from execution import Fault,FaultCode


def read_device(device,features,profiles):
    class Reader:
        calls=0
        def feature_request(self,feature,function,*args):
            self.calls+=1
            if feature!=features.ONBOARD_PROFILES or function not in (0x20,0x40,0x50) or self.calls>24:
                raise ValueError('Read-only profile request boundary')
            return device.feature_request(feature,function,*args)
    reader=Reader()
    mode=reader.feature_request(features.ONBOARD_PROFILES,0x20)
    if not mode:raise ValueError('Onboard mode was not reported')
    if mode[0]!=1:return {'mode':'host','profile':None,'sector':None}
    active=reader.feature_request(features.ONBOARD_PROFILES,0x40)
    headers=profiles.get_profile_headers(reader)
    if not active or len(active)<2:raise ValueError('Active onboard profile was not reported')
    sector=int.from_bytes(active[:2],'big');sectors=[entry[0] for entry in headers]
    if len(sectors)!=len(set(sectors)) or sector not in sectors:raise ValueError('Ambiguous onboard profile directory')
    return {'mode':'onboard','profile':sectors.index(sector),'sector':sector,'profile_count':len(sectors)}


def hardware(action,target):
    if action!='read' or not re.fullmatch(r'usb:046d:c08b:[0-9a-fA-F]+',target or ''):
        raise Fault(FaultCode.BACKEND_UNSUPPORTED,'logitech-status','Only read-only exact G502 HERO status is supported')
    from logitech_receiver import base
    from logitech_receiver.device import create_device,Device
    from logitech_receiver.hidpp20 import OnboardProfiles
    from logitech_receiver.hidpp20_constants import SupportedFeature
    infos=[info for info in base.receivers_and_devices() if str(info.vendor_id).lower()=='046d' and str(info.product_id).lower()=='c08b']
    # Ratbag's Model is not a physical selector for multiple identical units.
    if len(infos)!=1:raise Fault(FaultCode.CONFIG,'logitech-status','Live profile needs one unambiguous G502 HERO interface')
    device=create_device(base,infos[0])
    if device is None:raise Fault(FaultCode.DISCONNECTED,'logitech-status','G502 configuration interface unavailable')
    try:return read_device(device,SupportedFeature,OnboardProfiles)
    finally:
        handle,device.handle=device.handle,None
        if device in Device.instances:Device.instances.remove(device)
        if handle:base.close(handle)
