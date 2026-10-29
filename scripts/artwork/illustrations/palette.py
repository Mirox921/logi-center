"Offline mirror of src/logi_center/qml_ui/qml/Theme/Theme.qml; guarded by a parity test.\n\nOnly the illustration plastic is neutralized: the UI's warm graphite values\nare luminance references, not a brown tint painted over the hardware.\n"
TOKENS = {
    'background': '#171713', 'surface1': '#211f1a', 'surface2': '#292720',
    'surface3': '#343129', 'surface4': '#3e3a31', 'border': '#514c41',
    'borderStrong': '#756d5d', 'accent': '#f3aa32', 'text': '#f4f0e7',
}


def rgb(value):
    return tuple(int(value[i:i + 2], 16) / 255 for i in (1, 3, 5))


def neutral(token, lift=0):
    value = sum(rgb(TOKENS[token])) / 3 + lift
    return (value, value, value)


AMBER = rgb(TOKENS['accent'])
