import QtQuick
import QtQuick.Controls
import Theme 1.0

TextField {
    id: input
    color: Theme.text
    placeholderTextColor: Theme.subtle
    font.family: Theme.dataFont
    font.pixelSize: 13
    font.hintingPreference: Theme.textHinting
    renderType: Text.QtRendering
    implicitHeight: 38
    implicitWidth: 180
    leftPadding: 12; rightPadding: 12
    selectionColor: Theme.accentSoft
    selectedTextColor: Theme.text
    background: CutFrame { fillColor: Theme.background; lineColor: input.activeFocus ? Theme.accent : Theme.borderStrong; cut: Theme.cutSmall }
}
