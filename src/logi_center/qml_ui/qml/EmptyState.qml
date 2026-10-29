import QtQuick
import QtQuick.Layouts
import Theme 1.0

CutCard {
    id: empty
    property string title: ""
    property string detail: ""
    fillColor: "transparent"
    lineColor: Theme.borderStrong
    inset: 20
    CutFrame { anchors.fill: parent; fillColor: "transparent"; lineColor: Theme.border; dashed: true; cut: Theme.cut }
    ColumnLayout {
        anchors.fill: parent
        spacing: 8
        StyledText { text: empty.title; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 20; font.weight: Font.Bold; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        StyledText { text: empty.detail; color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
    }
}
