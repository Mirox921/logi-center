import QtQuick
import QtQuick.Layouts
import Theme 1.0

RowLayout {
    id: header
    property string indexText: "01"
    property string title: ""
    property string countText: ""
    spacing: 9
    StyledText { text: header.indexText + " /"; color: Theme.accent; font.family: Theme.dataFont; font.pixelSize: 12; font.weight: Font.Bold }
    StyledText { text: header.title.toLocaleUpperCase(); color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 12; font.letterSpacing: 1.2; font.weight: Font.Medium }
    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.border }
    StyledText { visible: header.countText.length > 0; text: header.countText; color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12 }
}
