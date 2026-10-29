import QtQuick
import Theme 1.0

Item {
    id: card
    property color fillColor: Theme.surface1
    property color lineColor: Theme.border
    property real cut: Theme.cut
    property int inset: 16
    default property alias content: body.data

    CutFrame { anchors.fill: parent; fillColor: card.fillColor; lineColor: card.lineColor; cut: card.cut }
    Item { id: body; anchors.fill: parent; anchors.margins: card.inset; clip: true }
}
