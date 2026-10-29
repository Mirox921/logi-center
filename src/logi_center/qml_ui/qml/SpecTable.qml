import QtQuick
import QtQuick.Layouts
import Theme 1.0

ColumnLayout {
    id: table
    property var entries: []
    spacing: 4
    Repeater {
        model: table.entries
        delegate: RowLayout {
            id: specRow
            required property var modelData
            Layout.fillWidth: true
            StyledText { text: specRow.modelData.key; color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12; Layout.preferredWidth: 82; elide: Text.ElideRight }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.border; opacity: .65 }
            StyledText { text: specRow.modelData.value; color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 12; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight; Layout.maximumWidth: 150 }
        }
    }
}
