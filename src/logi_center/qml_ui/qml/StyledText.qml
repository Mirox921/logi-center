import QtQuick
import Theme 1.0

// Shared glyph path. main.py selects grayscale distance-field antialiasing.
Text {
    renderType: Text.QtRendering
    font.hintingPreference: Theme.textHinting
    font.kerning: true
    anchors.alignWhenCentered: true
}
