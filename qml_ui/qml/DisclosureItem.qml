import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

ColumnLayout {
    id: root
    property string label: ""
    property string text: ""
    property bool expanded: false
    spacing: 8
    CutButton { text: (root.expanded ? "− " : "+ ") + root.label; onClicked: root.expanded = !root.expanded }
    ScrollView {
        visible: root.expanded
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(150, detail.implicitHeight + 8)
        TextArea {
            renderType: TextEdit.QtRendering; font.hintingPreference: Theme.textHinting; id: detail; readOnly: true; text: root.text; wrapMode: TextEdit.Wrap; color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 12; background: Rectangle { color: Theme.surface1 } }
    }
}
