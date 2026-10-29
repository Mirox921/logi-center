pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

ColumnLayout {
    id: root
    required property var controller
    required property var windowRef
    spacing: 9
    StyledText { text: root.windowRef.tr("Выбери клавишу на схеме"); color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 14 }
    CutCombo { visible: root.controller.referenceKeyboard; model: ["ANSI TKL","ANSI Full size","ANSI 60%","Laptop"]; onActivated: index=>root.controller.setReferenceLayout(["tkl","full","60","laptop"][index]) }
    Item {
        Layout.fillWidth: true
        Layout.preferredHeight: root.controller.keyboardRows*36+2
        readonly property real unit: width/root.controller.keyboardUnits
        Repeater {
            model: root.controller.keyModel
            delegate: CutButton {
                id: keycap
                required property var modelData
                x: modelData.x*parent.unit; y: modelData.y*36
                width: modelData.w*parent.unit-3; height: (modelData.h || 1)*36-4
                text: ({"Backspace":"⌫","Space":"Space","LShift":"⇧","RShift":"⇧","Enter":"↵","Caps":"⇪","Super":"◆","LCtrl":"Ctrl","RCtrl":"Ctrl","LAlt":"Alt","RAlt":"Alt","PgUp":"Pg↑","PgDn":"Pg↓"})[modelData.label] || modelData.label
                contentItem: StyledText { text: keycap.text; color: keycap.selected ? Theme.accent : Theme.text; font.family: Theme.dataFont; font.pixelSize: 12; leftPadding: 1; rightPadding: 1; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                selected: root.controller.selectedKey === modelData.id
                Accessible.name: modelData.label
                ToolTip.visible: hovered; ToolTip.text: modelData.label
                onClicked: root.controller.selectKey(modelData.id)
            }
        }
    }
    StyledText {
        visible: root.controller.referenceKeyboard
        text: root.windowRef.tr("Переназначение и подсветка отдельных клавиш не обнаружены.")
        color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true
    }
}
