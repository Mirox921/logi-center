"""Explicit class/variant registry. Generic classes never claim a product model."""
from . import mouse, keyboard, touchpad, dongle, headset, speaker, display_port, microphone, laptop_keyboard, generic

ARTWORK_KEYS = (
    'mouse', 'mouse_gaming', 'mouse_wireless', 'mouse_compact', 'mouse_builtin', 'touchpad', 'pointer_generic',
    'keyboard', 'keyboard_60', 'keyboard_65', 'keyboard_tkl', 'keyboard_full', 'keyboard_builtin',
    'headset', 'headphones', 'speakers', 'display_hdmi','display_dp','display_audio', 'microphone', 'usb_audio',
    'bluetooth_audio', 'builtin_audio', 'audio_unknown', 'receiver', 'unknown',
)


def build_model(key):
    if key not in ARTWORK_KEYS:
        raise ValueError(f'Unknown illustration class: {key}')
    if key in ('mouse_builtin','pointer_generic'):
        model=touchpad.build('pointer_generic')
    elif key.startswith('mouse'):
        variant = {'mouse': 'generic', 'mouse_builtin': 'generic', 'mouse_gaming': 'gaming',
                   'mouse_wireless': 'wireless', 'mouse_compact': 'compact'}[key]
        model = mouse.build(variant)
    elif key == 'touchpad':
        model = touchpad.build()
    elif key == 'keyboard_builtin':
        model = laptop_keyboard.build()
    elif key.startswith('keyboard'):
        model = keyboard.build(key.removeprefix('keyboard_') if key != 'keyboard' else '65')
    elif key in ('headset', 'headphones'):
        model = headset.build(key)
    elif key == 'bluetooth_audio':
        # Transport alone cannot establish headset vs speaker form.
        model = generic.build('bluetooth_audio')
    elif key == 'speakers':
        model = speaker.build()
    elif key in ('display_audio','display_hdmi','display_dp'):
        model = display_port.build(key.removeprefix('display_'))
    elif key == 'microphone':
        model = microphone.build()
    elif key == 'receiver':
        model = dongle.build()
    else:
        model = generic.build(key if key in ('usb_audio','builtin_audio','audio_unknown') else 'unknown')
    model.key = key
    return model
