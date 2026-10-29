import QtQuick
import QtQuick.Layouts
import Theme 1.0

Item {
    id: about
    required property var windowRef
    ColumnLayout {
        anchors.left: parent.left; anchors.top: parent.top
        spacing: 18
        Image { source: "../assets/brand/logi-mark.svg"; Layout.preferredWidth: 80; Layout.preferredHeight: 80; sourceSize: Qt.size(160,160) }
        StyledText { text: "LOGI / CENTER"; font.family: Theme.displayFont; font.bold: true; font.pixelSize: 32; color: Theme.text }
        StyledText { text: "v" + about.windowRef.bridge.appVersion + " · Qt6 / QML"; color: Theme.warning; font.family: Theme.dataFont; font.pixelSize: 14 }
        StyledText { text: about.windowRef.tr("Единый центр управления периферией Linux"); color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 12 }
        StyledText { text: "MIT · Qt for Python / PySide6"; color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12 }
    }
}
