import QtQuick
import Theme 1.0

Item {
    id: ledTag
    property string label: ""
    property color tone: Theme.success
    implicitWidth: labelText.implicitWidth + 18
    implicitHeight: 23
    CutFrame { anchors.fill: parent; fillColor: "transparent"; lineColor: Qt.darker(ledTag.tone, 1.35); cut: 5 }
    Rectangle { x: 7; y: 9; width: 5; height: 5; color: ledTag.tone }
    StyledText { id: labelText; anchors.verticalCenter: parent.verticalCenter; x: 17; text: ledTag.label.toLocaleUpperCase(); color: ledTag.tone; font.family: Theme.dataFont; font.pixelSize: 12; font.weight: Font.Medium }
}
