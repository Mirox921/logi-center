import QtQuick
import QtQuick.Controls
import Theme 1.0

Button {
    id: control
    property bool primary: false
    property bool selected: false
    property bool quietSelected: false
    hoverEnabled: true
    opacity: enabled ? 1 : 0.45
    padding: 0
    implicitWidth: labelText.implicitWidth + 28
    implicitHeight: 34
    background: CutFrame {
        fillColor: control.down ? Theme.surface4 : control.primary ? Theme.accent : (control.selected && !control.quietSelected ? Theme.accentSoft : control.hovered ? Theme.surface3 : Theme.surface1)
        lineColor: control.activeFocus ? Theme.accent : control.primary ? Theme.accent : control.selected ? Theme.accent : Theme.borderStrong
        lineWidth: control.activeFocus ? 2 : 1
        cut: Theme.cutSmall
    }
    contentItem: StyledText {
        id: labelText
        text: control.text
        color: control.primary ? Theme.background : control.selected ? Theme.accent : Theme.text
        font.family: control.primary ? Theme.displayFont : Theme.dataFont
        font.pixelSize: 12
        font.weight: control.primary ? Font.Bold : Font.Medium
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        leftPadding: 13; rightPadding: 13
        elide: Text.ElideRight
    }
}
