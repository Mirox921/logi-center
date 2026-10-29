import QtQuick
import Theme 1.0

Item {
    id: tag
    property string label: ""
    property color tone: Theme.muted
    implicitWidth: labelText.implicitWidth + 28
    implicitHeight: 28
    CutFrame { anchors.fill: parent; fillColor: "transparent"; lineColor: Theme.borderStrong; cut: 5 }
    StyledText { id: labelText; objectName: "connectionText"; anchors.centerIn: parent; text: tag.label.toLocaleUpperCase(); color: tag.tone; font.family: Theme.dataFont; font.pixelSize: 12; font.letterSpacing: 0 }
}
