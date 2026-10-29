import QtQuick
import QtQuick.Controls
import Theme 1.0

ComboBox {
    id: combo
    implicitHeight: 38
    implicitWidth: 230
    leftPadding: 12; rightPadding: 28
    font.family: Theme.dataFont; font.pixelSize: 13
    contentItem: StyledText {
        text: combo.displayText; color: combo.enabled ? Theme.text : Theme.subtle
        font: combo.font; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
    }
    background: CutFrame { fillColor: Theme.background; lineColor: combo.activeFocus ? Theme.accent : Theme.borderStrong; cut: Theme.cutSmall }
    indicator: StyledText { x: combo.width-24; y: 8; text: "⌄"; color: Theme.muted; font.pixelSize: 18 }
    delegate: ItemDelegate {
        required property int index
        required property var modelData
        width: combo.width
        implicitHeight: 38
        highlighted: combo.highlightedIndex === index
        contentItem: StyledText { text: combo.textRole ? modelData[combo.textRole] : modelData; color: Theme.text; font: combo.font; elide: Text.ElideRight }
        background: Rectangle { color: parent.highlighted ? Theme.surface3 : Theme.surface1 }
    }
    popup: Popup {
        y: combo.height; width: combo.width
        implicitHeight: Math.min(contentItem.implicitHeight+8,300)
        padding: 4
        background: CutFrame { fillColor: Theme.surface1; lineColor: Theme.borderStrong; cut: Theme.cutSmall }
        contentItem: ListView {
            clip: true; implicitHeight: contentHeight
            model: combo.popup.visible ? combo.delegateModel : null
            currentIndex: combo.highlightedIndex
            ScrollBar.vertical: ScrollBar {}
        }
    }
}
